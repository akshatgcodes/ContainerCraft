"""REST interface over the same ContainerService the CLI uses.

Controlling Docker over HTTP is close to handing out root on the host, so:
- with no CRAFT_API_KEY set, the API is read-only (writes return 403)
- with a key set, every endpoint requires it in the X-API-Key header
Bind it to localhost unless it sits behind something that adds TLS.
"""

import os
import secrets
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from containercraft.monitor import Monitor
from containercraft.policy import Policy
from containercraft.service import (
    ContainerNotFound,
    ContainerService,
    DockerUnavailable,
    NotRunning,
)


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


def policy_from_env() -> Policy:
    return Policy(
        cpu_threshold=float(os.environ.get("CRAFT_CPU_THRESHOLD", 80)),
        mem_threshold=float(os.environ.get("CRAFT_MEM_THRESHOLD", 90)),
        auto_restart=_env_bool("CRAFT_AUTO_RESTART"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.api_key = os.environ.get("CRAFT_API_KEY", "")
    if getattr(app.state, "service", None) is None:
        try:
            app.state.service = ContainerService()
        except DockerUnavailable:
            app.state.service = None  # endpoints answer 503 until restarted with Docker up
    app.state.monitor = None
    if app.state.service is not None:
        app.state.monitor = Monitor(
            app.state.service,
            policy_from_env(),
            interval=float(os.environ.get("CRAFT_INTERVAL", 30)),
        )
        if _env_bool("CRAFT_MONITOR"):
            app.state.monitor.start()
    yield
    if app.state.monitor:
        app.state.monitor.stop()


app = FastAPI(
    title="ContainerCraft API",
    version="0.1.0",
    description="Manage Docker containers over HTTP. Writes need X-API-Key.",
    lifespan=lifespan,
)


@app.exception_handler(ContainerNotFound)
def _not_found(_: Request, e: ContainerNotFound):
    return JSONResponse({"detail": str(e)}, status_code=404)


@app.exception_handler(NotRunning)
def _not_running(_: Request, e: NotRunning):
    return JSONResponse({"detail": str(e)}, status_code=409)


def service(request: Request) -> ContainerService:
    svc = request.app.state.service
    if svc is None:
        raise HTTPException(503, "Docker daemon unavailable")
    return svc


def _key_ok(request: Request, given: str | None) -> bool:
    expected = request.app.state.api_key
    return bool(expected and given and secrets.compare_digest(given, expected))


def read_access(request: Request, x_api_key: str | None = Header(None)) -> None:
    # Once a key exists, reads need it too: logs and labels can contain secrets
    if request.app.state.api_key and not _key_ok(request, x_api_key):
        raise HTTPException(401, "Missing or wrong X-API-Key")


def write_access(request: Request, x_api_key: str | None = Header(None)) -> None:
    if not request.app.state.api_key:
        raise HTTPException(403, "API is read-only: set CRAFT_API_KEY to enable writes")
    if not _key_ok(request, x_api_key):
        raise HTTPException(401, "Missing or wrong X-API-Key")


@app.get("/health")
def api_health() -> dict:
    return {"ok": True}


@app.get("/containers", dependencies=[Depends(read_access)])
def list_containers(
    all: bool = Query(False, description="include stopped containers"),
    label: str | None = None,
    svc: ContainerService = Depends(service),
) -> list[dict]:
    return [c.to_dict() for c in svc.list(all=all, label=label)]


@app.get("/containers/{ref}", dependencies=[Depends(read_access)])
def get_container(ref: str, svc: ContainerService = Depends(service)) -> dict:
    return svc.inspect(ref).to_dict()


@app.post("/containers/{ref}/start", dependencies=[Depends(write_access)])
def start(ref: str, svc: ContainerService = Depends(service)) -> dict:
    return svc.start(ref).to_dict()


@app.post("/containers/{ref}/stop", dependencies=[Depends(write_access)])
def stop(
    ref: str, timeout: int = Query(10, ge=0, le=300), svc: ContainerService = Depends(service)
):
    return svc.stop(ref, timeout=timeout).to_dict()


@app.post("/containers/{ref}/restart", dependencies=[Depends(write_access)])
def restart(
    ref: str, timeout: int = Query(10, ge=0, le=300), svc: ContainerService = Depends(service)
) -> dict:
    return svc.restart(ref, timeout=timeout).to_dict()


@app.get(
    "/containers/{ref}/logs", response_class=PlainTextResponse, dependencies=[Depends(read_access)]
)
def logs(
    ref: str, tail: int = Query(100, ge=1, le=10_000), svc: ContainerService = Depends(service)
):
    return svc.logs(ref, tail=tail)


@app.get("/containers/{ref}/health", dependencies=[Depends(read_access)])
def health(ref: str, svc: ContainerService = Depends(service)) -> dict:
    info = svc.inspect(ref)
    out = {"container": info.to_dict(), "usage": None}
    if info.state == "running":
        out["usage"] = asdict(svc.usage(info.id))
    return out


def _monitor(request: Request) -> Monitor:
    mon = request.app.state.monitor
    if mon is None:
        raise HTTPException(503, "Docker daemon unavailable")
    return mon


@app.get("/monitor", dependencies=[Depends(read_access)])
def monitor_status(limit: int = Query(50, ge=1, le=500), mon: Monitor = Depends(_monitor)) -> dict:
    return {
        "running": mon.running,
        "interval": mon.interval,
        "policy": asdict(mon.policy),
        "latest": mon.last_sample,
        "events": [e.to_dict() for e in list(mon.events)[-limit:]][::-1],
    }


@app.post("/monitor/start", dependencies=[Depends(write_access)])
def monitor_start(mon: Monitor = Depends(_monitor)) -> dict:
    mon.start()
    return {"running": True}


@app.post("/monitor/stop", dependencies=[Depends(write_access)])
def monitor_stop(mon: Monitor = Depends(_monitor)) -> dict:
    mon.stop()
    return {"running": False}
