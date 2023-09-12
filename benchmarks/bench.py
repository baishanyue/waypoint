#!/usr/bin/env python3
"""Reproducible micro-benchmark for Waypoint.

Measures plan validation throughput and full run throughput on the bundled
research plan. Numbers are indicative of this machine only.
"""
from __future__ import annotations

import os
import platform
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from waypoint import Executor, Plan, default_registry  # noqa: E402

PLAN_PATH = os.path.join(os.path.dirname(__file__), "..", "examples", "plan.json")


def load_plan() -> Plan:
    import json
    with open(PLAN_PATH, encoding="utf-8") as fh:
        return Plan.from_dict(json.load(fh))


def main() -> int:
    plan = load_plan()
    tools = default_registry()

    validations = 2000
    t0 = time.perf_counter()
    for _ in range(validations):
        plan.validate()
        plan.topological_order()
    validate_s = time.perf_counter() - t0

    runs = 300
    t0 = time.perf_counter()
    for _ in range(runs):
        result = Executor(tools).run(plan)
        assert result.status.value == "ok"
    run_s = time.perf_counter() - t0

    latencies = []
    for _ in range(30):
        t0 = time.perf_counter()
        Executor(tools).run(plan)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    print("## Benchmarks\n")
    print(f"Environment: Python {platform.python_version()} · "
          f"{platform.machine()} · {platform.system()}\n")
    print("| Metric | Value |")
    print("| --- | ---: |")
    print(f"| Steps per plan | {len(plan.steps)} |")
    print(f"| Validation throughput | {validations / validate_s:,.0f} plans/s |")
    print(f"| Run throughput | {runs / run_s:,.0f} plans/s |")
    print(f"| Run p50 | {statistics.median(latencies):.2f} ms |")
    print(f"| Run p95 | {sorted(latencies)[int(len(latencies) * 0.95) - 1]:.2f} ms |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
