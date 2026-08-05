"""Work-conserving 24/7 scheduler for continuous improvement."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SchedulerIntervals:
    """Liveness waits only; productive work is never delayed by a cadence."""

    idle_poll_seconds: float = 30.0
    blocked_poll_seconds: float = 2.0
    preempted_poll_seconds: float = 10.0
    failure_backoff_initial_seconds: float = 5.0
    failure_backoff_max_seconds: float = 300.0


class ContinualScheduler:
    """Keep the pipeline occupied whenever policy and hardware permit work."""

    def __init__(
        self,
        *,
        collect: Callable[[], bool],
        synthesize: Callable[[], Awaitable[bool]],
        research: Callable[[], Awaitable[bool]],
        preempted: Callable[[], bool],
        blocked: Callable[[], bool],
        on_error: Callable[[Exception], None] | None = None,
        intervals: SchedulerIntervals | None = None,
    ) -> None:
        self.collect = collect
        self.synthesize = synthesize
        self.research = research
        self.preempted = preempted
        self.blocked = blocked
        self.on_error = on_error
        self.intervals = intervals or SchedulerIntervals()

    async def run_forever(self) -> None:
        """Run successive discovery/candidate cycles without a time gate."""

        failure_backoff = self.intervals.failure_backoff_initial_seconds
        while True:
            if self.blocked():
                await asyncio.sleep(self.intervals.blocked_poll_seconds)
                continue
            if self.preempted():
                await asyncio.sleep(self.intervals.preempted_poll_seconds)
                continue
            try:
                self.collect()
                await self.research()
                if self.blocked() or self.preempted():
                    continue
                completed_cycle = await self.synthesize()
                failure_backoff = self.intervals.failure_backoff_initial_seconds
                if not completed_cycle:
                    await asyncio.sleep(self.intervals.idle_poll_seconds)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if self.on_error is not None:
                    # Error reporting must never disable scheduler recovery.
                    with suppress(Exception):
                        self.on_error(exc)
                await asyncio.sleep(failure_backoff)
                failure_backoff = min(
                    self.intervals.failure_backoff_max_seconds,
                    max(self.intervals.failure_backoff_initial_seconds, failure_backoff * 2),
                )
