"""`craft` command line: container management without memorising docker flags."""

import argparse
import os
import sys
from collections.abc import Sequence

from containercraft.monitor import Event, Monitor
from containercraft.policy import Policy
from containercraft.service import (
    ContainerNotFound,
    ContainerService,
    DockerUnavailable,
    NotRunning,
)
from containercraft.stats import human_bytes

COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ
STATE_COLORS = {"running": "32", "exited": "31", "dead": "31", "paused": "33", "restarting": "33"}
EVENT_ICONS = {
    "warn": "⚠️ ",
    "restart": "🔄",
    "restarted": "✅",
    "suppressed": "⛔",
    "error": "❌",
    "ok": "· ",
}


def paint(text: str, code: str | None) -> str:
    return f"\033[{code}m{text}\033[0m" if COLOR and code else text


def table(headers: list[str], rows: list[list[str]], colors: list[str | None] | None = None) -> str:
    widths = [
        max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)
    ]
    lines = [
        "  ".join(paint(h.ljust(w), "1") for h, w in zip(headers, widths, strict=True)).rstrip()
    ]
    for n, row in enumerate(rows):
        cells = [c.ljust(w) for c, w in zip(row, widths, strict=True)]
        # Colour only the state column (index 2), after padding so alignment holds
        if colors and colors[n]:
            cells[2] = paint(cells[2], colors[n])
        lines.append("  ".join(cells).rstrip())
    return "\n".join(lines)


def cmd_list(svc: ContainerService, args) -> int:
    infos = svc.list(all=args.all, label=args.label)
    if not infos:
        print("No containers" + ("" if args.all else " running (use -a to include stopped ones)"))
        return 0
    headers = ["NAME", "IMAGE", "STATE", "STATUS", "PORTS"]
    usage = {}
    if args.stats:
        headers += ["CPU", "MEM"]
        usage = svc.usage_many([i for i in infos if i.state == "running"])
    rows = []
    for i in infos:
        status = i.health and f"{i.status} ({i.health})" or i.status
        row = [i.name, i.image, i.state, status, ", ".join(i.ports) or "-"]
        if args.stats:
            u = usage.get(i.name)
            row += (
                [f"{u.cpu_percent:.1f}%", f"{u.mem_percent:.1f}%"]
                if u and not isinstance(u, Exception)
                else ["-", "-"]
            )
        rows.append(row)
    print(table(headers, rows, [STATE_COLORS.get(i.state) for i in infos]))
    return 0


def cmd_inspect(svc: ContainerService, args) -> int:
    i = svc.inspect(args.container)
    for key, value in [
        ("Name", i.name),
        ("ID", i.id),
        ("Image", i.image),
        ("State", i.state),
        ("Status", i.status),
        ("Health", i.health or "no healthcheck"),
        ("Ports", ", ".join(i.ports) or "-"),
        ("Restarts", str(i.restart_count)),
        ("Labels", ", ".join(f"{k}={v}" for k, v in i.labels.items()) or "-"),
    ]:
        print(f"{paint(key.ljust(9), '1')} {value}")
    return 0


def _lifecycle(action: str):
    def run(svc: ContainerService, args) -> int:
        failed = 0
        for ref in args.containers:
            try:
                info = getattr(svc, action)(ref)
                print(f"{info.name}: {paint(info.state, STATE_COLORS.get(info.state))}")
            except ContainerNotFound as e:
                print(paint(str(e), "31"), file=sys.stderr)
                failed += 1
        return 1 if failed else 0

    return run


def cmd_logs(svc: ContainerService, args) -> int:
    if args.follow:
        try:
            for chunk in svc.follow_logs(args.container, tail=args.tail):
                sys.stdout.write(chunk)
                sys.stdout.flush()
        except KeyboardInterrupt:
            pass
        return 0
    sys.stdout.write(svc.logs(args.container, tail=args.tail, timestamps=args.timestamps))
    return 0


def cmd_health(svc: ContainerService, args) -> int:
    i = svc.inspect(args.container)
    state = paint(i.state, STATE_COLORS.get(i.state))
    print(f"{paint(i.name, '1')}  {state}  restarts: {i.restart_count}")
    if i.health:
        print(f"healthcheck: {i.health}")
    if i.state != "running":
        return 1
    u = svc.usage(i.id)
    print(f"CPU     {u.cpu_percent:.1f}%")
    print(f"Memory  {u.mem_percent:.1f}%  ({human_bytes(u.mem_used)} / {human_bytes(u.mem_limit)})")
    return 0


def print_event(e: Event, verbose: bool) -> None:
    if e.kind == "ok" and not verbose:
        return
    color = {
        "warn": "33",
        "restart": "33",
        "restarted": "32",
        "suppressed": "31",
        "error": "31",
    }.get(e.kind)
    icon = EVENT_ICONS.get(e.kind, "")
    name = paint(e.container, "1")
    print(f"{e.time[11:19]}  {icon} {name}: {paint(e.message, color)}", flush=True)


def cmd_monitor(svc: ContainerService, args) -> int:
    policy = Policy(
        cpu_threshold=args.threshold,
        mem_threshold=args.mem_threshold,
        consecutive=args.consecutive,
        auto_restart=args.restart,
        cooldown=args.cooldown,
        max_restarts=args.max_restarts,
    )
    mon = Monitor(
        svc,
        policy,
        interval=args.interval,
        label=args.label,
        on_event=lambda e: print_event(e, args.verbose),
    )
    mode = "auto-restart ON" if args.restart else "warn only (add --restart to self-heal)"
    print(
        f"Monitoring every {args.interval:g}s · CPU > {args.threshold:g}% or "
        f"memory > {args.mem_threshold:g}% for {args.consecutive} checks · {mode}"
        + (f" · label {args.label}" if args.label else "")
    )
    if args.once:
        mon.tick()
        return 0
    mon.start()
    try:
        while mon.running:
            mon._thread.join(0.5)  # wake regularly so Ctrl+C is handled promptly
    except KeyboardInterrupt:
        print("\nStopping monitor…")
        mon.stop()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="craft", description="Manage Docker containers without memorising flags."
    )
    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    s = sub.add_parser("list", aliases=["ls"], help="list containers")
    s.add_argument("-a", "--all", action="store_true", help="include stopped containers")
    s.add_argument("--stats", action="store_true", help="add live CPU and memory columns")
    s.add_argument("--label", help="only containers with this label (key or key=value)")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("inspect", help="show details for one container")
    s.add_argument("container")
    s.set_defaults(func=cmd_inspect)

    for action in ("start", "stop", "restart"):
        s = sub.add_parser(action, help=f"{action} one or more containers")
        s.add_argument("containers", nargs="+", metavar="CONTAINER")
        s.set_defaults(func=_lifecycle(action))

    s = sub.add_parser("logs", help="print a container's logs")
    s.add_argument("container")
    s.add_argument("-n", "--tail", type=int, default=100, help="lines from the end (default 100)")
    s.add_argument("-f", "--follow", action="store_true", help="keep streaming new lines")
    s.add_argument("-t", "--timestamps", action="store_true")
    s.set_defaults(func=cmd_logs)

    s = sub.add_parser("health", help="CPU, memory and healthcheck for one container")
    s.add_argument("container")
    s.set_defaults(func=cmd_health)

    s = sub.add_parser("monitor", help="watch all running containers and optionally self-heal")
    s.add_argument(
        "--threshold", type=float, default=80, help="CPU %% (100 = one core). Default 80"
    )
    s.add_argument("--mem-threshold", type=float, default=90, help="memory %% of limit. Default 90")
    s.add_argument("--interval", type=float, default=30, help="seconds between checks. Default 30")
    s.add_argument(
        "--consecutive", type=int, default=3, help="checks over threshold before acting. Default 3"
    )
    s.add_argument(
        "--restart", action="store_true", help="restart containers that stay over threshold"
    )
    s.add_argument(
        "--cooldown", type=float, default=120, help="seconds between restarts of one container"
    )
    s.add_argument(
        "--max-restarts", type=int, default=3, help="give up after this many restarts in 10 min"
    )
    s.add_argument("--label", help="only watch containers with this label")
    s.add_argument("--once", action="store_true", help="run a single check and exit")
    s.add_argument("-v", "--verbose", action="store_true", help="also print healthy samples")
    s.set_defaults(func=cmd_monitor)
    return p


def main(argv: Sequence[str] | None = None, service: ContainerService | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        svc = service or ContainerService()
        return args.func(svc, args)
    except (DockerUnavailable, ContainerNotFound, NotRunning) as e:
        print(paint(str(e), "31"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
