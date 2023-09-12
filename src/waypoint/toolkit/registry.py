"""Deterministic tool registry with light schema validation."""
from __future__ import annotations

from typing import Any, Callable

ToolFn = Callable[..., Any]

_TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}


class ToolError(RuntimeError):
    """Raised when a tool is missing, misused or returns badly."""


class ToolRegistry:
    def __init__(self) -> None:
        self._fns: dict[str, ToolFn] = {}
        self._schemas: dict[str, dict[str, str]] = {}
        self._docs: dict[str, str] = {}

    def register(self, name: str, fn: ToolFn, schema: dict[str, str] | None = None,
                 doc: str = "") -> None:
        if name in self._fns:
            raise ToolError(f"tool already registered: {name}")
        self._fns[name] = fn
        self._schemas[name] = schema or {}
        self._docs[name] = doc

    def names(self) -> list[str]:
        return sorted(self._fns)

    def describe(self) -> dict[str, dict]:
        return {n: {"schema": self._schemas[n], "doc": self._docs[n]}
                for n in self.names()}

    def call(self, name: str, **kwargs) -> Any:
        fn = self._fns.get(name)
        if fn is None:
            raise ToolError(f"unknown tool: {name}")
        schema = self._schemas[name]
        for arg, type_name in schema.items():
            if arg not in kwargs:
                raise ToolError(f"tool {name!r} missing argument {arg!r}")
            expected = _TYPE_MAP[type_name]
            if not isinstance(kwargs[arg], expected):
                raise ToolError(
                    f"tool {name!r} argument {arg!r} expected {type_name}"
                )
        unknown = set(kwargs) - set(schema)
        if unknown:
            raise ToolError(f"tool {name!r} got unexpected args: {sorted(unknown)}")
        return fn(**kwargs)
