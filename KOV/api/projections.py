"""Read-only dashboard projections derived exclusively from ledger events."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

from KOV.contracts.events import EventRecord, EventType
from KOV.storage.ledger import EventLedger


@dataclass(frozen=True, slots=True)
class DashboardProjection:
    ledger: EventLedger

    def overview(self) -> dict[str, object]:
        latest_by_run: dict[str, EventRecord] = {
            event.run_id: event for event in self.ledger.latest_event_per_run()
        }
        active = 0
        terminal_types = {
            "run.failed",
            "run.completed",
            "review.completed",
            "candidate.rejected",
            "candidate.approved",
            "candidate.published",
            "research.completed",
        }
        for event in latest_by_run.values():
            active += event.event_type.value not in terminal_types
        decisions = self.ledger.latest_events_by_type((EventType.DECISION,), limit=500)
        outcomes = self.ledger.latest_events_by_type(
            (
                EventType.CANDIDATE_REJECTED,
                EventType.CANDIDATE_APPROVED,
                EventType.PUBLISHED,
            ),
            limit=1,
        )
        latest_decision_event = decisions[0] if decisions else None
        latest_decision = (
            json.loads(latest_decision_event.payload_json) if latest_decision_event else None
        )
        latest_decision_active = bool(
            latest_decision_event
            and latest_by_run[latest_decision_event.run_id].event_type.value not in terminal_types
        )
        latest_outcome = (
            {
                "type": outcomes[0].event_type.value,
                "payload": json.loads(outcomes[0].payload_json),
            }
            if outcomes
            else None
        )
        test_passing_runs = self.ledger.distinct_run_count((EventType.COMPLETED,))
        approved_candidates = self.ledger.distinct_run_count(
            (EventType.CANDIDATE_APPROVED, EventType.PUBLISHED)
        )
        rejected_candidates = self.ledger.distinct_run_count(
            (EventType.CANDIDATE_REJECTED,)
        )
        return {
            "operationMode": "continuous",
            "workConserving": True,
            "activeRuns": active,
            "testPassingRuns": test_passing_runs,
            "approvedCandidates": approved_candidates,
            "rejectedCandidates": rejected_candidates,
            "totalEvents": self.ledger.event_count(),
            "latestDecision": latest_decision,
            "latestDecisionActive": latest_decision_active,
            "latestDecisionAt": (
                latest_decision_event.occurred_at.isoformat() if latest_decision_event else None
            ),
            "latestOutcome": latest_outcome,
            "metrics": self._metrics(decisions),
        }

    def timeline(self, limit: int = 100) -> list[dict[str, object]]:
        return [
            {
                "eventId": event.event_id,
                "runId": event.run_id,
                "sequence": event.sequence,
                "type": event.event_type.value,
                "actor": event.actor.value,
                "at": event.occurred_at.isoformat(),
                "payload": json.loads(event.payload_json),
                "privacyClass": event.privacy_class,
            }
            for event in self.ledger.latest_events(limit)
        ]

    @staticmethod
    def _metrics(decisions: Sequence[EventRecord]) -> dict[str, object]:
        parsed = [json.loads(event.payload_json) for event in decisions]
        durations = [
            int(item["model_duration_ms"]) for item in parsed if item.get("model_duration_ms")
        ]
        inputs = [int(item["input_tokens"]) for item in parsed if item.get("input_tokens")]
        outputs = [int(item["output_tokens"]) for item in parsed if item.get("output_tokens")]
        return {
            "modelCalls": len(parsed),
            "meanLatencyMs": round(sum(durations) / len(durations)) if durations else None,
            "inputTokens": sum(inputs) if inputs else None,
            "outputTokens": sum(outputs) if outputs else None,
            "latencyLabel": "measured" if durations else "unavailable",
            "tokenLabel": "measured" if inputs or outputs else "unavailable",
        }
