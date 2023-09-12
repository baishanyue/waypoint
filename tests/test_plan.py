import pytest

from waypoint import Plan, PlanError, Step, TemplatePlanner


class TestPlanValidation:
    def test_linear_plan_is_valid(self):
        plan = Plan("demo", [
            Step(id="a", action="decompose"),
            Step(id="b", action="review", inputs={"result": "$a.x"}, depends_on=["a"]),
        ])
        assert plan.validate() == []

    def test_unknown_dependency_is_reported(self):
        plan = Plan("demo", [Step(id="a", action="review", depends_on=["ghost"])])
        assert any("unknown step" in e for e in plan.validate())

    def test_cycle_is_reported(self):
        plan = Plan("demo", [
            Step(id="a", action="x", depends_on=["bb"]),
            Step(id="bb", action="y", depends_on=["a"]),
        ])
        assert any("cycle" in e for e in plan.validate())

    def test_duplicate_ids_are_rejected_at_construction(self):
        with pytest.raises(PlanError):
            Plan("demo", [Step(id="a", action="x"), Step(id="a", action="y")])

    def test_dangling_output_reference_is_reported(self):
        plan = Plan("demo", [Step(id="a", action="x", inputs={"v": "$ghost.field"})])
        assert any("unknown output" in e for e in plan.validate())

    def test_goal_pseudo_step_is_allowed(self):
        plan = Plan("demo", [Step(id="a", action="x", inputs={"v": "$goal.topic"})])
        assert plan.validate() == []


class TestOrdering:
    def test_order_is_deterministic(self):
        plan = Plan("demo", [
            Step(id="c", action="x", depends_on=["a", "aa"]),
            Step(id="a", action="x"),
            Step(id="aa", action="x"),
        ])
        assert plan.topological_order() == ["a", "aa", "c"]


class TestTemplatePlanner:
    def test_intent_detection(self):
        planner = TemplatePlanner()
        assert planner.detect("write a research report on RAG") == "research"
        assert planner.detect("fix the failing regression") == "fix"
        assert planner.detect("do something") == "default"

    def test_template_plan_is_valid_and_round_trips(self):
        plan = TemplatePlanner().plan("research vector databases")
        assert plan.validate() == []
        assert Plan.from_dict(plan.as_dict()).validate() == []
