from containercraft.stats import cpu_percent, human_bytes, memory, usage
from tests.fakes import stats_sample


def test_cpu_percent_matches_docker_formula():
    # cpu_delta / system_delta * online_cpus * 100
    assert round(cpu_percent(stats_sample(cpu_percent=87)), 1) == 87.0


def test_cpu_can_exceed_100_on_multiple_cores():
    assert round(cpu_percent(stats_sample(cpu_percent=180))) == 180


def test_cpu_zero_when_no_previous_sample():
    s = stats_sample(50)
    s["precpu_stats"] = {}
    s["cpu_stats"]["system_cpu_usage"] = 0
    assert cpu_percent(s) == 0.0


def test_cpu_falls_back_to_percpu_count():
    s = stats_sample(40)
    del s["cpu_stats"]["online_cpus"]
    s["cpu_stats"]["cpu_usage"]["percpu_usage"] = [1, 1]
    assert round(cpu_percent(s)) == 40


def test_memory_excludes_page_cache_v2_and_v1():
    v2 = {"memory_stats": {"usage": 500, "limit": 1000, "stats": {"inactive_file": 100}}}
    v1 = {"memory_stats": {"usage": 500, "limit": 1000, "stats": {"cache": 200}}}
    assert memory(v2) == (400, 1000)
    assert memory(v1) == (300, 1000)


def test_usage_handles_missing_limit():
    u = usage({"memory_stats": {"usage": 10}})
    assert u.mem_percent == 0.0 and u.cpu_percent == 0.0


def test_human_bytes():
    assert human_bytes(512) == "512B"
    assert human_bytes(8 * 1024**2) == "8.0MiB"
    assert human_bytes(3 * 1024**3) == "3.0GiB"
