# Setup

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- A running Docker daemon: Docker Desktop, [OrbStack](https://orbstack.dev) (macOS), or Docker Engine (Linux). The SDK uses `DOCKER_HOST` or `/var/run/docker.sock`.

```bash
uv sync
uv run python craft.py list      # or: uv run craft list
```

## CLI reference

| Command | What it does |
|---|---|
| `list` / `ls` `[-a] [--stats] [--label KEY[=VALUE]]` | running containers (`-a` adds stopped), optional live CPU/MEM |
| `inspect NAME` | image, state, ports, restarts, labels |
| `start` / `stop` / `restart NAME...` | one or more containers |
| `logs NAME [-n 100] [-f] [-t]` | tail, follow, timestamps |
| `health NAME` | CPU, memory, healthcheck status |
| `monitor [options]` | watch running containers |

`monitor` options: `--threshold 80` (CPU %, 100 = one core), `--mem-threshold 90`, `--interval 30`, `--consecutive 3`, `--restart`, `--cooldown 120`, `--max-restarts 3`, `--label`, `--once`, `-v`.

Try the self-healing on a throwaway container:

```bash
docker run -d --name burner --label demo=true busybox sh -c 'while :; do :; done'
uv run python craft.py monitor --label demo=true --threshold 50 --interval 3 --consecutive 2 --restart --cooldown 8 --max-restarts 2
docker rm -f burner
```

## API

```bash
CRAFT_API_KEY=change-me uv run uvicorn containercraft.api:app --reload   # http://localhost:8000/docs
```

| Variable | Default | Purpose |
|---|---|---|
| `CRAFT_API_KEY` | empty | enables writes; once set, required for every endpoint |
| `CRAFT_MONITOR` | `false` | start the monitor with the API |
| `CRAFT_CPU_THRESHOLD` | `80` | |
| `CRAFT_MEM_THRESHOLD` | `90` | |
| `CRAFT_INTERVAL` | `30` | seconds |
| `CRAFT_AUTO_RESTART` | `false` | restart instead of warn |

## Checks

```bash
uv run ruff check .
uv run pytest          # Docker integration tests skip if no daemon is reachable
```

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
