# Architecture

```
  craft.py / `craft` CLI          FastAPI app (containercraft.api)
  argparse commands               /containers · /monitor · X-API-Key
           │                                   │
           └──────────────┬────────────────────┘
                          ▼
                ContainerService (service.py)          Monitor (monitor.py)
                list · inspect · start/stop/restart ◀── background thread
                logs · usage · usage_many (parallel)    tick(): sample → decide → act
                          │                                    │
                          ▼                                    ▼
                docker SDK → /var/run/docker.sock       policy.py (pure)
                                                         decide() · record_restart()
                                                         stats.py (pure)
                                                         cpu % · memory − page cache
```

## Components

| Module | Role |
|---|---|
| `stats.py` | CPU % from `cpu_delta / system_delta × online_cpus × 100` (same as `docker stats`, so 100% = one core). Memory = usage minus page cache (`inactive_file` on cgroup v2, `cache` on v1) over the limit. |
| `service.py` | One place for Docker calls; maps SDK objects to `ContainerInfo`, turns SDK errors into `ContainerNotFound` / `NotRunning` / `DockerUnavailable`. `usage_many` samples in parallel because each `stats()` call blocks ~1s. |
| `policy.py` | `Policy` (thresholds, consecutive, cooldown, max restarts, window) and `decide()`, which returns `ok` / `warn` / `restart` / `suppressed`. No I/O. |
| `monitor.py` | `Monitor.tick()` lists running containers (optionally by label), samples them, applies the policy, restarts, and records `Event`s in a bounded deque. `start()` runs ticks on a daemon thread at a steady cadence. |
| `cli.py` | argparse subcommands, table output, coloured states and events. |
| `api.py` | FastAPI routes, API-key dependencies, monitor lifecycle in the app lifespan. |

## Monitor tick

1. `service.list(label=…)` → running containers; forget state for containers that disappeared
2. `usage_many` → `Usage` per container (or the exception if one vanished mid-sample)
3. For each: `decide(policy, state, usage, now)`
   - under thresholds → reset the breach counter → `ok`
   - over, fewer than `consecutive` checks → `warn`
   - auto-restart off → `warn`
   - restarted less than `cooldown` ago → `suppressed` (code `cooldown`)
   - `max_restarts` already within `window` → `suppressed` (code `gave_up`)
   - else → `restart`
4. On `restart`: call `service.restart`, then `record_restart`; a failure becomes an `error` event
5. Repeated `suppressed` events with the same code are emitted once

## API

| Method | Path | Access |
|---|---|---|
| GET | `/health` | open |
| GET | `/containers?all=&label=` | read |
| GET | `/containers/{ref}` | read |
| POST | `/containers/{ref}/start` · `/stop?timeout=` · `/restart?timeout=` | write |
| GET | `/containers/{ref}/logs?tail=` (text) | read |
| GET | `/containers/{ref}/health` | read |
| GET | `/monitor?limit=` | read |
| POST | `/monitor/start` · `/monitor/stop` | write |

**Read**: open when `CRAFT_API_KEY` is unset, otherwise needs `X-API-Key`. **Write**: always needs the key; 403 when no key is configured.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
