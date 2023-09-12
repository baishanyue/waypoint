"""Built-in offline tool set."""
from __future__ import annotations

from .registry import ToolRegistry


def default_registry() -> ToolRegistry:
    """A small, fully offline tool set used by the examples and tests."""
    reg = ToolRegistry()

    reg.register(
        "wordcount", lambda text: len(text.split()),
        {"text": "str"}, "Count whitespace-delimited words.",
    )
    reg.register(
        "uppercase", lambda text: text.upper(),
        {"text": "str"}, "Uppercase a string.",
    )
    reg.register(
        "concat", lambda a, b, sep=" ": f"{a}{sep}{b}",
        {"a": "str", "b": "str"}, "Join two strings.",
    )
    reg.register(
        "gather_sources", _gather_sources, {"topic": "str"},
        "Return two placeholder sources for a topic.",
    )
    reg.register(
        "extract_facts", _extract_facts, {"source": "str"},
        "Extract fact-like sentences from a source.",
    )
    reg.register(
        "merge_facts", _merge_facts, {"left": "list", "right": "list"},
        "Merge two fact lists without duplicates.",
    )
    reg.register(
        "verify_facts", _verify_facts, {"facts": "list"},
        "Drop facts that are too short to be meaningful.",
    )
    reg.register(
        "compose_report", _compose_report, {"topic": "str", "facts": "list"},
        "Render a short markdown report.",
    )
    reg.register(
        "run_checks", lambda target: {"report": f"checks run for {target}", "ok": True},
        {"target": "str"}, "Run a placeholder check suite.",
    )
    reg.register(
        "diagnose", lambda report: {"summary": f"diagnosis from: {report}"},
        {"report": "str"}, "Summarize a failure report.",
    )
    reg.register(
        "apply_patch", lambda diagnosis: {"patched": True, "note": diagnosis},
        {"diagnosis": "str"}, "Apply a placeholder patch.",
    )
    reg.register(
        "decompose", lambda topic: {"tasks": [f"task-1:{topic}", f"task-2:{topic}"]},
        {"topic": "str"}, "Split a topic into two tasks.",
    )
    reg.register(
        "execute", lambda plan: {"output": list(plan)},
        {"plan": "list"}, "Execute a task list.",
    )
    reg.register(
        "review", lambda result: {"reviewed": True, "items": len(result)},
        {"result": "list"}, "Review a result list.",
    )
    return reg


# ------------------------------------------------------------------ helpers
def _gather_sources(topic: str) -> dict:
    return {
        "primary": (
            f"{topic} is usually decomposed into retrieval, reasoning and "
            "verification. Each stage fails in a characteristic way."
        ),
        "secondary": (
            f"Evaluations of {topic} report that retrieval quality dominates "
            "end-to-end accuracy more than generation quality."
        ),
    }


def _extract_facts(source: str) -> dict:
    sentences = [s.strip() for s in source.replace("!", ".").replace("?", ".")
                 .split(".") if s.strip()]
    return {"facts": [s for s in sentences if len(s.split()) >= 4]}


def _merge_facts(left: list, right: list) -> dict:
    seen: list = []
    for item in list(left) + list(right):
        if item not in seen:
            seen.append(item)
    return {"facts": seen}


def _verify_facts(facts: list) -> dict:
    kept = [f for f in facts if isinstance(f, str) and len(f) >= 12]
    return {"facts": kept, "dropped": len(facts) - len(kept)}


def _compose_report(topic: str, facts: list) -> dict:
    lines = [f"# {topic}", ""]
    for fact in facts:
        lines.append(f"- {fact}")
    return {"markdown": "\n".join(lines), "fact_count": len(facts)}
