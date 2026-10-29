# Decisions

### 1. Consecutive breaches before acting
**Context:** CPU spikes are normal (builds, cache warm-up, bursts).
**Decision:** A container must be over a threshold for `consecutive` checks in a row (default 3, i.e. 90s at a 30s interval). One healthy sample resets the count.
**Trade-off:** A genuinely stuck container is detected later. Tunable per run.

### 2. Cooldown and a give-up limit
**Decision:** After a restart, no new restart for `cooldown` seconds; after `max_restarts` within a sliding 10-minute window, stop and report "needs a human".
**Why:** If restarts don't fix it, more restarts only hide the bug and drop requests. Same idea as Kubernetes' CrashLoopBackOff.

### 3. Warn-only unless asked
**Decision:** `--restart` / `CRAFT_AUTO_RESTART=true` must be set explicitly.
**Why:** Restarting a database because of a heavy query is worse than a warning. Self-healing should be a choice.

### 4. Pure policy, injectable clock
**Decision:** `decide()` takes `now` as an argument; `Monitor` takes a `clock`.
**Why:** Cooldowns and windows are tested by moving a fake clock, not by sleeping. The full policy suite runs in well under a second.

### 5. CPU percent on the `docker stats` scale
**Decision:** 100% = one full core, so a container can show 180% on two cores.
**Why:** It matches what people see in `docker stats`, so thresholds mean the same thing in both tools.
**Trade-off:** On a 16-core host an 80% threshold is less than one core. Documented on `--threshold`.

### 6. Memory excludes page cache
**Decision:** used = usage − `inactive_file` (cgroup v2) or `cache` (v1).
**Why:** Page cache is reclaimable. Counting it would make any container that reads files look nearly full and trigger restarts for nothing.

### 7. Polling with parallel sampling
**Decision:** Poll on an interval; sample containers concurrently (up to 8 threads).
**Why:** Each non-streaming stats call takes ~1s because Docker takes two readings. Sequential sampling of 20 containers would take longer than the interval.
**Trade-off:** Polling misses spikes between checks. Fine for "stuck" detection, which is the goal.

### 8. API read-only by default, key for everything once set
**Decision:** No key → reads only. Key set → every endpoint needs it.
**Why:** Docker control is close to root on the host; logs and labels can hold secrets. A forgotten env var should fail safe.

### 9. One service layer for CLI and API
**Decision:** Both call `ContainerService`, which tests construct with a fake client.
**Why:** Same behaviour and errors everywhere, and most tests run without Docker. Real-daemon tests live in one file that skips when Docker is absent.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
