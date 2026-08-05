"""Immutable outbound privacy and credential scan."""

from __future__ import annotations

import re

from KOV.observations.redaction import sanitize_text

_FORBIDDEN = (
    re.compile(r"(?i)-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:password|api[_-]?key|secret|token)\s*[:=]"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?i)traceback \(most recent call last\)"),
    re.compile(r"(?i)raw (?:conversation|trace)"),
)


class OutboundGate:
    def verify(self, *documents: str) -> None:
        for document in documents:
            sanitized, redacted = sanitize_text(document)
            if redacted or sanitized != document:
                raise PermissionError("Outbound text contains data requiring redaction")
            if any(pattern.search(document) for pattern in _FORBIDDEN):
                raise PermissionError("Outbound privacy gate rejected protected content")
