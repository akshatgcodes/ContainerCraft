"""An in-memory stand-in for docker.DockerClient, just enough for ContainerService."""

from docker.errors import NotFound


def stats_sample(cpu_percent: float = 5.0, mem_used: int = 50, mem_limit: int = 1000) -> dict:
    """Build a raw stats dict that works out to the given CPU % on a 2-CPU host."""
    system_delta = 1_000_000
    cpu_delta = int(cpu_percent / 100 / 2 * system_delta)
    return {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 10_000 + cpu_delta},
            "system_cpu_usage": 5_000_000 + system_delta,
            "online_cpus": 2,
        },
        "precpu_stats": {"cpu_usage": {"total_usage": 10_000}, "system_cpu_usage": 5_000_000},
        "memory_stats": {
            "usage": mem_used + 10,
            "limit": mem_limit,
            "stats": {"inactive_file": 10},
        },
    }


class FakeImage:
    def __init__(self, tag):
        self.tags = [tag]
        self.short_id = "sha256:abc"


class FakeContainer:
    def __init__(self, name, image="nginx:alpine", state="running", labels=None, cpu=5.0, logs=""):
        self.name = name
        self.short_id = f"{abs(hash(name)) % 10**12:012d}"
        self.image = FakeImage(image)
        self.labels = labels or {}
        self.cpu = cpu
        self._logs = logs
        self.calls: list[str] = []
        self.restart_error: Exception | None = None
        self._state = state

    @property
    def status(self):
        return self._state

    @property
    def attrs(self):
        return {
            "State": {
                "Status": self._state,
                "ExitCode": 0,
                "StartedAt": "2024-08-01T10:00:00.000000000Z",
                "FinishedAt": "2024-08-01T11:00:00.000000000Z",
            },
            "Config": {"Image": self.image.tags[0], "Labels": self.labels},
            "NetworkSettings": {"Ports": {"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}},
            "RestartCount": 0,
        }

    def start(self):
        self.calls.append("start")
        self._state = "running"

    def stop(self, timeout=10):
        self.calls.append("stop")
        self._state = "exited"

    def restart(self, timeout=10):
        if self.restart_error:
            raise self.restart_error
        self.calls.append("restart")
        self._state = "running"

    def reload(self):
        pass

    def logs(self, tail=100, timestamps=False, stream=False, follow=False):
        lines = self._logs.splitlines(keepends=True)[-tail:]
        if stream:
            return iter(line.encode() for line in lines)
        return "".join(lines).encode()

    def stats(self, stream=False):
        return stats_sample(self.cpu)


class FakeContainers:
    def __init__(self, containers):
        self.by_name = {c.name: c for c in containers}

    def get(self, ref):
        for c in self.by_name.values():
            if ref in (c.name, c.short_id):
                return c
        raise NotFound(f"No such container: {ref}")

    def list(self, all=False, filters=None):
        out = [c for c in self.by_name.values() if all or c.status == "running"]
        if filters and filters.get("label"):
            key, _, value = filters["label"].partition("=")
            out = [c for c in out if key in c.labels and (not value or c.labels[key] == value)]
        return out


class FakeClient:
    def __init__(self, *containers):
        self.containers = FakeContainers(containers)
