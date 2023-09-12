from waypoint import (EpisodicMemory, Memory, Observer, Tracer, ToolError,
                     ToolRegistry, default_registry)


class TestToolRegistry:
    def test_type_checking(self):
        reg = default_registry()
        assert reg.call("wordcount", text="one two three") == 3
        try:
            reg.call("wordcount", text=42)
        except ToolError as exc:
            assert "expected str" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("expected ToolError")

    def test_unknown_tool(self):
        try:
            ToolRegistry().call("nope")
        except ToolError as exc:
            assert "unknown tool" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("expected ToolError")


class TestMemory:
    def test_episodic_summary(self):
        mem = EpisodicMemory()
        mem.append("a", "step_ok")
        mem.append("a", "step_ok")
        mem.append("b", "step_failed")
        summary = mem.summary()
        assert summary["entries"] == 3
        assert summary["steps"] == ["a", "b"]

    def test_facade_records_detail(self):
        mem = Memory()
        mem.record("a", "note", "hello")
        assert mem.episodic.entries[0]["detail"] == "hello"


class TestTracer:
    def test_event_counts(self):
        tracer = Tracer()
        tracer.emit("step_ok", "a")
        tracer.emit("step_ok", "b")
        tracer.emit("run_end")
        assert tracer.kinds() == {"run_end": 1, "step_ok": 2}
        assert len(tracer.events) == 3

    def test_tracer_satisfies_observer_protocol(self):
        assert isinstance(Tracer(), Observer)
