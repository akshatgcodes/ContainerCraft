"""Runs against a real Docker daemon; skipped when none is reachable."""

import time
import uuid

import pytest

from containercraft.monitor import Monitor
from containercraft.policy import Policy
from containercraft.service import ContainerService, DockerUnavailable

pytestmark = pytest.mark.docker


@pytest.fixture(scope="module")
def svc():
    try:
        return ContainerService()
    except DockerUnavailable:
        pytest.skip("Docker daemon not available")


@pytest.fixture
def container(svc):
    label = f"containercraft.test={uuid.uuid4().hex[:8]}"
    key, value = label.split("=")
    c = svc.client.containers.run(
        "busybox",
        # trap so SIGTERM stops it at once (PID 1 ignores it otherwise, forcing a 10s kill)
        [
            "sh",
            "-c",
            "trap 'exit 0' TERM; i=0; while true; do echo tick $i; i=$((i+1)); sleep 0.2; done",
        ],
        detach=True,
        labels={key: value},
        name=f"craft-test-{value}",
    )
    yield c, label
    c.remove(force=True)


def test_lifecycle_logs_and_stats(svc, container):
    c, label = container
    assert [i.name for i in svc.list(label=label)] == [c.name]

    time.sleep(1)
    assert "tick 0" in svc.logs(c.name, tail=1000)

    u = svc.usage(c.name)
    assert 0 <= u.cpu_percent < 50 and u.mem_limit > 0

    assert svc.stop(c.name, timeout=2).state == "exited"
    assert svc.list(label=label) == []
    assert svc.start(c.name).state == "running"
    assert svc.restart(c.name, timeout=2).state == "running"


def test_monitor_restarts_real_container(svc, container):
    c, label = container
    started = svc.client.api.inspect_container(c.id)["State"]["StartedAt"]
    # Threshold of -1% means "always over", so the policy fires on the first check
    mon = Monitor(svc, Policy(cpu_threshold=-1, consecutive=1, auto_restart=True), label=label)
    mon.tick()
    assert [e.kind for e in mon.events] == ["restart", "restarted"]
    assert svc.client.api.inspect_container(c.id)["State"]["StartedAt"] != started
