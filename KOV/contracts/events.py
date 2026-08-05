"""Append-only event contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from KOV.contracts.common import Digest, Identifier, StrictModel


class ActorRole(StrEnum):
    CONTROLLER = "controller"
    DISCOVERY = "discovery"
    PLANNER = "planner"
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    LEARNER = "learner"
    EVALUATOR = "evaluator"
    PUBLISHER = "publisher"
    DEPLOYER = "deployer"
    OPERATOR = "operator"


class EventType(StrEnum):
    RUN_CREATED = "run.created"
    DECISION = "decision.recorded"
    ACTION_REQUESTED = "action.requested"
    ACTION_AUTHORIZED = "action.authorized"
    ACTION_REJECTED = "action.rejected"
    OBSERVATION = "observation.recorded"
    REVIEW = "review.completed"
    EVIDENCE_GATE = "evidence_gate.completed"
    RESEARCH = "research.completed"
    CANDIDATE_REJECTED = "candidate.rejected"
    CANDIDATE_APPROVED = "candidate.approved"
    PUBLISHED = "candidate.published"
    STATE_TRANSITION = "state.transitioned"
    POLICY_VERIFIED = "policy.verified"
    POLICY_DEGRADED = "policy.degraded"
    PAUSED = "control.paused"
    STOPPED = "control.stopped"
    FAILURE = "run.failed"
    COMPLETED = "run.completed"


class EventRecord(StrictModel):
    schema_version: str = "1.0"
    event_id: Identifier
    run_id: Identifier
    candidate_id: Identifier | None = None
    sequence: int = Field(ge=1)
    event_type: EventType
    actor: ActorRole
    occurred_at: datetime
    causal_parent_id: Identifier | None = None
    idempotency_key: Identifier
    payload_json: str = Field(min_length=2, max_length=1_000_000)
    payload_digest: Digest
    privacy_class: str = Field(default="sanitized", pattern=r"^[a-z][a-z0-9_.-]+$")
