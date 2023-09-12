"""Command line interface for Waypoint."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .plan.model import PlanError
from .runtime.executor import Executor
from .plan.planner import Plan, TemplatePlanner
from .runtime.policies import BudgetPolicy, RetryPolicy
from .toolkit.builtins import default_registry


def _load_plan(path: str) -> Plan:
    with open(path, encoding="utf-8") as fh:
        return Plan.from_dict(json.load(fh))


def cmd_plan(args: argparse.Namespace) -> int:
    plan = TemplatePlanner().plan(args.goal)
    print(json.dumps(plan.as_dict(), ensure_ascii=False, indent=1))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    plan = _load_plan(args.file)
    errors = plan.validate()
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=1))
        return 1
    print(json.dumps({
        "valid": True,
        "steps": len(plan.steps),
        "order": plan.topological_order(),
    }, ensure_ascii=False, indent=1))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if args.goal:
        plan = TemplatePlanner().plan(args.goal)
    else:
        plan = _load_plan(args.file)
    tools = default_registry()
    executor = Executor(
        tools,
        retry=RetryPolicy(max_attempts=args.max_attempts),
        budget=BudgetPolicy(max_steps=args.max_steps, max_failures=args.max_failures),
    )
    result = executor.run(plan)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=1))
    return 0 if result.status.value == "ok" else 1


def cmd_tools(_: argparse.Namespace) -> int:
    print(json.dumps(default_registry().describe(), ensure_ascii=False, indent=1))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="waypoint",
        description="Deterministic DAG execution for multi-step agent tasks.",
    )
    parser.add_argument(
        "--version", action="version", version=f"waypoint {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="print the plan for a goal")
    p_plan.add_argument("goal")
    p_plan.set_defaults(func=cmd_plan)

    p_validate = sub.add_parser("validate", help="validate a plan file")
    p_validate.add_argument("file")
    p_validate.set_defaults(func=cmd_validate)

    p_run = sub.add_parser("run", help="execute a plan")
    group = p_run.add_mutually_exclusive_group(required=True)
    group.add_argument("--goal", help="plan from a natural-language goal")
    group.add_argument("--file", help="path to a plan JSON")
    p_run.add_argument("--max-attempts", type=int, default=3)
    p_run.add_argument("--max-steps", type=int, default=100)
    p_run.add_argument("--max-failures", type=int, default=5)
    p_run.set_defaults(func=cmd_run)

    p_tools = sub.add_parser("tools", help="list registered tools")
    p_tools.set_defaults(func=cmd_tools)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (PlanError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
