from containercraft.policy import Policy, State, decide, record_restart
from containercraft.stats import Usage

HOT = Usage(cpu_percent=95, mem_percent=10, mem_used=1, mem_limit=10)
COOL = Usage(cpu_percent=5, mem_percent=10, mem_used=1, mem_limit=10)
FULL = Usage(cpu_percent=5, mem_percent=97, mem_used=1, mem_limit=10)

AUTO = Policy(
    cpu_threshold=80, consecutive=3, auto_restart=True, cooldown=60, max_restarts=2, window=600
)


def run(policy, samples, start=0.0, step=10.0, state=None):
    state = state or State()
    out = []
    for n, u in enumerate(samples):
        d = decide(policy, state, u, start + n * step)
        if d.kind == "restart":
            record_restart(state, start + n * step)
        out.append(d.kind)
    return out, state


def test_single_spike_only_warns():
    kinds, _ = run(AUTO, [HOT, COOL, HOT, COOL])
    assert kinds == ["warn", "ok", "warn", "ok"]


def test_restart_after_consecutive_breaches():
    kinds, state = run(AUTO, [HOT, HOT, HOT])
    assert kinds == ["warn", "warn", "restart"]
    assert state.breaches == 0 and len(state.restarts) == 1


def test_memory_breach_counts_too():
    d = decide(AUTO, State(), FULL, 0)
    assert d.kind == "warn" and "memory 97%" in d.reason


def test_warn_only_without_auto_restart():
    kinds, _ = run(Policy(consecutive=2), [HOT, HOT, HOT])
    assert kinds == ["warn", "warn", "warn"]


def test_cooldown_blocks_immediate_second_restart():
    # restart at t=20, then 3 more breaches by t=50: still inside the 60s cooldown
    kinds, _ = run(AUTO, [HOT] * 6)
    assert kinds[2] == "restart"
    assert kinds[5] == "suppressed"


def test_gives_up_after_max_restarts_in_window():
    # 6 minutes of constant breaches: restarts at t=60 and t=150, then it stops trying
    kinds, state = run(AUTO, [HOT] * 12, step=30)
    assert kinds.count("restart") == 2
    last = decide(AUTO, state, HOT, 12 * 30)
    assert last.code == "gave_up" and "needs a human" in last.reason


def test_restarts_allowed_again_after_window():
    _, state = run(AUTO, [HOT] * 12, step=30)
    # Later, the old restarts have aged out of the 10-minute sliding window
    kinds, _ = run(AUTO, [HOT] * 3, start=2000, state=state)
    assert kinds == ["restart", "warn", "warn"]
