"""Waypoint — deterministic DAG execution for multi-step agent tasks.

Interface-first: plans, tools and observers are all small protocols, so the
executor never depends on a concrete implementation of any of them.
"""
from .plan.model import (BudgetExceeded, PlanError, RunResult, Status, Step,
                         StepResult)
from .plan.planner import Plan, TemplatePlanner
from .protocols import Observer, Planner, Tool
from .runtime.executor import Executor, run_plan
from .runtime.policies import BudgetPolicy, Checkpoint, RetryPolicy
from .runtime.trace import Tracer
from .toolkit.builtins import default_registry
from .toolkit.registry import ToolError, ToolRegistry
from .memory import EpisodicMemory, Memory, WorkingMemory

__version__ = "0.1.0"

__all__ = [
    "BudgetExceeded", "BudgetPolicy", "Checkpoint", "EpisodicMemory",
    "Executor", "Memory", "Observer", "Plan", "PlanError", "Planner",
    "RetryPolicy", "RunResult", "Status", "Step", "StepResult",
    "TemplatePlanner", "Tool", "ToolError", "ToolRegistry", "Tracer",
    "WorkingMemory", "default_registry", "run_plan", "__version__",
]
