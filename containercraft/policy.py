"""When should the monitor restart a container? Pure decision logic, no Docker.

Restarting on every spike would be worse than doing nothing: a build step or a cache
warm-up legitimately pegs the CPU for a few seconds. So a container must stay over the
threshold for several checks in a row, a restarted container gets a cooldown, and after
too many restarts in a window the monitor gives up and says so (the same idea as
Kubernetes' CrashLoopBackOff), instead of restarting forever.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Literal

from containercraft.stats import Usage

Kind = Literal["ok", "warn", "restart", "suppressed"]


@dataclass(frozen=True)
class Policy:
    cpu_threshold: float = 80.0
    mem_threshold: float = 90.0
    consecutive: int = 3  # checks over threshold before acting
    auto_restart: bool = False
    cooldown: float = 120.0  # seconds after a restart before another is allowed
    max_restarts: int = 3  # within `window`
    window: float = 600.0


@dataclass
class State:
    breaches: int = 0
    restarts: deque[float] = field(default_factory=deque)


@dataclass(frozen=True)
class Decision:
    kind: Kind
    reason: str
    # Finer than kind: tells "cooling down" apart from "gave up" (both suppressed)
    code: str = ""


def breach_reason(policy: Policy, u: Usage) -> str | None:
    parts = []
    if u.cpu_percent > policy.cpu_threshold:
        parts.append(f"CPU {u.cpu_percent:.0f}% > {policy.cpu_threshold:.0f}%")
    if u.mem_percent > policy.mem_threshold:
        parts.append(f"memory {u.mem_percent:.0f}% > {policy.mem_threshold:.0f}%")
    return ", ".join(parts) or None


def decide(policy: Policy, state: State, u: Usage, now: float) -> Decision:
    """Update `state` with this sample and say what to do. The caller performs the restart
    and must call `record_restart` if it succeeded."""
    reason = breach_reason(policy, u)
    if reason is None:
        state.breaches = 0
        return Decision("ok", f"CPU {u.cpu_percent:.0f}%, memory {u.mem_percent:.0f}%")

    state.breaches += 1
    if state.breaches < policy.consecutive:
        return Decision("warn", f"{reason} ({state.breaches}/{policy.consecutive} checks)")
    if not policy.auto_restart:
        return Decision("warn", f"{reason} for {state.breaches} checks (auto-restart is off)")

    while state.restarts and now - state.restarts[0] > policy.window:
        state.restarts.popleft()
    if state.restarts and now - state.restarts[-1] < policy.cooldown:
        left = policy.cooldown - (now - state.restarts[-1])
        return Decision(
            "suppressed", f"{reason}, but restarted recently (cooldown {left:.0f}s)", "cooldown"
        )
    if len(state.restarts) >= policy.max_restarts:
        return Decision(
            "suppressed",
            f"{reason}, but already restarted {len(state.restarts)}x in "
            f"{policy.window / 60:.0f} min. Restarting isn't fixing it; needs a human.",
            "gave_up",
        )
    return Decision("restart", f"{reason} for {state.breaches} checks, restarting")


def record_restart(state: State, now: float) -> None:
    state.restarts.append(now)
    state.breaches = 0
