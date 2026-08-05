"""Deterministic proof requirements for candidate categories."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence

from pydantic import Field

from KOV.contracts.common import StrictModel
from KOV.contracts.events import EventRecord


class MeaningfulnessVerdict(StrictModel):
    """Machine-verifiable evidence outcome, independent of model confidence."""

    allowed: bool
    component: str = Field(min_length=1, max_length=160)
    requirements: tuple[str, ...] = Field(min_length=1, max_length=12)
    missing: tuple[str, ...] = Field(default_factory=tuple, max_length=12)


class MeaningfulnessGate:
    """Reject plausible-sounding changes that lack category-specific proof."""

    _CRITERIA = {
        "tests": ("Change only focused test files and prove the full Python suite passes.",),
        "service-runtime": (
            "Include a reproducing regression test and the smallest source fix.",
            "Prove the full Python suite passes.",
        ),
        "reliability": (
            "Include a reproducing regression test and the smallest source fix.",
            "Prove the full Python suite passes.",
        ),
        "usability": ("Include a focused UI test and a successful production frontend build.",),
        "performance": (
            "Include a reproducible benchmark with before and after measurements.",
            "Include regression coverage and prove the full Python suite passes.",
        ),
        "runtime": (
            "Include a behavioral evaluation proving the configuration change helps.",
            "Include regression coverage and prove the full Python suite passes.",
        ),
        "exploration": (
            "Convert the hypothesis into a focused regression test before publication.",
            "Prove the full Python suite passes.",
        ),
    }

    @classmethod
    def criteria_for(cls, component: str) -> tuple[str, ...]:
        return cls._CRITERIA.get(
            component,
            ("Provide a focused regression test and prove the full Python suite passes.",),
        )

    @classmethod
    def evaluate(
        cls,
        *,
        component: str,
        changed_files: Sequence[str],
        events: Sequence[EventRecord],
        diff: str = "",
    ) -> MeaningfulnessVerdict:
        requirements = cls.criteria_for(component)
        changed = tuple(changed_files)
        test_files = tuple(path for path in changed if cls._is_test(path))
        source_files = tuple(path for path in changed if not cls._is_test(path))
        frontend_files = tuple(path for path in changed if path.startswith("frontend/src/"))
        frontend_tests = tuple(
            path for path in changed if path.startswith("frontend/") and cls._is_frontend_test(path)
        )
        benchmark_files = tuple(
            path for path in changed if "benchmark" in path.lower() or "perf" in path.lower()
        )
        successful_commands = cls._successful_commands(events)
        python_passed = any("pytest" in command for command in successful_commands)
        frontend_built = any("npm run build" in command for command in successful_commands)
        benchmark_ran = any("benchmark" in command for command in successful_commands)
        missing: list[str] = []

        if not python_passed:
            missing.append("successful full Python test suite")
        if component == "tests":
            if not test_files:
                missing.append("focused test-file change")
            if source_files:
                missing.append("test-only scope")
            if diff:
                added_tests, removed_tests = cls._test_definition_delta(diff)
                if removed_tests:
                    missing.append("preserve existing regression tests")
                if added_tests <= removed_tests:
                    missing.append("net new regression test")
        elif component in {"service-runtime", "reliability"}:
            if not test_files:
                missing.append("reproducing regression test")
            if not source_files:
                missing.append("source fix")
        elif component == "usability":
            if not frontend_files:
                missing.append("frontend source change")
            if not frontend_tests:
                missing.append("focused frontend test")
            if not frontend_built:
                missing.append("successful production frontend build")
        elif component == "performance":
            if not source_files:
                missing.append("source optimization")
            if not test_files:
                missing.append("performance regression coverage")
            if not benchmark_files or not benchmark_ran:
                missing.append("reproducible before/after benchmark")
        elif component == "runtime":
            if not test_files:
                missing.append("behavioral configuration evaluation")
            if not benchmark_files or not benchmark_ran:
                missing.append("measured before/after evidence")
        else:
            if not test_files:
                missing.append("focused regression test")

        return MeaningfulnessVerdict(
            allowed=not missing,
            component=component,
            requirements=requirements,
            missing=tuple(missing),
        )

    @staticmethod
    def _is_test(path: str) -> bool:
        name = path.rsplit("/", 1)[-1]
        return path.startswith("tests/") or "/tests/" in path or name.startswith("test_")

    @staticmethod
    def _is_frontend_test(path: str) -> bool:
        lowered = path.lower()
        return any(marker in lowered for marker in (".test.", ".spec.", "/tests/"))

    @staticmethod
    def _test_definition_delta(diff: str) -> tuple[int, int]:
        """Count Python test definitions added and removed by a unified diff."""

        definition = re.compile(r"^(?:async\s+)?def\s+test_[A-Za-z0-9_]*\s*\(")
        added = 0
        removed = 0
        for line in diff.splitlines():
            if line.startswith("+++") or line.startswith("---") or len(line) < 2:
                continue
            body = line[1:].lstrip()
            if not definition.match(body):
                continue
            if line.startswith("+"):
                added += 1
            elif line.startswith("-"):
                removed += 1
        return added, removed

    @staticmethod
    def _successful_commands(events: Sequence[EventRecord]) -> tuple[str, ...]:
        commands: list[str] = []
        for event in events:
            if event.event_type.value != "observation.recorded":
                continue
            payload = json.loads(event.payload_json)
            if payload.get("action_kind") != "run_check" or payload.get("exit_code") != 0:
                continue
            summary = payload.get("summary")
            if isinstance(summary, str):
                commands.append(summary.splitlines()[0])
        return tuple(commands)
