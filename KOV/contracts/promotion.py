"""Independent review, publication, deployment, and self-change contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from KOV.contracts.common import Digest, EvidenceRef, StrictModel


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"


class ReviewVerdict(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    decision: ReviewDecision
    summary: str = Field(min_length=3, max_length=1_200)
    correctness_findings: tuple[str, ...] = Field(default_factory=tuple, max_length=16)
    security_findings: tuple[str, ...] = Field(default_factory=tuple, max_length=16)
    test_findings: tuple[str, ...] = Field(default_factory=tuple, max_length=16)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple, max_length=24)


class EvidenceManifest(StrictModel):
    candidate_id: str = Field(min_length=3, max_length=96)
    base_commit: Digest | str = Field(min_length=40, max_length=64)
    candidate_commit: Digest | str = Field(min_length=40, max_length=64)
    changed_files: tuple[str, ...] = Field(min_length=1, max_length=100)
    check_artifacts: tuple[EvidenceRef, ...] = Field(min_length=1, max_length=32)
    observer_verdict: ReviewDecision
    diff_digest: Digest
    rollback_ready: bool


class SelfChangeDossier(StrictModel):
    candidate_id: str = Field(min_length=3, max_length=96)
    initiating_lessons: tuple[EvidenceRef, ...] = Field(min_length=1, max_length=32)
    rationale: str = Field(min_length=10, max_length=2_000)
    affected_capabilities: tuple[str, ...] = Field(min_length=1, max_length=32)
    threat_analysis: tuple[str, ...] = Field(min_length=1, max_length=32)
    predicted_benefits: tuple[str, ...] = Field(min_length=1, max_length=32)
    predicted_regressions: tuple[str, ...] = Field(min_length=1, max_length=32)
    activation_procedure: tuple[str, ...] = Field(min_length=1, max_length=32)
    rollback_manifest: tuple[str, ...] = Field(min_length=1, max_length=32)
