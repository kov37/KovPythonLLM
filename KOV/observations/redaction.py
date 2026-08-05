"""Deterministic local redaction before any text reaches model context."""

from __future__ import annotations

import re

_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?i)\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{12,}\b"),
        "[REDACTED_TOKEN]",
    ),
    (
        re.compile(r"(?i)(?:api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+"),
        "credential=[REDACTED]",
    ),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])"), "[REDACTED_IP]"),
    (re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"), "Bearer [REDACTED]"),
    (
        re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY]",
    ),
)


def sanitize_text(text: str) -> tuple[str, bool]:
    """Remove terminal controls and redact common direct identifiers and credentials."""

    sanitized = _ANSI.sub("", text.replace("\x00", ""))
    redacted = sanitized != text
    for pattern, replacement in _RULES:
        sanitized, count = pattern.subn(replacement, sanitized)
        redacted = redacted or count > 0
    return sanitized, redacted
