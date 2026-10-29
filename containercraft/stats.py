"""Turn a raw `docker stats` sample into CPU and memory percentages.

Pure functions over the stats JSON, so the maths is testable without a daemon.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    cpu_percent: float  # same scale as `docker stats`: 100% = one full core
    mem_percent: float
    mem_used: int  # bytes
    mem_limit: int  # bytes


def cpu_percent(stats: dict) -> float:
    cpu = stats.get("cpu_stats") or {}
    pre = stats.get("precpu_stats") or {}
    cpu_delta = (cpu.get("cpu_usage") or {}).get("total_usage", 0) - (
        pre.get("cpu_usage") or {}
    ).get("total_usage", 0)
    system_delta = cpu.get("system_cpu_usage", 0) - pre.get("system_cpu_usage", 0)
    if cpu_delta <= 0 or system_delta <= 0:
        return 0.0
    cpus = (
        cpu.get("online_cpus") or len((cpu.get("cpu_usage") or {}).get("percpu_usage") or []) or 1
    )
    return cpu_delta / system_delta * cpus * 100


def memory(stats: dict) -> tuple[int, int]:
    """(used, limit) in bytes. Page cache is excluded like `docker stats` does: it's
    reclaimable, so counting it would make every file-heavy container look full."""
    mem = stats.get("memory_stats") or {}
    usage = mem.get("usage", 0)
    detail = mem.get("stats") or {}
    # cgroup v2 reports inactive_file, v1 reports cache
    cache = detail.get("inactive_file", detail.get("cache", 0))
    return max(usage - cache, 0), mem.get("limit", 0)


def usage(stats: dict) -> Usage:
    used, limit = memory(stats)
    return Usage(
        cpu_percent=round(cpu_percent(stats), 1),
        mem_percent=round(used / limit * 100, 1) if limit else 0.0,
        mem_used=used,
        mem_limit=limit,
    )


def human_bytes(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TiB"
