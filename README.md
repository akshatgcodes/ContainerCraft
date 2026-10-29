<p align="center">
  <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24"
       fill="none" stroke="#0db7ed" stroke-width="1.5"
       stroke-linecap="round" stroke-linejoin="round">
    <path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/>
    <path d="M12 22V12"/>
    <path d="m3.3 7 7.703 4.734a2 2 0 0 0 1.994 0L20.7 7"/>
    <path d="m7.5 4.27 9 5.15"/>
  </svg>
</p>

<h1 align="center">ContainerCraft</h1>

<p align="center">
  <strong>Manage Docker containers from a friendly CLI or a REST API, with a health monitor that restarts containers stuck at high CPU or memory, and knows when to stop trying.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Docker_SDK-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker SDK">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/license-GPL--3.0-0db7ed?style=flat-square" alt="License">
</p>

---

## What is ContainerCraft?

Developer tooling, not an app: a wrapper around the Docker SDK so you can list, start, stop, restart, inspect and tail containers without remembering flags, plus an HTTP API for scripts and dashboards.

The interesting part is the **health monitor**, a small version of what Kubernetes does for you. It samples every running container, and if one stays over the CPU or memory threshold it restarts it:

```
$ python craft.py monitor --threshold 50 --interval 3 --consecutive 2 --restart --max-restarts 2
Monitoring every 3s · CPU > 50% or memory > 90% for 2 checks · auto-restart ON
15:56:07  ⚠️  cc-burner: CPU 101% > 50% (1/2 checks)
15:56:09  🔄 cc-burner: CPU 101% > 50% for 2 checks, restarting
15:56:21  ✅ cc-burner: restart complete
15:56:23  ⚠️  cc-burner: CPU 100% > 50% (1/2 checks)
15:56:25  🔄 cc-burner: CPU 101% > 50% for 2 checks, restarting
15:56:36  ✅ cc-burner: restart complete
15:56:38  ⚠️  cc-burner: CPU 101% > 50% (1/2 checks)
15:56:40  ⛔ cc-burner: CPU 100% > 50%, but already restarted 2x in 10 min. Restarting isn't fixing it; needs a human.
```

That's real output against a container running an infinite loop. A naive monitor would restart it forever.

---

## What you get

- **CLI:** `list` (with `-a`, `--stats` for live CPU/MEM, `--label`), `inspect`, `start`/`stop`/`restart` (several at once), `logs` (`--tail`, `-f`), `health`, `monitor`
- **REST API:** the same operations over HTTP, with interactive docs at `/docs`
- **Restart policy that won't make things worse:** acts only after N consecutive breaches (one spike is ignored), waits out a cooldown after each restart, and gives up after too many restarts in a 10-minute window (like Kubernetes' CrashLoopBackOff)
- **Warn-only by default:** the monitor never restarts anything unless you pass `--restart` (or set `CRAFT_AUTO_RESTART=true` for the API)
- **Safe API defaults:** read-only until you set `CRAFT_API_KEY`; once set, every endpoint needs it
- **Label scoping:** `--label app=api` limits the monitor to containers you opt in

---

## Stack

| Layer | Tech |
|---|---|
| Docker access | Docker SDK for Python (`docker`) over the local socket |
| CLI | argparse, ANSI colours (respects `NO_COLOR` and non-TTY output) |
| API | FastAPI + Uvicorn |
| Monitor | background thread, parallel stats sampling (ThreadPoolExecutor) |
| Tooling | uv · pytest (fake Docker client + real-daemon tests) · ruff · GitHub Actions |

---

## Run it

Needs a running Docker daemon (Docker Desktop, OrbStack, or Docker Engine on Linux).

```bash
uv sync

# CLI
uv run python craft.py list --stats
uv run python craft.py logs my-api --tail 50
uv run python craft.py monitor --threshold 80            # warn only
uv run python craft.py monitor --threshold 80 --restart  # self-heal

# API → http://localhost:8000/docs
CRAFT_API_KEY=change-me uv run uvicorn containercraft.api:app --reload
curl -H "X-API-Key: change-me" localhost:8000/containers
curl -X POST -H "X-API-Key: change-me" localhost:8000/containers/my-api/restart
```

More in [docs/SETUP.md](docs/SETUP.md).

---

## Engineering Decisions

**Why not restart as soon as CPU crosses the threshold?**
Builds, cache warm-ups and traffic bursts legitimately spike CPU. Requiring several consecutive breaches filters those out, and the cooldown stops a container from being restarted again before it has even warmed up.

**Why give up instead of restarting forever?**
If three restarts didn't fix it, the problem is in the code or the load, not a stuck process. Endless restarts hide that and can drop every in-flight request. The monitor says "needs a human" once and keeps watching.

**Why is the policy separate from the monitor?**
`policy.py` is pure: usage + state + time in, decision out. Every rule (cooldown, window expiry, give-up) is tested with a fake clock in milliseconds, with no Docker and no sleeping.

**What would you do differently in v2?**
Use the Docker events stream instead of polling for state changes, and respect each container's own `restart` policy and healthcheck instead of only CPU/memory.

More in [docs/DECISIONS.md](docs/DECISIONS.md).

---

## Docs

| Document | Description |
|---|---|
| [PRD](docs/PRD.md) | Product requirements: goals, user stories, non-goals |
| [Architecture](docs/ARCHITECTURE.md) | Components, monitor loop, API |
| [Decisions](docs/DECISIONS.md) | Every major technical decision and why |
| [Setup](docs/SETUP.md) | Local setup, CLI reference and env vars |
| [Deploy](docs/DEPLOY.md) | Running the API as a service |
| [Contributing](CONTRIBUTING.md) | How to propose changes |
| [Changelog](CHANGELOG.md) | What changed in each release |
| [Security](SECURITY.md) | How to report a vulnerability |

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
