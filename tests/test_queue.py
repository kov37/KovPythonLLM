"""Deterministic retry behavior for the durable opportunity queue."""

from datetime import UTC, datetime

from KOV.contracts.learning import Opportunity, OpportunityOrigin, OpportunityStatus
from KOV.discovery.queue import OpportunityQueue


def _opportunity() -> Opportunity:
    return Opportunity(
        opportunity_id="opportunity:test",
        origin=OpportunityOrigin.EVIDENCE,
        title="Retry a transient failure",
        hypothesis="A repaired controller can now complete the candidate.",
        component="reliability",
        severity=50,
        evidence_refs=("artifact:test",),
        fingerprint="a" * 64,
        created_at=datetime.now(UTC),
    )


def test_deferred_opportunity_is_retried_once_then_stays_deferred(tmp_path) -> None:
    queue = OpportunityQueue(tmp_path / "opportunities.sqlite3")
    queue.initialize()
    assert queue.add(_opportunity())

    first = queue.select_next()
    assert first is not None
    queue.finish(first.opportunity_id, OpportunityStatus.DEFERRED)
    assert queue.requeue_deferred(max_selections=2) == 1

    second = queue.select_next()
    assert second is not None
    queue.finish(second.opportunity_id, OpportunityStatus.DEFERRED)
    assert queue.requeue_deferred(max_selections=2) == 0
    assert queue.queued_count() == 0


def test_active_opportunity_is_deferred_after_restart(tmp_path) -> None:
    queue = OpportunityQueue(tmp_path / "opportunities.sqlite3")
    queue.initialize()
    assert queue.add(_opportunity())
    assert queue.select_next() is not None

    assert queue.recover_active() == 1
    assert queue.recover_active() == 0
    assert queue.queued_count() == 0
