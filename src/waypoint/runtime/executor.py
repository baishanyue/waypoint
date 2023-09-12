"""DAG executor: dependency-ordered execution with retries and budgets."""
from __future__ import annotations

import re
import time

from ..plan.model import (BudgetExceeded, PlanError, RunResult, Status, StepResult)
from ..plan.planner import Plan
from .policies import BudgetPolicy, RetryPolicy
from ..toolkit.registry import ToolError, ToolRegistry

_REF = re.compile(r"^\$([a-zA-Z0-9_\-]+)(?:\.([a-zA-Z0-9_.]+))?$")
_GOAL = "__goal__"


class Executor:
    def __init__(self, tools: ToolRegistry, retry: RetryPolicy | None = None,
                 budget: BudgetPolicy | None = None, tracer=None):
        self.tools = tools
        self.retry = retry or RetryPolicy()
        self.budget = budget or BudgetPolicy()
        self.tracer = tracer

    # ------------------------------------------------------------- resolution
    def _resolve(self, value, goal: str, outputs: dict):
        if isinstance(value, str):
            match = _REF.match(value)
            if match:
                sid, path = match.group(1), match.group(2)
                if sid in (_GOAL, "goal"):
                    base: object = {"topic": goal, "text": goal}
                else:
                    if sid not in outputs:
                        raise PlanError(f"output of {sid!r} is not available")
                    base = outputs[sid]
                return self._dig(base, path)
            return value
        if isinstance(value, dict):
            return {k: self._resolve(v, goal, outputs) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve(v, goal, outputs) for v in value]
        return value

    @staticmethod
    def _dig(base, path: str | None):
        if not path:
            return base
        current = base
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise PlanError(f"cannot resolve field {part!r} in {base!r}")
        return current

    # ------------------------------------------------------------------- run
    def run(self, plan: Plan, goal: str | None = None,
            resume: dict[str, StepResult] | None = None) -> RunResult:
        goal_text = goal if goal is not None else plan.goal
        order = plan.topological_order()
        results: dict[str, StepResult] = dict(resume or {})
        outputs: dict[str, object] = {}
        trace: list[dict] = []
        started = time.perf_counter()

        def emit(kind: str, step_id: str | None = None, **data) -> None:
            event = {
                "seq": len(trace),
                "kind": kind,
                "step_id": step_id,
                "t_ms": round((time.perf_counter() - started) * 1000.0, 3),
                **data,
            }
            trace.append(event)
            if self.tracer is not None:
                self.tracer.emit(kind, step_id, **data)

        emit("run_start", goal=goal_text)
        executed = 0
        failures = 0

        for sid in order:
            step = plan.steps[sid]

            # Already finished in a previous attempt: reuse, do not re-run.
            if sid in results and results[sid].status is Status.OK:
                outputs[sid] = results[sid].output
                emit("step_resumed", sid)
                continue

            blocked = [
                dep for dep in step.depends_on
                if dep not in results or results[dep].status is not Status.OK
            ]
            if blocked:
                results[sid] = StepResult(
                    sid, Status.SKIPPED,
                    error=f"dependency failed: {', '.join(sorted(blocked))}",
                )
                emit("step_skipped", sid, blocked=blocked)
                continue

            try:
                inputs = self._resolve(step.inputs, goal_text, outputs)
            except PlanError as exc:
                failures += 1
                results[sid] = StepResult(sid, Status.FAILED, error=str(exc))
                emit("step_failed", sid, error=str(exc))
                continue

            executed += 1
            self.budget.check(executed, failures)

            attempt = 0
            step_start = time.perf_counter()
            while True:
                attempt += 1
                try:
                    output = self.tools.call(step.action, **inputs)
                    results[sid] = StepResult(
                        sid, Status.OK, output=output, attempts=attempt,
                        elapsed_ms=(time.perf_counter() - step_start) * 1000.0,
                    )
                    outputs[sid] = output
                    emit("step_ok", sid, attempts=attempt)
                    break
                except ToolError as exc:
                    allowed = attempt <= step.retries and self.retry.should_retry(attempt)
                    if allowed:
                        emit("step_retry", sid, attempt=attempt, error=str(exc))
                        if self.retry.backoff_seconds:
                            time.sleep(self.retry.backoff_seconds)
                        continue
                    failures += 1
                    results[sid] = StepResult(
                        sid, Status.FAILED, error=str(exc), attempts=attempt,
                        elapsed_ms=(time.perf_counter() - step_start) * 1000.0,
                    )
                    emit("step_failed", sid, attempts=attempt, error=str(exc))
                    break

        run = RunResult(goal=goal_text, order=order, results=results, trace=trace)
        emit("run_end", status=run.status.value)
        return run


def run_plan(plan: Plan, tools: ToolRegistry, goal: str | None = None,
             retry: RetryPolicy | None = None) -> RunResult:
    return Executor(tools, retry=retry).run(plan, goal=goal)
