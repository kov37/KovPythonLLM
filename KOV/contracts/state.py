"""Lifecycle state and transition contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from KOV.contracts.common import Identifier, StrictModel


class LifecycleState(StrEnum):
    IDLE = "idle"
    COLLECTING = "collecting"
    TRIAGING = "triaging"
    RESEARCHING = "researching"
    HYPOTHESIZING = "hypothesizing"
    BASELINING = "baselining"
    IMPLEMENTING = "implementing"
    VALIDATING_SYNTAX = "validating_syntax"
    TESTING = "testing"
    REVIEWING = "reviewing"
    PUBLISHING = "publishing"
    WAITING_CI = "waiting_ci"
    DEPLOYING = "deploying"
    CANARY = "canary"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    FAILED = "failed"
    PAUSED = "paused"
    ROLLING_BACK = "rolling_back"
    DEGRADED = "degraded"
    STOPPED = "stopped"


class TransitionRecord(StrictModel):
    transition_id: Identifier
    run_id: Identifier
    from_state: LifecycleState
    to_state: LifecycleState
    reason: str = Field(min_length=1, max_length=500)
    policy_ids: tuple[Identifier, ...] = Field(default_factory=tuple, max_length=32)
    occurred_at: datetime
