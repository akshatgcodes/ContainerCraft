import type { Site } from "./types";

export const site: Site = {
  name: "ContainerCraft",
  letter: "C",
  title: "ContainerCraft — a Docker CLI that knows when to stop restarting",
  description:
    "Manage Docker containers from a friendly CLI or a REST API, with a health monitor that restarts containers stuck at high CPU or memory, and knows when to stop trying.",
  meta: ["CLI + REST API", "Docker SDK for Python", "GPLv3"],
  headline: ["Self-healing containers that", "know when to give up."],
  intro:
    "A wrapper around the Docker SDK: list, start, stop, restart, inspect and tail containers without remembering flags, plus an HTTP API for scripts. Its health monitor restarts containers stuck at high CPU or memory, a small version of what Kubernetes does for you.",
  primary: { label: "Install it", href: "#run-it" },
  repo: "https://github.com/akshatgcodes/ContainerCraft",
  xfactor: {
    title: "A restart policy that won't make things worse.",
    intro:
      "A naive monitor restarts a broken container forever and hides the real problem. ContainerCraft's policy is the part that's actually designed.",
    features: [
      {
        icon: "⚠",
        title: "N breaches, not one spike",
        body: "Builds and cache warm-ups spike CPU legitimately. The monitor acts only after several consecutive checks over the threshold.",
      },
      {
        icon: "⏱",
        title: "Cooldown after restart",
        body: "A restarted container gets time to warm up before it can be judged again, so it isn't restarted twice for the same load.",
      },
      {
        icon: "⛔",
        title: "Gives up, says why",
        body: "Too many restarts in a 10-minute window and it stops, like Kubernetes' CrashLoopBackOff: \"Restarting isn't fixing it; needs a human.\"",
      },
    ],
  },
  preview: {
    intro: "Real output against a container running an infinite loop: two restarts, then the monitor stops trying.",
    terminal: `$ python craft.py monitor --threshold 50 --interval 3 --consecutive 2 --restart --max-restarts 2
Monitoring every 3s · CPU > 50% or memory > 90% for 2 checks · auto-restart ON
15:56:07  ⚠️  cc-burner: CPU 101% > 50% (1/2 checks)
15:56:09  🔄 cc-burner: CPU 101% > 50% for 2 checks, restarting
15:56:21  ✅ cc-burner: restart complete
15:56:23  ⚠️  cc-burner: CPU 100% > 50% (1/2 checks)
15:56:25  🔄 cc-burner: CPU 101% > 50% for 2 checks, restarting
15:56:36  ✅ cc-burner: restart complete
15:56:38  ⚠️  cc-burner: CPU 101% > 50% (1/2 checks)
15:56:40  ⛔ cc-burner: CPU 100% > 50%, but already restarted 2x in 10 min.
             Restarting isn't fixing it; needs a human.`,
  },
  stack: ["Python 3", "Docker SDK", "argparse", "FastAPI", "Uvicorn", "ThreadPoolExecutor", "uv", "pytest", "ruff"],
  concepts: [
    { title: "Pure restart policy", body: "`policy.py` takes usage, state and time and returns a decision. Cooldown, window expiry and give-up are tested with a fake clock: no Docker, no sleeping." },
    { title: "Warn-only by default", body: "The monitor never restarts anything unless you pass `--restart` (or set `CRAFT_AUTO_RESTART=true` for the API)." },
    { title: "Read-only API until keyed", body: "The REST API refuses changes until `CRAFT_API_KEY` is set; once set, every endpoint needs it." },
    { title: "Parallel sampling", body: "Stats for every running container are sampled at once with a thread pool, so one slow container doesn't stall the loop." },
    { title: "Label scoping", body: "`--label app=api` limits the monitor to the containers you opt in." },
    { title: "Tested against a real daemon", body: "Unit tests use a fake Docker client; integration tests start real containers when a daemon is available." },
  ],
  run: {
    title: "Install and run",
    intro: "Needs a running Docker daemon: Docker Desktop, OrbStack, or Docker Engine on Linux.",
    blocks: [
      {
        title: "CLI",
        steps: [
          { text: "Clone and install:", cmd: "git clone https://github.com/akshatgcodes/ContainerCraft\ncd ContainerCraft && uv sync" },
          { text: "List containers with live CPU and memory:", cmd: "uv run python craft.py list --stats" },
          { text: "Watch them, restarting when stuck:", cmd: "uv run python craft.py monitor --threshold 80 --restart" },
        ],
      },
      {
        title: "REST API",
        steps: [
          { text: "Start it with a key (docs at `/docs`):", cmd: "CRAFT_API_KEY=change-me \\\n  uv run uvicorn containercraft.api:app" },
          { text: "Call it:", cmd: 'curl -H "X-API-Key: change-me" \\\n  localhost:8000/containers' },
        ],
      },
    ],
  },
  tagline: "a Docker CLI and API with a careful health monitor.",
};
