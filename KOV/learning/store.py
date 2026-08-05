"""Typed episodes, lessons, FTS retrieval, and retry suppression."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from KOV.contracts.learning import LearningEpisode, Lesson

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=FULL;
CREATE TABLE IF NOT EXISTS episodes (
  episode_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, outcome TEXT NOT NULL,
  strategy TEXT NOT NULL, component TEXT NOT NULL, summary TEXT NOT NULL,
  evidence_json TEXT NOT NULL, failure_fingerprint TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_episode_failure ON episodes(failure_fingerprint, created_at);
CREATE TABLE IF NOT EXISTS lessons (
  lesson_id TEXT PRIMARY KEY, version INTEGER NOT NULL, situation TEXT NOT NULL,
  guidance TEXT NOT NULL, applicability TEXT NOT NULL, confidence REAL NOT NULL,
  evidence_json TEXT NOT NULL, supersedes TEXT, created_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS lesson_search USING fts5(
  lesson_id UNINDEXED, situation, guidance, applicability
);
"""


class LearningStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(_SCHEMA)

    def add_episode(self, episode: LearningEpisode) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "INSERT INTO episodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    episode.episode_id,
                    episode.run_id,
                    episode.outcome.value,
                    episode.strategy,
                    episode.component,
                    episode.summary,
                    json.dumps(episode.evidence_refs),
                    episode.failure_fingerprint,
                    episode.created_at.isoformat(),
                ),
            )

    def add_lesson(self, lesson: Lesson, valid_evidence: set[str]) -> bool:
        if not set(lesson.evidence_refs).issubset(valid_evidence):
            raise ValueError("Lesson cites unavailable evidence")
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "INSERT OR IGNORE INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    lesson.lesson_id,
                    lesson.version,
                    lesson.situation,
                    lesson.guidance,
                    lesson.applicability,
                    lesson.confidence,
                    json.dumps(lesson.evidence_refs),
                    lesson.supersedes,
                    lesson.created_at.isoformat(),
                ),
            )
            if cursor.rowcount == 1:
                connection.execute(
                    "INSERT INTO lesson_search VALUES (?, ?, ?, ?)",
                    (lesson.lesson_id, lesson.situation, lesson.guidance, lesson.applicability),
                )
            connection.commit()
        return cursor.rowcount == 1

    def retrieve(self, query: str, *, limit: int = 5) -> tuple[Lesson, ...]:
        terms = " OR ".join(f'"{token}"' for token in re.findall(r"[A-Za-z0-9_]{3,}", query))
        if not terms:
            return ()
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT l.* FROM lesson_search s JOIN lessons l USING(lesson_id) "
                "WHERE lesson_search MATCH ? "
                "ORDER BY bm25(lesson_search), l.confidence DESC LIMIT ?",
                (terms, limit),
            ).fetchall()
        return tuple(self._lesson(row) for row in rows)

    def seen_failure(self, fingerprint: str, *, since: datetime) -> bool:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT 1 FROM episodes WHERE failure_fingerprint = ? AND created_at >= ? LIMIT 1",
                (fingerprint, since.astimezone(UTC).isoformat()),
            ).fetchone()
        return row is not None

    def recent_lessons(self, *, limit: int = 3) -> tuple[Lesson, ...]:
        if not 1 <= limit <= 20:
            raise ValueError("lesson limit must be between 1 and 20")
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM lessons ORDER BY created_at DESC, confidence DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple(self._lesson(row) for row in rows)

    @staticmethod
    def _lesson(row: tuple[object, ...]) -> Lesson:
        return Lesson(
            lesson_id=str(row[0]),
            version=int(str(row[1])),
            situation=str(row[2]),
            guidance=str(row[3]),
            applicability=str(row[4]),
            confidence=float(str(row[5])),
            evidence_refs=tuple(json.loads(str(row[6]))),
            supersedes=str(row[7]) if row[7] else None,
            created_at=datetime.fromisoformat(str(row[8])),
        )
