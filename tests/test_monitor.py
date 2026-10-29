from docker.errors import APIError

from containercraft.monitor import Monitor
from containercraft.policy import Policy
from containercraft.service import ContainerService
from tests.fakes import FakeClient, FakeContainer


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def make(*containers, **policy):
    clock = Clock()
    events = []
    svc = ContainerService(FakeClient(*containers))
    mon = Monitor(svc, Policy(**policy), on_event=events.append, clock=clock)
    return mon, clock, events


def test_restarts_hot_container_and_leaves_others_alone():
    hot, cool = FakeContainer("api", cpu=95), FakeContainer("db", cpu=5)
    mon, clock, _ = make(hot, cool, consecutive=2, auto_restart=True)
    for _ in range(2):
        mon.tick()
        clock.t += 30
    assert hot.calls == ["restart"] and cool.calls == []
    assert [e.kind for e in mon.events] == ["warn", "restart", "restarted"]
    assert mon.last_sample["db"]["cpu_percent"] == 5.0


def test_gave_up_is_reported_once():
    hot = FakeContainer("api", cpu=95)
    mon, clock, _ = make(hot, consecutive=1, auto_restart=True, cooldown=0, max_restarts=1)
    for _ in range(5):
        mon.tick()
        clock.t += 30
    kinds = [e.kind for e in mon.events]
    assert kinds.count("restart") == 1
    assert kinds.count("suppressed") == 1


def test_failed_restart_is_an_error_event():
    hot = FakeContainer("api", cpu=95)
    hot.restart_error = APIError("boom")
    mon, _, _ = make(hot, consecutive=1, auto_restart=True)
    mon.tick()
    assert mon.events[-1].kind == "error" and "restart failed" in mon.events[-1].message


def test_ok_samples_are_not_history():
    mon, _, events = make(FakeContainer("db", cpu=5))
    mon.tick()
    assert list(mon.events) == [] and events[0].kind == "ok"


def test_stopped_containers_are_ignored_and_forgotten():
    c = FakeContainer("api", cpu=95)
    mon, _, _ = make(c, consecutive=5)
    mon.tick()
    assert "api" in mon.states
    c.stop()
    mon.tick()
    assert "api" not in mon.states


def test_label_filter():
    a = FakeContainer("a", cpu=95, labels={"craft.watch": "true"})
    b = FakeContainer("b", cpu=95)
    clock = Clock()
    mon = Monitor(
        ContainerService(FakeClient(a, b)),
        Policy(consecutive=1, auto_restart=True),
        label="craft.watch=true",
        clock=clock,
    )
    mon.tick()
    assert a.calls == ["restart"] and b.calls == []


def test_background_thread_starts_and_stops():
    mon, _, _ = make(FakeContainer("db"))
    mon.interval = 0.01
    mon.start()
    assert mon.running
    mon.stop()
    assert not mon.running
