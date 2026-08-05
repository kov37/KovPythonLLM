"""Fast deterministic Context-Preserving Relevance Selection (CPRS)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from KOV.observations.redaction import sanitize_text

_IMPORTANT = re.compile(
    r"(?i)(traceback|error|exception|failed|failure|fatal|assert|caused by|syntaxerror|"
    r"^\s*file \"|^\s*at\s+|^\s*def\s+|^\s*async\s+def\s+|^\s*class\s+|"
    r"^\s*(?:FAILED|ERROR|E\s+)|tests?\s+(?:passed|failed)|exit code|returncode|"
    r"^@@|^\+\+\+|^---|^[+-](?![+-]))"
)
_WARNING = re.compile(r"(?i)\b(?:warning|deprecated|deprecationwarning)\b")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{2,}")


@dataclass(frozen=True, slots=True)
class ReductionResult:
    text: str
    original_lines: int
    visible_lines: int
    hidden_lines: int
    estimated_tokens: int
    compressed: bool
    redacted: bool


class CPRSCompressor:
    """Bound model observations while retaining errors and objective evidence."""

    def __init__(self, token_threshold: int = 1_500, token_budget: int = 1_350) -> None:
        if not 128 <= token_budget <= token_threshold <= 32_000:
            raise ValueError("Invalid CPRS token bounds")
        self.token_threshold = token_threshold
        self.token_budget = token_budget

    @staticmethod
    def estimate_tokens(text: str) -> int:
        # Conservative and allocation-free enough for local control decisions.
        return max(1, (len(text.encode("utf-8")) + 2) // 3)

    def compress(self, text: str, *, objective: str = "") -> ReductionResult:
        sanitized, redacted = sanitize_text(text)
        lines = sanitized.splitlines()
        estimate = self.estimate_tokens(sanitized)
        if estimate <= self.token_threshold:
            return ReductionResult(
                text=sanitized,
                original_lines=len(lines),
                visible_lines=len(lines),
                hidden_lines=0,
                estimated_tokens=estimate,
                compressed=False,
                redacted=redacted,
            )

        objective_terms = {
            term.lower()
            for term in _WORD.findall(objective)
            if len(term) >= 4 and term.lower() not in {"this", "that", "with", "from"}
        }
        keep: set[int] = set()
        warning_seen: set[str] = set()
        for index, line in enumerate(lines):
            lowered = line.lower()
            important = bool(_IMPORTANT.search(line))
            relevant = any(term in lowered for term in objective_terms)
            boundary = index < 12 or index >= max(0, len(lines) - 12)
            if _WARNING.search(line):
                fingerprint = re.sub(r"\d+", "#", lowered).strip()
                if fingerprint in warning_seen and not important and not relevant:
                    continue
                warning_seen.add(fingerprint)
            if important or relevant or boundary:
                keep.add(index)
                if important:
                    keep.update(range(max(0, index - 2), min(len(lines), index + 3)))

        rendered = self._render(lines, keep)
        while self.estimate_tokens(rendered) > self.token_budget and len(keep) > 16:
            removable = [
                index
                for index in sorted(keep)
                if 12 <= index < len(lines) - 12 and not _IMPORTANT.search(lines[index])
            ]
            if not removable:
                break
            keep.difference_update(removable[::2])
            rendered = self._render(lines, keep)
        encoded = rendered.encode("utf-8")
        hard_limit = self.token_budget * 3
        if len(encoded) > hard_limit:
            rendered = encoded[:hard_limit].decode("utf-8", errors="ignore")
            rendered += "\n... [output clipped at CPRS hard limit] ..."
        visible = sum(1 for index in range(len(lines)) if index in keep)
        return ReductionResult(
            text=rendered,
            original_lines=len(lines),
            visible_lines=visible,
            hidden_lines=max(0, len(lines) - visible),
            estimated_tokens=self.estimate_tokens(rendered),
            compressed=True,
            redacted=redacted,
        )

    @staticmethod
    def _render(lines: list[str], keep: set[int]) -> str:
        output: list[str] = []
        previous = -1
        for index in sorted(keep):
            hidden = index - previous - 1
            if hidden:
                output.append(f"... [{hidden} lines hidden] ...")
            output.append(lines[index])
            previous = index
        trailing = len(lines) - previous - 1
        if trailing:
            output.append(f"... [{trailing} lines hidden] ...")
        return "\n".join(output)
