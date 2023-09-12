import pytest

from waypoint import (BudgetExceeded, BudgetPolicy, Executor, Plan, RetryPolicy,
                    Status, Step, ToolError, ToolRegistry, TemplatePlanner,
                    default_registry)


class TestExecution:
    def test_research_plan_runs_to_completion(self):
        plan = TemplatePlanner().plan("research vector databases")
        result = Executor(default_registry()).run(plan)
        assert result.status is Status.OK
        assert set(result.results) == set(plan.steps)
        assert result.results["write"].output["fact_count"] > 0
        assert result.trace[0]["kind"] == "run_start"

    def test_missing_tool_argument_is_a_failure_not_a_crash(self):
        tools = ToolRegistry()
        tools.register("needs_arg", lambda a: a, {"a": "str"})
        result = Executor(tools).run(Plan("demo", [Step(id="a", action="needs_arg")]))
        assert result.results["a"].status is Status.FAILED
        assert "missing argument" in result.results["a"].error


class TestFailureSemantics:
    def test_dependency_failure_skips_dependents(self):
        tools = ToolRegistry()
        tools.register(
            "boom", lambda topic: (_ for _ in ()).throw(ToolError("boom")),
            {"topic": "str"})
        tools.register("ok", lambda result: {"done": True}, {"result": "dict"})
        plan = Plan("demo", [
            Step(id="a", action="boom", inputs={"topic": "x"}),
            Step(id="b", action="ok", inputs={"result": "$a.value"}, depends_on=["a"]),
        ])
        result = Executor(tools).run(plan)
        assert result.results["a"].status is Status.FAILED
        assert result.results["b"].status is Status.SKIPPED


class TestRetriesAndBudget:
    def test_step_retries_until_success(self):
        state = {"calls": 0}

        def flaky(value):
            state["calls"] += 1
            if state["calls"] < 3:
                raise ToolError("not yet")
            return {"value": value}

        tools = ToolRegistry()
        tools.register("flaky", flaky, {"value": "str"})
        plan = Plan("demo", [Step(id="a", action="flaky", inputs={"value": "v"}, retries=3)])
        result = Executor(tools, retry=RetryPolicy(max_attempts=5)).run(plan)
        assert result.results["a"].status is Status.OK
        assert result.results["a"].attempts == 3

    def test_budget_exhaustion_raises(self):
        plan = TemplatePlanner().plan("research anything")
        executor = Executor(default_registry(), budget=BudgetPolicy(max_steps=2))
        with pytest.raises(BudgetExceeded):
            executor.run(plan)


class TestResume:
    def test_completed_steps_are_not_rerun(self):
        plan = TemplatePlanner().plan("research anything")
        tools = default_registry()
        first = Executor(tools).run(plan)
        second = Executor(tools).run(plan, resume={"collect": first.results["collect"]})
        assert "step_resumed" in [e["kind"] for e in second.trace]
        assert second.results["collect"].output == first.results["collect"].output
