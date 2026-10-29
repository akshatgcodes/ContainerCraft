import pytest

from containercraft.cli import main
from containercraft.service import ContainerService
from tests.fakes import FakeClient, FakeContainer


@pytest.fixture
def svc():
    return ContainerService(
        FakeClient(
            FakeContainer("api", cpu=12.5, logs="".join(f"line {i}\n" for i in range(10))),
            FakeContainer("old-job", image="busybox", state="exited"),
        )
    )


def test_list_running_only(svc, capsys):
    assert main(["list"], svc) == 0
    out = capsys.readouterr().out
    assert "api" in out and "old-job" not in out and "0.0.0.0:8080->80/tcp" in out


def test_list_all_with_stats(svc, capsys):
    main(["ls", "-a", "--stats"], svc)
    out = capsys.readouterr().out.splitlines()
    assert out[0].split() == ["NAME", "IMAGE", "STATE", "STATUS", "PORTS", "CPU", "MEM"]
    assert "12.5%" in out[1]
    assert out[2].startswith("old-job") and out[2].rstrip().endswith("-")


def test_logs_tail(svc, capsys):
    main(["logs", "api", "--tail", "2"], svc)
    assert capsys.readouterr().out == "line 8\nline 9\n"


def test_restart_multiple_reports_missing(svc, capsys):
    assert main(["restart", "api", "ghost"], svc) == 1
    captured = capsys.readouterr()
    assert "api: running" in captured.out
    assert "ghost" in captured.err


def test_health(svc, capsys):
    assert main(["health", "api"], svc) == 0
    assert "CPU     12.5%" in capsys.readouterr().out


def test_health_of_stopped_container_fails(svc):
    assert main(["health", "old-job"], svc) == 1


def test_unknown_container_exit_code(svc, capsys):
    assert main(["inspect", "nope"], svc) == 1
    assert "nope" in capsys.readouterr().err


def test_monitor_once(svc, capsys):
    assert main(["monitor", "--once", "--threshold", "10", "--consecutive", "1"], svc) == 0
    out = capsys.readouterr().out
    assert "api: CPU 12% > 10%" in out and "auto-restart is off" in out
