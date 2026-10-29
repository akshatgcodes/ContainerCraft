"""Background health monitor: sample every running container on an interval, apply the
restart policy, and keep a short history of events."""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from containercraft.policy import Decision, Policy, State, decide, record_restart
from containercraft.service import ContainerService
from containercraft.stats import Usage

log = logging.getLogger("containercraft.monitor")


@dataclass
class Event:
    time: str
    container: str
    kind: str  # ok | warn | restart | restarted | suppressed | error
    message: str
    cpu_percent: float | None = None
    mem_percent: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class Monitor:
    def __init__(
        self,
        service: ContainerService,
        policy: Policy,
        interval: float = 30.0,
        label: str | None = None,
        on_event: Callable[[Event], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.service = service
        self.policy = policy
        self.interval = interval
        self.label = label
        self.on_event = on_event
        self.clock = clock
        self.states: dict[str, State] = {}
        self.events: deque[Event] = deque(maxlen=500)
        self.last_sample: dict[str, dict] = {}
        self._last_kind: dict[str, str] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _emit(self, name: str, kind: str, message: str, u: Usage | None = None) -> None:
        event = Event(
            time=datetime.now(UTC).isoformat(timespec="seconds"),
            container=name,
            kind=kind,
            message=message,
            cpu_percent=u.cpu_percent if u else None,
            mem_percent=u.mem_percent if u else None,
        )
        # "ok" samples are only kept as the latest reading, not as history
        if kind != "ok":
            self.events.append(event)
        if self.on_event:
            self.on_event(event)

    def tick(self) -> None:
        """One round of sampling. Called by the loop, and directly by tests."""
        running = self.service.list(label=self.label)
        names = {c.name for c in running}
        # Forget containers that are gone so a recreated one starts fresh
        for gone in set(self.states) - names:
            del self.states[gone]
            self.last_sample.pop(gone, None)
            self._last_kind.pop(gone, None)

        samples = self.service.usage_many(running)
        now = self.clock()
        for c in running:
            u = samples.get(c.name)
            if isinstance(u, Exception) or u is None:
                self._emit(c.name, "error", f"couldn't read stats: {u}")
                continue
            self.last_sample[c.name] = {"cpu_percent": u.cpu_percent, "mem_percent": u.mem_percent}
            state = self.states.setdefault(c.name, State())
            d: Decision = decide(self.policy, state, u, now)
            # Say "cooling down" / "giving up" once, not on every tick until it changes
            code = d.code or d.kind
            repeat = d.kind == "suppressed" and self._last_kind.get(c.name) == code
            self._last_kind[c.name] = code
            if not repeat:
                self._emit(c.name, d.kind, d.reason, u)
            if d.kind == "restart":
                try:
                    self.service.restart(c.id)
                    record_restart(state, now)
                    self._emit(c.name, "restarted", "restart complete")
                except Exception as e:  # noqa: BLE001 — report and keep monitoring others
                    self._emit(c.name, "error", f"restart failed: {e}")

    def _loop(self) -> None:
        while not self._stop.is_set():
            started = self.clock()
            try:
                self.tick()
            except Exception:  # noqa: BLE001 — a daemon hiccup must not kill the thread
                log.exception("monitor tick failed")
            # Keep a steady cadence even though sampling itself takes ~1s
            self._stop.wait(max(0.0, self.interval - (self.clock() - started)))

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="craft-monitor", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())
