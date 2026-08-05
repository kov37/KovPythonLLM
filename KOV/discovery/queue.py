"""Persistent ranked opportunity queue with rolling evidence/exploration allocation."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from KOV.contracts.learning import Opportunity, OpportunityOrigin, OpportunityStatus

_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS opportunities (
 opportunity_id TEXT PRIMARY KEY, origin TEXT NOT NULL, status TEXT NOT NULL,
 title TEXT NOT NULL, hypothesis TEXT NOT NULL, component TEXT NOT NULL,
 severity INTEGER NOT NULL, evidence_json TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS selections (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, opportunity_id TEXT NOT NULL,
 origin TEXT NOT NULL, selected_at TEXT NOT NULL
);
"""


class OpportunityQueue:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(_SCHEMA)

    def add(self, opportunity: Opportunity) -> bool:
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO opportunities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    opportunity.opportunity_id,
                    opportunity.origin.value,
                    opportunity.status.value,
                    opportunity.title,
                    opportunity.hypothesis,
                    opportunity.component,
                    opportunity.severity,
                    json.dumps(opportunity.evidence_refs),
                    opportunity.fingerprint,
                    opportunity.created_at.isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def queued_count(self) -> int:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM opportunities WHERE status = ?",
                (OpportunityStatus.QUEUED.value,),
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def requeue_deferred(self, *, max_selections: int = 2) -> int:
        """Retry transiently deferred work without permitting an infinite loop."""

        if max_selections < 1:
            raise ValueError("max_selections must be positive")
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                "UPDATE opportunities SET status = ? "
                "WHERE status = ? AND ("
                "SELECT COUNT(*) FROM selections "
                "WHERE selections.opportunity_id = opportunities.opportunity_id"
                ") < ?",
                (
                    OpportunityStatus.QUEUED.value,
                    OpportunityStatus.DEFERRED.value,
                    max_selections,
                ),
            )
        return cursor.rowcount

    def recover_active(self) -> int:
        """Mark work interrupted by a daemon restart as safely deferred."""

        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                "UPDATE opportunities SET status = ? WHERE status = ?",
                (OpportunityStatus.DEFERRED.value, OpportunityStatus.ACTIVE.value),
            )
        return cursor.rowcount

    def select_next(self) -> Opportunity | None:
        with sqlite3.connect(self.database_path) as connection:
            recent = connection.execute(
                "SELECT origin FROM selections ORDER BY sequence DESC LIMIT 4"
            ).fetchall()
            exploration_count = sum(row[0] == OpportunityOrigin.EXPLORATORY.value for row in recent)
            preferred = (
                OpportunityOrigin.EXPLORATORY
                if len(recent) == 4 and exploration_count == 0
                else OpportunityOrigin.EVIDENCE
            )
            row = self._ranked(connection, preferred)
            if row is None:
                alternate = (
                    OpportunityOrigin.EXPLORATORY
                    if preferred is OpportunityOrigin.EVIDENCE
                    else OpportunityOrigin.EVIDENCE
                )
                row = self._ranked(connection, alternate)
            if row is None:
                return None
            opportunity = self._from_row(row)
            connection.execute(
                "UPDATE opportunities SET status = ? WHERE opportunity_id = ?",
                (OpportunityStatus.ACTIVE.value, opportunity.opportunity_id),
            )
            connection.execute(
                "INSERT INTO selections(opportunity_id, origin, selected_at) VALUES (?, ?, ?)",
                (
                    opportunity.opportunity_id,
                    opportunity.origin.value,
                    opportunity.created_at.isoformat(),
                ),
            )
            connection.commit()
        return opportunity.model_copy(update={"status": OpportunityStatus.ACTIVE})

    def finish(self, opportunity_id: str, status: OpportunityStatus) -> None:
        if status not in {
            OpportunityStatus.COMPLETED,
            OpportunityStatus.DEFERRED,
            OpportunityStatus.REJECTED,
        }:
            raise ValueError("Opportunity can only finish in a durable terminal status")
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                "UPDATE opportunities SET status = ? WHERE opportunity_id = ? AND status = ?",
                (status.value, opportunity_id, OpportunityStatus.ACTIVE.value),
            )
        if cursor.rowcount != 1:
            raise KeyError(opportunity_id)

    @staticmethod
    def _ranked(connection: sqlite3.Connection, origin: OpportunityOrigin):
        return connection.execute(
            "SELECT * FROM opportunities WHERE status = ? AND origin = ? "
            "ORDER BY severity DESC, created_at ASC LIMIT 1",
            (OpportunityStatus.QUEUED.value, origin.value),
        ).fetchone()

    @staticmethod
    def _from_row(row: tuple[object, ...]) -> Opportunity:
        from datetime import datetime

        return Opportunity(
            opportunity_id=str(row[0]),
            origin=OpportunityOrigin(str(row[1])),
            status=OpportunityStatus(str(row[2])),
            title=str(row[3]),
            hypothesis=str(row[4]),
            component=str(row[5]),
            severity=int(str(row[6])),
            evidence_refs=tuple(json.loads(str(row[7]))),
            fingerprint=str(row[8]),
            created_at=datetime.fromisoformat(str(row[9])),
        )
