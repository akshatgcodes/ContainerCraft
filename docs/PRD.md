# PRD: ContainerCraft

## Problem

Day-to-day Docker work means remembering flags (`docker ps -a --format …`, `docker logs --tail 50 -f`) and noticing by hand when a container is stuck at 100% CPU. Kubernetes solves the second problem, but it's heavy for a single machine running a few containers.

## Goal

A small tool for one Docker host: friendly commands for common tasks, an HTTP API for scripts, and a monitor that heals stuck containers without making outages worse.

## Users

- A developer running a local or single-server Docker stack
- A CI script or dashboard that needs to restart or inspect containers over HTTP

## User stories

| As a… | I want to… | So that… |
|---|---|---|
| developer | see containers with live CPU/memory in one table | I spot the hungry one at a glance |
| developer | tail logs and restart several containers with one command | I don't look up flags |
| developer | be warned when a container stays over a threshold | I notice before users do |
| developer | opt in to automatic restarts | a stuck process recovers on its own |
| developer | have the monitor stop restarting when it isn't helping | a broken image doesn't flap all night |
| script | call `POST /containers/{id}/restart` with a key | CI can recover a service |

## Requirements

- CLI: list (all, stats, label filter), inspect, start/stop/restart, logs (tail, follow), health, monitor
- API: list, get, start/stop/restart, logs, health, monitor status/start/stop
- Monitor: CPU and memory thresholds, N consecutive breaches, warn-only by default, cooldown, max restarts per window, label filter
- API is read-only without a key, fully protected with one
- Clear errors when Docker isn't running or a container doesn't exist (exit code 1 / 404)

## Non-goals

- Multiple hosts, scheduling, or replacing Docker Compose/Kubernetes
- Creating or building containers and images
- Persistent event history (in memory only)

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
