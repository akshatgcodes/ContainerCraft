import pytest
from fastapi.testclient import TestClient

from containercraft.api import app
from containercraft.service import ContainerService
from tests.fakes import FakeClient, FakeContainer

KEY = "s3cret-key"


@pytest.fixture
def containers():
    return [FakeContainer("api", cpu=30, logs="a\nb\nc\n"), FakeContainer("job", state="exited")]


def client_with(monkeypatch, containers, key=""):
    monkeypatch.setenv("CRAFT_API_KEY", key)
    monkeypatch.delenv("CRAFT_MONITOR", raising=False)
    app.state.service = ContainerService(FakeClient(*containers))
    return TestClient(app)


def test_read_only_without_key(monkeypatch, containers):
    with client_with(monkeypatch, containers) as c:
        assert [x["name"] for x in c.get("/containers").json()] == ["api"]
        assert len(c.get("/containers", params={"all": True}).json()) == 2
        r = c.post("/containers/api/restart")
        assert r.status_code == 403 and "read-only" in r.json()["detail"]
    assert containers[0].calls == []


def test_key_required_everywhere_once_set(monkeypatch, containers):
    with client_with(monkeypatch, containers, KEY) as c:
        assert c.get("/containers").status_code == 401
        assert c.post("/containers/api/restart", headers={"X-API-Key": "wrong"}).status_code == 401
        r = c.post("/containers/api/restart", headers={"X-API-Key": KEY})
        assert r.status_code == 200 and r.json()["state"] == "running"
    assert containers[0].calls == ["restart"]


def test_stop_start(monkeypatch, containers):
    h = {"X-API-Key": KEY}
    with client_with(monkeypatch, containers, KEY) as c:
        assert c.post("/containers/api/stop", headers=h).json()["state"] == "exited"
        assert c.post("/containers/api/start", headers=h).json()["state"] == "running"


def test_logs_and_health(monkeypatch, containers):
    with client_with(monkeypatch, containers) as c:
        assert c.get("/containers/api/logs", params={"tail": 2}).text == "b\nc\n"
        h = c.get("/containers/api/health").json()
        assert h["usage"]["cpu_percent"] == 30.0
        assert c.get("/containers/job/health").json()["usage"] is None


def test_not_found(monkeypatch, containers):
    with client_with(monkeypatch, containers) as c:
        assert c.get("/containers/ghost").status_code == 404


def test_monitor_endpoints(monkeypatch, containers):
    h = {"X-API-Key": KEY}
    with client_with(monkeypatch, containers, KEY) as c:
        status = c.get("/monitor", headers=h).json()
        assert status["running"] is False and status["policy"]["cpu_threshold"] == 80
        assert c.post("/monitor/start", headers=h).json() == {"running": True}
        assert c.post("/monitor/stop", headers=h).json() == {"running": False}
