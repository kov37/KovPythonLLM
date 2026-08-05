"""Machine-readable policy loading and action authorization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from KOV.contracts.actions import AgentAction
from KOV.contracts.policies import PolicyClass, PolicyRecord, PolicyVerdict
from KOV.contracts.state import LifecycleState


class PolicyConfigurationError(ValueError):
    """Raised when protected policy definitions are incomplete or conflicting."""


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    verdicts: tuple[PolicyVerdict, ...]

    @property
    def reason(self) -> str:
        return "; ".join(verdict.reason for verdict in self.verdicts)


_READ_ACTIONS = frozenset({"repo_snapshot", "view_file", "search_code", "view_artifact"})
_MUTATION_ACTIONS = frozenset({"edit_lines", "create_file", "move_path", "delete_path"})
_READ_STATES = frozenset(
    {
        LifecycleState.TRIAGING,
        LifecycleState.RESEARCHING,
        LifecycleState.HYPOTHESIZING,
        LifecycleState.BASELINING,
        LifecycleState.IMPLEMENTING,
        LifecycleState.VALIDATING_SYNTAX,
        LifecycleState.TESTING,
        LifecycleState.REVIEWING,
    }
)


class PolicyRegistry:
    """Validated immutable view of executable policy records."""

    def __init__(self, policies: tuple[PolicyRecord, ...]) -> None:
        by_id = {policy.policy_id: policy for policy in policies}
        if len(by_id) != len(policies):
            raise PolicyConfigurationError("Duplicate policy IDs")
        for policy in policies:
            if (
                policy.enabled
                and policy.policy_class is not PolicyClass.INFORMATIONAL
                and not policy.verification_tests
            ):
                raise PolicyConfigurationError(
                    f"Required policy has no verification test: {policy.policy_id}"
                )
        self._policies = by_id

    @classmethod
    def load(cls, directory: Path) -> PolicyRegistry:
        policies: list[PolicyRecord] = []
        for path in sorted(directory.glob("*.json")):
            try:
                payload = path.read_text(encoding="utf-8")
                json.loads(payload)
                policies.append(PolicyRecord.model_validate_json(payload, strict=True))
            except (OSError, json.JSONDecodeError, ValidationError) as exc:
                raise PolicyConfigurationError(f"Invalid policy file {path}: {exc}") from exc
        if not policies:
            raise PolicyConfigurationError(f"No policy records found in {directory}")
        return cls(tuple(policies))

    @property
    def policies(self) -> tuple[PolicyRecord, ...]:
        return tuple(self._policies[key] for key in sorted(self._policies))

    def get(self, policy_id: str) -> PolicyRecord:
        try:
            return self._policies[policy_id]
        except KeyError as exc:
            raise PolicyConfigurationError(f"Unknown policy: {policy_id}") from exc

    def authorize_action(
        self,
        action: AgentAction,
        state: LifecycleState,
        *,
        degraded: bool = False,
        stopped: bool = False,
    ) -> AuthorizationDecision:
        now = datetime.now(UTC)
        verdicts: list[PolicyVerdict] = []

        def add(policy_id: str, allowed: bool, reason: str) -> None:
            self.get(policy_id)
            verdicts.append(
                PolicyVerdict(
                    policy_id=policy_id,
                    allowed=allowed,
                    reason=reason,
                    verified_at=now,
                )
            )

        if stopped:
            add("policy.control.stop", False, "Emergency Stop blocks every model action")
            return AuthorizationDecision(False, tuple(verdicts))
        if degraded and action.kind not in _READ_ACTIONS:
            add("policy.control.degraded", False, "Degraded mode permits read-only actions only")
            return AuthorizationDecision(False, tuple(verdicts))

        if action.kind in _READ_ACTIONS:
            allowed = state in _READ_STATES
            add("policy.tools.read_state", allowed, f"Read action in state {state.value}")
        elif action.kind in _MUTATION_ACTIONS:
            allowed = state is LifecycleState.IMPLEMENTING
            add("policy.tools.mutation_state", allowed, f"Mutation action in state {state.value}")
        elif action.kind == "run_check":
            allowed = state in {
                LifecycleState.BASELINING,
                LifecycleState.VALIDATING_SYNTAX,
                LifecycleState.TESTING,
                LifecycleState.REVIEWING,
            }
            add("policy.tools.check_state", allowed, f"Check action in state {state.value}")
        elif action.kind == "submit_candidate":
            allowed = state is LifecycleState.IMPLEMENTING
            add("policy.candidate.submit_state", allowed, f"Submission in state {state.value}")
        else:
            add("policy.actions.known", False, f"Unknown action kind: {action.kind}")

        return AuthorizationDecision(all(verdict.allowed for verdict in verdicts), tuple(verdicts))
