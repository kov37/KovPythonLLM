"""Deterministic syntax gate for changed Python source."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from KOV.workspaces.registry import WorkspaceRegistry


@dataclass(frozen=True, slots=True)
class SyntaxFailure:
    path: str
    line: int
    column: int
    message: str


@dataclass(frozen=True, slots=True)
class SyntaxResult:
    passed: bool
    checked_files: tuple[str, ...]
    failures: tuple[SyntaxFailure, ...]

    def summary(self) -> str:
        if self.passed:
            return f"Syntax gate passed for {len(self.checked_files)} Python file(s)."
        return "\n".join(
            f"{failure.path}:{failure.line}:{failure.column}: SyntaxError: {failure.message}"
            for failure in self.failures
        )


class SyntaxVerifier:
    def __init__(self, registry: WorkspaceRegistry) -> None:
        self.registry = registry

    def verify(self, workspace: str, paths: tuple[str, ...]) -> SyntaxResult:
        python_paths = tuple(sorted(path for path in set(paths) if path.endswith(".py")))
        failures: list[SyntaxFailure] = []
        checked: list[str] = []
        for relative in python_paths:
            source = self.registry.resolve(workspace, relative)
            if not source.is_file():
                continue
            checked.append(relative)
            try:
                text = source.read_text(encoding="utf-8")
                ast.parse(text, filename=relative)
            except SyntaxError as exc:
                syntax = exc
                failures.append(
                    SyntaxFailure(
                        path=relative,
                        line=int(getattr(syntax, "lineno", 0) or 0),
                        column=int(getattr(syntax, "offset", 0) or 0),
                        message=str(getattr(syntax, "msg", syntax)),
                    )
                )
        return SyntaxResult(not failures, tuple(checked), tuple(failures))
