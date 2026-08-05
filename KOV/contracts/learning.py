"""Opportunity and continual-learning contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from KOV.contracts.common import EvidenceRef, Identifier, StrictModel


class OpportunityOrigin(StrEnum):
    EVIDENCE = "evidence"
    EXPLORATORY = "exploratory"


class OpportunityStatus(StrEnum):
    QUEUED = "queued"
    ACTIVE = "active"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    COMPLETED = "completed"


class Opportunity(StrictModel):
    opportunity_id: Identifier
    origin: OpportunityOrigin
    status: OpportunityStatus = OpportunityStatus.QUEUED
    title: str = Field(min_length=3, max_length=160)
    hypothesis: str = Field(min_length=3, max_length=1_200)
    component: str = Field(min_length=1, max_length=160)
    severity: int = Field(ge=0, le=100)
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1, max_length=24)
    fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    created_at: datetime


class EpisodeOutcome(StrEnum):
    SUCCESS = "success"
    IMPLEMENTATION_FAILURE = "implementation_failure"
    INVALID_HYPOTHESIS = "invalid_hypothesis"
    INADEQUATE_TEST = "inadequate_test"
    ENVIRONMENT_FAILURE = "environment_failure"
    BUDGET_EXHAUSTED = "budget_exhausted"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class LearningEpisode(StrictModel):
    episode_id: Identifier
    run_id: Identifier
    outcome: EpisodeOutcome
    strategy: str = Field(min_length=1, max_length=200)
    component: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=2_000)
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1, max_length=32)
    failure_fingerprint: str | None = Field(default=None, min_length=64, max_length=64)
    created_at: datetime


class Lesson(StrictModel):
    lesson_id: Identifier
    version: int = Field(ge=1)
    situation: str = Field(min_length=1, max_length=1_000)
    guidance: str = Field(min_length=1, max_length=1_000)
    applicability: str = Field(min_length=1, max_length=600)
    confidence: float = Field(ge=0, le=1)
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1, max_length=32)
    supersedes: Identifier | None = None
    created_at: datetime
