"""Memory: working state plus an append-only episodic log."""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class WorkingMemory:
    """Key-value state shared across the steps of one run."""

    values: dict = field(default_factory=dict)

    def set(self, key: str, value) -> None:
        self.values[key] = value

    def get(self, key: str, default=None):
        return self.values.get(key, default)

    def snapshot(self) -> dict:
        return json.loads(json.dumps(self.values, ensure_ascii=False, default=str))


@dataclass
class EpisodicMemory:
    """Append-only record of what happened, in order."""

    entries: list[dict] = field(default_factory=list)

    def append(self, step_id: str | None, kind: str, detail: str = "") -> None:
        self.entries.append({"step_id": step_id, "kind": kind, "detail": detail})

    def for_step(self, step_id: str) -> list[dict]:
        return [e for e in self.entries if e["step_id"] == step_id]

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for entry in self.entries:
            counts[entry["kind"]] = counts.get(entry["kind"], 0) + 1
        return {
            "entries": len(self.entries),
            "by_kind": dict(sorted(counts.items())),
            "steps": sorted({e["step_id"] for e in self.entries if e["step_id"]}),
        }

    def to_json(self) -> str:
        return json.dumps(self.entries, ensure_ascii=False, indent=1)


class Memory:
    """Facade combining working and episodic memory for one run."""

    def __init__(self) -> None:
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()

    def record(self, step_id: str | None, kind: str, detail: str = "") -> None:
        self.episodic.append(step_id, kind, detail)
