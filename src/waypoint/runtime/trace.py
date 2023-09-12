"""Trace collection."""
from __future__ import annotations

import json
import time


class Tracer:
    """Collects structured execution events for inspection or export."""

    def __init__(self) -> None:
        self.events: list[dict] = []
        self._start = time.perf_counter()

    def emit(self, kind: str, step_id: str | None = None, **data) -> None:
        self.events.append({
            "seq": len(self.events),
            "kind": kind,
            "step_id": step_id,
            "t_ms": round((time.perf_counter() - self._start) * 1000.0, 3),
            **data,
        })

    def kinds(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in self.events:
            counts[event["kind"]] = counts.get(event["kind"], 0) + 1
        return dict(sorted(counts.items()))

    def to_json(self) -> str:
        return json.dumps(self.events, ensure_ascii=False, indent=1)
