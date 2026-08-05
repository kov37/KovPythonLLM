"""Deterministic, privacy-safe lessons distilled from controller events."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from KOV.contracts.events import EventRecord
from KOV.contracts.learning import Lesson
from KOV.learning.store import LearningStore
from KOV.storage.ledger import EventLedger


@dataclass(frozen=True, slots=True)
class FailurePattern:
    needles: tuple[str, ...]
    minimum_matches: int
    situation: str
    guidance: str
    applicability: str
    confidence: float = 0.97
    match_all: bool = False


_PATTERNS = (
    FailurePattern(
        needles=("removes a test case", "existing regression test"),
        minimum_matches=1,
        situation="A test-focused candidate modifies existing regression coverage.",
        guidance=(
            "Preserve every existing test. Add one distinct behavior-focused test and verify "
            "the diff has a positive net test-definition count before submission."
        ),
        applicability="Test-only repository candidates.",
    ),
    FailurePattern(
        needles=("filenotfounderror",),
        minimum_matches=2,
        situation="A repository trajectory repeatedly uses an unobserved file path.",
        guidance=(
            "After FileNotFoundError, stop retrying the shortened path. Use repo_snapshot or "
            "search_code and copy the exact observed repository-relative path."
        ),
        applicability="All repository file actions.",
    ),
    FailurePattern(
        needles=("line_end exceeds file length",),
        minimum_matches=2,
        situation="A line edit repeatedly exceeds the current file boundary.",
        guidance=(
            "Refresh the exact file window and use its reported total line count and digest "
            "before another edit. Never reuse stale line coordinates."
        ),
        applicability="Digest-checked line edits.",
    ),
    FailurePattern(
        needles=("replacement_text", "string_too_short"),
        minimum_matches=2,
        situation="A trajectory needs to delete an inspected line range.",
        guidance=(
            "Use edit_lines with an empty replacement_text for exact range deletion; do not "
            "replace neighboring behavior or invent placeholder code."
        ),
        applicability="Exact line-range deletion.",
        match_all=True,
    ),
    FailurePattern(
        needles=("replacement cannot exceed 100 lines", "cannot replace more than 100 lines"),
        minimum_matches=1,
        situation="A proposed atomic edit is larger than the inspected context window.",
        guidance=(
            "Split the change into independently inspectable edits of at most 100 lines and "
            "view the authoritative post-edit neighborhood after each mutation."
        ),
        applicability="All line-oriented repository mutations.",
    ),
)


def distill_failure_lesson(events: tuple[EventRecord, ...]) -> Lesson | None:
    """Return one highest-priority fixed lesson supported by event metadata."""

    searchable: list[tuple[EventRecord, str]] = []
    for event in events:
        try:
            payload = json.loads(event.payload_json)
        except json.JSONDecodeError:
            continue
        fragments = [payload.get(key) for key in ("summary", "reason")]
        text = " ".join(value for value in fragments if isinstance(value, str)).casefold()
        if text:
            searchable.append((event, text))
    for pattern in _PATTERNS:
        matches = [
            event
            for event, text in searchable
            if (
                all(needle in text for needle in pattern.needles)
                if pattern.match_all
                else any(needle in text for needle in pattern.needles)
            )
        ]
        if len(matches) < pattern.minimum_matches:
            continue
        digest = hashlib.sha256(
            f"{pattern.situation}\n{pattern.guidance}".encode()
        ).hexdigest()
        return Lesson(
            lesson_id=f"lesson:{digest[:32]}",
            version=1,
            situation=pattern.situation,
            guidance=pattern.guidance,
            applicability=pattern.applicability,
            confidence=pattern.confidence,
            evidence_refs=tuple(event.event_id for event in matches[:32]),
            created_at=datetime.now(UTC),
        )
    return None


def distill_recent_failures(
    ledger: EventLedger, learning: LearningStore, *, event_limit: int = 10_000
) -> int:
    """Idempotently backfill lessons from bounded append-only history."""

    grouped: dict[str, list[EventRecord]] = {}
    for event in reversed(ledger.latest_events(event_limit)):
        grouped.setdefault(event.run_id, []).append(event)
    added = 0
    for events in grouped.values():
        lesson = distill_failure_lesson(tuple(events))
        if lesson is None:
            continue
        if learning.add_lesson(lesson, {event.event_id for event in events}):
            added += 1
    return added
