"""Plans, validation and a small template planner.

The planner is deliberately rule-based. A language model can be plugged in by
implementing ``Planner.plan``, but the offline default gives every run a
reproducible, inspectable shape.
"""
from __future__ import annotations

import heapq
import re

from .model import PlanError, Step

_REF = re.compile(r"^\$([a-zA-Z0-9_\-]+)(?:\.([a-zA-Z0-9_.]+))?$")


class Plan:
    def __init__(self, goal: str, steps: list[Step]):
        self.goal = goal
        self.steps: dict[str, Step] = {}
        for step in steps:
            if step.id in self.steps:
                raise PlanError(f"duplicate step id: {step.id}")
            self.steps[step.id] = step

    # ------------------------------------------------------------ validation
    def validate(self) -> list[str]:
        errors: list[str] = []
        for step in self.steps.values():
            for dep in step.depends_on:
                if dep not in self.steps:
                    errors.append(f"step {step.id!r} depends on unknown step {dep!r}")
                if dep == step.id:
                    errors.append(f"step {step.id!r} depends on itself")
            for value in step.inputs.values():
                if isinstance(value, str):
                    match = _REF.match(value)
                    if match and match.group(1) not in self.steps \
                            and match.group(1) != "goal":
                        errors.append(
                            f"step {step.id!r} references unknown output {value!r}"
                        )
        if not errors:
            try:
                self.topological_order()
            except PlanError as exc:
                errors.append(str(exc))
        return errors

    def topological_order(self) -> list[str]:
        """Deterministic Kahn order; ties broken by insertion order."""
        indegree = {sid: 0 for sid in self.steps}
        children: dict[str, list[str]] = {sid: [] for sid in self.steps}
        for sid, step in self.steps.items():
            for dep in step.depends_on:
                if dep not in self.steps:
                    raise PlanError(f"unknown dependency {dep!r} in step {sid!r}")
                indegree[sid] += 1
                children[dep].append(sid)
        heap = [sid for sid, deg in indegree.items() if deg == 0]
        heapq.heapify(heap)
        order: list[str] = []
        while heap:
            sid = heapq.heappop(heap)
            order.append(sid)
            for child in children[sid]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    heapq.heappush(heap, child)
        if len(order) != len(self.steps):
            raise PlanError("plan contains a cycle")
        return order

    def as_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": [self.steps[sid].as_dict() for sid in self.topological_order()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Plan":
        return cls(data.get("goal", ""), [Step.from_dict(s) for s in data["steps"]])


def _tool(tid: str, action: str, inputs: dict | None = None,
          deps: list[str] | None = None, retries: int = 0) -> Step:
    return Step(id=tid, action=action, inputs=inputs or {},
                depends_on=deps or [], retries=retries)


# Intent -> ordered step templates. Each list is a linear chain plus branches.
TEMPLATES: dict[str, list[Step]] = {
    "research": [
        _tool("collect", "gather_sources", {"topic": "$goal.topic"}),
        _tool("extract_a", "extract_facts", {"source": "$collect.primary"},
              ["collect"]),
        _tool("extract_b", "extract_facts", {"source": "$collect.secondary"},
              ["collect"]),
        _tool("merge", "merge_facts",
              {"left": "$extract_a.facts", "right": "$extract_b.facts"},
              ["extract_a", "extract_b"]),
        _tool("verify", "verify_facts", {"facts": "$merge.facts"}, ["merge"],
              retries=1),
        _tool("write", "compose_report",
              {"topic": "$goal.topic", "facts": "$verify.facts"}, ["verify"]),
    ],
    "fix": [
        _tool("reproduce", "run_checks", {"target": "$goal.topic"}),
        _tool("diagnose", "diagnose", {"report": "$reproduce.report"}, ["reproduce"]),
        _tool("patch", "apply_patch", {"diagnosis": "$diagnose.summary"},
              ["diagnose"], retries=1),
        _tool("verify", "run_checks", {"target": "$goal.topic"}, ["patch"]),
    ],
    "default": [
        _tool("decompose", "decompose", {"topic": "$goal.topic"}),
        _tool("execute", "execute", {"plan": "$decompose.tasks"}, ["decompose"]),
        _tool("review", "review", {"result": "$execute.output"}, ["execute"]),
    ],
}


class TemplatePlanner:
    """Pick a plan template from the goal text."""

    KEYWORDS = {
        "research": ("research", "report", "survey", "调研", "报告", "综述"),
        "fix": ("fix", "bug", "failing", "regression", "修复", "缺陷"),
    }

    def detect(self, goal: str) -> str:
        lowered = goal.lower()
        for intent, words in self.KEYWORDS.items():
            if any(w in lowered for w in words):
                return intent
        return "default"

    def plan(self, goal: str) -> Plan:
        intent = self.detect(goal)
        steps = [Step.from_dict(s.as_dict()) for s in TEMPLATES[intent]]
        plan = Plan(goal=goal, steps=steps)
        errors = plan.validate()
        if errors:
            raise PlanError("; ".join(errors))
        return plan
