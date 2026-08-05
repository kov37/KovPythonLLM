"""Explicit deterministic lifecycle state machine."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import RLock

from KOV.contracts.common import new_id
from KOV.contracts.state import LifecycleState, TransitionRecord


class TransitionError(ValueError):
    """Raised when a requested lifecycle transition is illegal."""


_FORWARD: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.IDLE: frozenset({LifecycleState.COLLECTING}),
    LifecycleState.COLLECTING: frozenset({LifecycleState.TRIAGING, LifecycleState.IDLE}),
    LifecycleState.TRIAGING: frozenset(
        {LifecycleState.RESEARCHING, LifecycleState.HYPOTHESIZING, LifecycleState.DEFERRED}
    ),
    LifecycleState.RESEARCHING: frozenset(
        {LifecycleState.HYPOTHESIZING, LifecycleState.DEFERRED, LifecycleState.REJECTED}
    ),
    LifecycleState.HYPOTHESIZING: frozenset(
        {LifecycleState.BASELINING, LifecycleState.DEFERRED, LifecycleState.REJECTED}
    ),
    LifecycleState.BASELINING: frozenset(
        {LifecycleState.IMPLEMENTING, LifecycleState.DEFERRED, LifecycleState.REJECTED}
    ),
    LifecycleState.IMPLEMENTING: frozenset(
        {LifecycleState.VALIDATING_SYNTAX, LifecycleState.DEFERRED, LifecycleState.REJECTED}
    ),
    LifecycleState.VALIDATING_SYNTAX: frozenset(
        {LifecycleState.IMPLEMENTING, LifecycleState.TESTING, LifecycleState.REJECTED}
    ),
    LifecycleState.TESTING: frozenset(
        {LifecycleState.IMPLEMENTING, LifecycleState.REVIEWING, LifecycleState.REJECTED}
    ),
    LifecycleState.REVIEWING: frozenset(
        {LifecycleState.IMPLEMENTING, LifecycleState.PUBLISHING, LifecycleState.REJECTED}
    ),
    LifecycleState.PUBLISHING: frozenset(
        {LifecycleState.WAITING_CI, LifecycleState.COMPLETED, LifecycleState.FAILED}
    ),
    LifecycleState.WAITING_CI: frozenset(
        {LifecycleState.DEPLOYING, LifecycleState.REJECTED, LifecycleState.FAILED}
    ),
    LifecycleState.DEPLOYING: frozenset(
        {LifecycleState.CANARY, LifecycleState.ROLLING_BACK, LifecycleState.FAILED}
    ),
    LifecycleState.CANARY: frozenset(
        {LifecycleState.MONITORING, LifecycleState.ROLLING_BACK, LifecycleState.FAILED}
    ),
    LifecycleState.MONITORING: frozenset(
        {LifecycleState.COMPLETED, LifecycleState.ROLLING_BACK, LifecycleState.FAILED}
    ),
    LifecycleState.ROLLING_BACK: frozenset(
        {LifecycleState.FAILED, LifecycleState.REJECTED, LifecycleState.COMPLETED}
    ),
    LifecycleState.COMPLETED: frozenset({LifecycleState.IDLE}),
    LifecycleState.DEFERRED: frozenset({LifecycleState.IDLE}),
    LifecycleState.REJECTED: frozenset({LifecycleState.IDLE}),
    LifecycleState.FAILED: frozenset({LifecycleState.IDLE, LifecycleState.ROLLING_BACK}),
    LifecycleState.PAUSED: frozenset(),
    LifecycleState.DEGRADED: frozenset(),
    LifecycleState.STOPPED: frozenset(),
}

_INTERRUPTIBLE = frozenset(
    state
    for state in LifecycleState
    if state
    not in {
        LifecycleState.PAUSED,
        LifecycleState.DEGRADED,
        LifecycleState.STOPPED,
        LifecycleState.COMPLETED,
    }
)


class LifecycleMachine:
    """Thread-safe state owner with explicit pause/degraded restoration."""

    def __init__(self, run_id: str, initial: LifecycleState = LifecycleState.IDLE) -> None:
        self.run_id = run_id
        self._state = initial
        self._resume_state: LifecycleState | None = None
        self._lock = RLock()

    @property
    def state(self) -> LifecycleState:
        with self._lock:
            return self._state

    def can_transition(self, target: LifecycleState) -> bool:
        with self._lock:
            if target in {LifecycleState.PAUSED, LifecycleState.DEGRADED, LifecycleState.STOPPED}:
                return self._state in _INTERRUPTIBLE
            return target in _FORWARD[self._state]

    def transition(
        self,
        target: LifecycleState,
        reason: str,
        policy_ids: tuple[str, ...] = (),
    ) -> TransitionRecord:
        with self._lock:
            source = self._state
            if not self.can_transition(target):
                raise TransitionError(f"Illegal transition: {source.value} -> {target.value}")
            if target in {LifecycleState.PAUSED, LifecycleState.DEGRADED}:
                self._resume_state = source
            self._state = target
            return TransitionRecord(
                transition_id=new_id("transition"),
                run_id=self.run_id,
                from_state=source,
                to_state=target,
                reason=reason,
                policy_ids=policy_ids,
                occurred_at=datetime.now(UTC),
            )

    def resume(self, reason: str, policy_ids: tuple[str, ...] = ()) -> TransitionRecord:
        with self._lock:
            if self._state not in {LifecycleState.PAUSED, LifecycleState.DEGRADED}:
                raise TransitionError(f"Cannot resume from {self._state.value}")
            if self._resume_state is None:
                raise TransitionError("No durable resume state is available")
            source = self._state
            target = self._resume_state
            self._state = target
            self._resume_state = None
            return TransitionRecord(
                transition_id=new_id("transition"),
                run_id=self.run_id,
                from_state=source,
                to_state=target,
                reason=reason,
                policy_ids=policy_ids,
                occurred_at=datetime.now(UTC),
            )
