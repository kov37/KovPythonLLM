"""Executable policy contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from KOV.contracts.common import Identifier, StrictModel
from KOV.contracts.state import LifecycleState


class PolicyClass(StrEnum):
    IMMUTABLE_ROOT = "immutable_root"
    PROTECTED_CONTROLLER = "protected_controller"
    SELF_UPDATABLE_ADAPTIVE = "self_updatable_adaptive"
    INFORMATIONAL = "informational"


class PolicyFailureMode(StrEnum):
    FAIL_CLOSED = "fail_closed"
    DEGRADE = "degrade"
    WARN = "warn"


class PolicyRecord(StrictModel):
    policy_id: Identifier
    schema_version: str = Field(pattern=r"^\d+\.\d+$")
    title: str = Field(min_length=1, max_length=160)
    requirement: str = Field(min_length=1, max_length=2_000)
    policy_class: PolicyClass
    owner_component: str = Field(min_length=1, max_length=120)
    enforcement: str = Field(min_length=1, max_length=500)
    applicable_states: tuple[LifecycleState, ...] = Field(default_factory=tuple)
    verification_tests: tuple[str, ...] = Field(default_factory=tuple, max_length=32)
    failure_mode: PolicyFailureMode
    enabled: bool = True


class PolicyVerdict(StrictModel):
    policy_id: Identifier
    allowed: bool
    reason: str = Field(min_length=1, max_length=500)
    verified_at: datetime
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=16)
