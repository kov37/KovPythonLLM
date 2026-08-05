"""Typed tool and gate observations."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from KOV.contracts.common import Digest, EvidenceRef, StrictModel


class ObservationStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    TRUNCATED = "truncated"


class Observation(StrictModel):
    observation_id: EvidenceRef
    action_kind: str = Field(min_length=1, max_length=80)
    status: ObservationStatus
    summary: str = Field(min_length=1, max_length=12_000)
    artifact_id: EvidenceRef | None = None
    content_digest: Digest | None = None
    exit_code: int | None = Field(default=None, ge=-255, le=255)
    duration_ms: int = Field(default=0, ge=0)
    byte_count: int = Field(default=0, ge=0)
    line_count: int = Field(default=0, ge=0)
    hidden_line_count: int = Field(default=0, ge=0)
    redacted: bool = False
