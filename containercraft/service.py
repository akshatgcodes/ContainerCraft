"""Thin layer over the Docker SDK. The CLI and the API both go through this, so they
behave the same and tests can swap in a fake client."""

# Lazy annotations: the class has a `list` method that would shadow the builtin otherwise
from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import docker
from docker.errors import NotFound

from containercraft.stats import Usage, usage


class ContainerNotFound(Exception):
    pass


class DockerUnavailable(Exception):
    pass


class NotRunning(Exception):
    pass


@dataclass
class ContainerInfo:
    id: str
    name: str
    image: str
    state: str  # running | exited | paused | restarting | created | dead
    status: str  # human text, e.g. "Up 3 minutes"
    health: str | None  # from the image's HEALTHCHECK, if it has one
    ports: list[str]
    restart_count: int
    labels: dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)


def _ports(attrs: dict) -> list[str]:
    out = []
    for container_port, bindings in (attrs.get("NetworkSettings", {}).get("Ports") or {}).items():
        for b in bindings or []:
            out.append(f"{b.get('HostIp') or '0.0.0.0'}:{b['HostPort']}->{container_port}")
    return sorted(set(out))


def _info(c) -> ContainerInfo:
    attrs = c.attrs
    state = attrs.get("State", {})
    image = attrs.get("Config", {}).get("Image") or (
        c.image.tags[0] if c.image.tags else c.image.short_id
    )
    return ContainerInfo(
        id=c.short_id,
        name=c.name,
        image=image,
        state=state.get("Status", c.status),
        status=_status_text(state),
        health=(state.get("Health") or {}).get("Status"),
        ports=_ports(attrs),
        restart_count=attrs.get("RestartCount", 0),
        labels=attrs.get("Config", {}).get("Labels") or {},
    )


def _ago(iso: str | None, now: datetime | None = None) -> str | None:
    """'2024-08-03T10:00:00.123456789Z' -> '3m'. Docker timestamps have nanoseconds."""
    if not iso or iso.startswith("0001-"):
        return None
    when = datetime.fromisoformat(iso[:19]).replace(tzinfo=UTC)
    secs = int(((now or datetime.now(UTC)) - when).total_seconds())
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{secs // size}{unit}"
    return f"{max(secs, 0)}s"


def _status_text(state: dict) -> str:
    s = state.get("Status", "unknown")
    if s == "running":
        up = _ago(state.get("StartedAt"))
        return f"up {up}" if up else "up"
    if s == "exited":
        ago = _ago(state.get("FinishedAt"))
        return f"exited ({state.get('ExitCode', '?')})" + (f" {ago} ago" if ago else "")
    return s


class ContainerService:
    def __init__(self, client=None):
        if client is None:
            try:
                client = docker.from_env()
                client.ping()
            except Exception as e:  # noqa: BLE001 — any connection failure means the same thing
                raise DockerUnavailable(
                    "Can't reach the Docker daemon. Is Docker (or OrbStack) running?"
                ) from e
        self.client = client

    def _get(self, ref: str):
        try:
            return self.client.containers.get(ref)
        except NotFound as e:
            raise ContainerNotFound(f"No container named or with id {ref!r}") from e

    def list(self, all: bool = False, label: str | None = None) -> list[ContainerInfo]:
        filters = {"label": label} if label else None
        containers = self.client.containers.list(all=all, filters=filters)
        return sorted((_info(c) for c in containers), key=lambda i: (i.state != "running", i.name))

    def inspect(self, ref: str) -> ContainerInfo:
        return _info(self._get(ref))

    def start(self, ref: str) -> ContainerInfo:
        c = self._get(ref)
        c.start()
        c.reload()
        return _info(c)

    def stop(self, ref: str, timeout: int = 10) -> ContainerInfo:
        c = self._get(ref)
        c.stop(timeout=timeout)
        c.reload()
        return _info(c)

    def restart(self, ref: str, timeout: int = 10) -> ContainerInfo:
        c = self._get(ref)
        c.restart(timeout=timeout)
        c.reload()
        return _info(c)

    def logs(self, ref: str, tail: int = 100, timestamps: bool = False) -> str:
        raw = self._get(ref).logs(tail=tail, timestamps=timestamps)
        return raw.decode("utf-8", errors="replace")

    def follow_logs(self, ref: str, tail: int = 20) -> Iterator[str]:
        for chunk in self._get(ref).logs(tail=tail, stream=True, follow=True):
            yield chunk.decode("utf-8", errors="replace")

    def usage(self, ref: str) -> Usage:
        c = self._get(ref)
        if c.status != "running":
            raise NotRunning(f"{c.name} is {c.status}; stats need a running container")
        # stream=False makes Docker take two readings ~1s apart, so precpu is filled in
        return usage(c.stats(stream=False))

    def usage_many(self, infos: list[ContainerInfo]) -> dict[str, Usage | Exception]:
        """Each stats call blocks ~1s, so sample all containers in parallel."""
        if not infos:
            return {}
        with ThreadPoolExecutor(max_workers=min(8, len(infos))) as pool:
            futures = {i.name: pool.submit(self.usage, i.id) for i in infos}
        out: dict[str, Usage | Exception] = {}
        for name, f in futures.items():
            try:
                out[name] = f.result()
            except Exception as e:  # noqa: BLE001 — a container can vanish mid-sample
                out[name] = e
        return out
