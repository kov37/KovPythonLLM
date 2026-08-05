"""Long-running KOV service: quiet collection, bounded autonomous candidates."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from KOV.contracts.common import new_id
from KOV.contracts.events import ActorRole, EventType
from KOV.contracts.learning import (
    EpisodeOutcome,
    LearningEpisode,
    Opportunity,
    OpportunityOrigin,
    OpportunityStatus,
)
from KOV.contracts.promotion import EvidenceManifest, ReviewDecision
from KOV.control.agent_loop import AgentRunResult, run_agent_async
from KOV.control.stop import StopController
from KOV.discovery.collectors import CollectionSnapshot, EvidenceCollector
from KOV.discovery.queue import OpportunityQueue
from KOV.git.candidates import CandidateWorktree, GitCandidateManager
from KOV.learning.distiller import distill_failure_lesson, distill_recent_failures
from KOV.learning.store import LearningStore
from KOV.observations.redaction import sanitize_text
from KOV.promotion.meaningfulness import MeaningfulnessGate
from KOV.promotion.observer import IndependentObserver
from KOV.promotion.publisher import CandidatePullRequest, GitHubPublisher
from KOV.research.client import PublicResearchClient
from KOV.runtime.privacy import apply_local_privacy_defaults
from KOV.runtime.scheduler import ContinualScheduler
from KOV.storage.artifacts import ArtifactStore
from KOV.storage.ledger import EventLedger
from KOV.storage.retention import RetentionManager

_TERMINAL_RUN_EVENTS = frozenset(
    {
        EventType.FAILURE,
        EventType.COMPLETED,
        EventType.REVIEW,
        EventType.CANDIDATE_REJECTED,
        EventType.CANDIDATE_APPROVED,
        EventType.PUBLISHED,
        EventType.RESEARCH,
    }
)


def recover_interrupted_runs(ledger: EventLedger) -> int:
    """Close nonterminal historical runs before a new daemon loop starts."""

    latest_by_run = {}
    for event in ledger.latest_events(10_000):
        latest_by_run.setdefault(event.run_id, event)
    recovered = 0
    for run_id, event in latest_by_run.items():
        if event.event_type in _TERMINAL_RUN_EVENTS:
            continue
        ledger.append(
            run_id=run_id,
            event_type=EventType.FAILURE,
            actor=ActorRole.CONTROLLER,
            idempotency_key=f"idem:{run_id.split(':', 1)[1]}-restart-recovery",
            payload={
                "status": "failed",
                "stage": "restart_recovery",
                "summary": "Interrupted run closed during daemon startup recovery.",
            },
        )
        recovered += 1
    return recovered


def reconcile_pull_requests(
    ledger: EventLedger, pull_requests: tuple[CandidatePullRequest, ...]
) -> int:
    """Append terminal outcomes proven by read-only GitHub PR state."""

    run_ids = ledger.run_ids()
    terminal_candidate_events = {
        EventType.CANDIDATE_REJECTED,
        EventType.CANDIDATE_APPROVED,
        EventType.PUBLISHED,
    }
    reconciled = 0
    for pull_request in pull_requests:
        if pull_request.state == "OPEN":
            continue
        token = pull_request.branch.removeprefix("kov/candidate-")
        matches = [run_id for run_id in run_ids if run_id.startswith(f"run:{token}")]
        if len(matches) != 1:
            continue
        run_id = matches[0]
        if any(
            event.event_type in terminal_candidate_events
            for event in ledger.events_for_run(run_id)
        ):
            continue
        merged = pull_request.state == "MERGED" or pull_request.merged_at is not None
        event_type = EventType.PUBLISHED if merged else EventType.CANDIDATE_REJECTED
        outcome = "merged" if merged else "closed_without_merge"
        ledger.append(
            run_id=run_id,
            candidate_id=pull_request.branch.split("/", 1)[1],
            event_type=event_type,
            actor=ActorRole.PUBLISHER,
            idempotency_key=(
                f"idem:{run_id.split(':', 1)[1]}-github-reconciliation-{outcome}"
            ),
            payload={
                "stage": "github_reconciliation",
                "status": outcome,
                "summary": f"GitHub reports KOV PR #{pull_request.number} {outcome}.",
                "pull_request_number": pull_request.number,
                "pull_request_url": pull_request.url,
            },
        )
        reconciled += 1
    return reconciled


class KOVDaemon:
    def __init__(self, project: Path | None = None) -> None:
        self.project = project or Path(__file__).resolve().parents[1]
        self.state = self.project / ".kov-state"
        self.target = Path(
            os.getenv("KOV_RESEARCH_TUTOR_ROOT", "/home/digichameleon/adk/research-agent")
        ).resolve()
        self.artifacts = ArtifactStore(self.state / "artifacts", self.state / "artifacts.sqlite3")
        self.artifacts.initialize()
        self.queue = OpportunityQueue(self.state / "opportunities.sqlite3")
        self.queue.initialize()
        self.queue.recover_active()
        self.learning = LearningStore(self.state / "learning.sqlite3")
        self.learning.initialize()
        self.ledger = EventLedger(self.state / "ledger.sqlite3")
        self.ledger.initialize()
        recover_interrupted_runs(self.ledger)
        distill_recent_failures(self.ledger, self.learning)
        self.stop = StopController(self.state / "control")
        self.stop.initialize()
        self.collector = EvidenceCollector(self.target, self.artifacts)
        self.retention = RetentionManager(self.artifacts)
        self._last_snapshot_digest = ""
        self._latest_snapshot: CollectionSnapshot | None = None
        self._researched_commits: dict[str, datetime] = {}
        self._candidate_active = False
        self._last_pr_reconciled_at: datetime | None = None

    def collect(self) -> bool:
        snapshot = self.collector.collect()
        changed = snapshot.artifact.digest != self._last_snapshot_digest
        self._last_snapshot_digest = snapshot.artifact.digest
        self._latest_snapshot = snapshot
        self._derive_local_opportunities(snapshot)
        self._reconcile_pull_requests()
        # A deferred candidate represents a transient controller, environment,
        # or publication failure. Permit one bounded retry; selections remain
        # durable so repeated failures cannot create an endless work loop.
        self.queue.requeue_deferred(max_selections=2)
        self.retention.enforce()
        return changed

    def _reconcile_pull_requests(self) -> int:
        now = datetime.now(UTC)
        if (
            self._last_pr_reconciled_at is not None
            and now - self._last_pr_reconciled_at < timedelta(minutes=5)
        ):
            return 0
        self._last_pr_reconciled_at = now
        try:
            pull_requests = GitHubPublisher(self.target).candidate_pull_requests()
        except (RuntimeError, json.JSONDecodeError):
            return 0
        return reconcile_pull_requests(self.ledger, pull_requests)

    async def synthesize(self) -> bool:
        if self._candidate_active:
            return False
        if self.queue.queued_count() == 0:
            return False
        publisher = GitHubPublisher(self.target, allow_merge=self._auto_merge_enabled())
        if publisher.open_candidate_url() is not None:
            return False
        self._sync_target_main()
        opportunity = self.queue.select_next()
        if opportunity is None:
            return False
        self._candidate_active = True
        try:
            criteria = " ".join(MeaningfulnessGate.criteria_for(opportunity.component))
            task = (
                f"Opportunity: {opportunity.title}. Hypothesis: {opportunity.hypothesis}. "
                f"Component: {opportunity.component}. Acceptance criteria: {criteria} "
                "Make one small, focused, reversible change. If the required evidence cannot be "
                "produced, do not invent a substitute."
            )
            result = await run_agent_async(task, str(self.target))
            await self._complete_candidate(opportunity, result)
            return True
        except Exception:
            self.queue.finish(opportunity.opportunity_id, OpportunityStatus.DEFERRED)
            raise
        finally:
            self._candidate_active = False

    async def research(self) -> bool:
        snapshot = self._latest_snapshot
        commit = snapshot.repository_commit if snapshot else None
        research_key = commit or "unknown"
        now = datetime.now(UTC)
        last_researched = self._researched_commits.get(research_key)
        if last_researched is not None and now - last_researched < timedelta(hours=6):
            return False
        self._researched_commits[research_key] = now
        client = PublicResearchClient()
        sources = (
            ("https://github.com/google/adk-python/releases", "Google ADK release changes"),
            ("https://github.com/ollama/ollama/releases", "Ollama local inference changes"),
        )
        evidence: list[str] = []
        for url, objective in sources:
            try:
                result = await asyncio.to_thread(client.fetch, url, objective=objective)
                artifact = self.artifacts.put(
                    result.text.encode(),
                    privacy_class="sanitized",
                    retention_class="routine",
                )
                evidence.append(artifact.artifact_id)
            except Exception:
                continue
        if not evidence:
            return False
        research_run = new_id("run")
        self.ledger.append(
            run_id=research_run,
            event_type=EventType.RESEARCH,
            actor=ActorRole.DISCOVERY,
            idempotency_key=f"idem:{research_run.split(':', 1)[1]}-research",
            payload={
                "status": "completed",
                "stage": "public_release_research",
                "summary": "Sanitized ADK and Ollama release evidence refreshed.",
                "source_count": len(evidence),
                "evidence_refs": evidence,
                "refresh_after_seconds": 21_600,
            },
        )
        return bool(evidence)

    def preempted(self) -> bool:
        if self._candidate_active:
            return True
        result = subprocess.run(
            ("nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"),
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
        try:
            return result.returncode == 0 and int(result.stdout.splitlines()[0]) >= 70
        except (IndexError, ValueError):
            return False

    def blocked(self) -> bool:
        status = self.stop.status()
        return status.paused or status.emergency_stopped

    def _derive_local_opportunities(self, snapshot: CollectionSnapshot) -> None:
        if snapshot.service_status is None or snapshot.service_status >= 500:
            fingerprint = hashlib.sha256(
                f"service-unhealthy:{snapshot.repository_commit}".encode()
            ).hexdigest()
            self.queue.add(
                Opportunity(
                    opportunity_id=new_id("opportunity"),
                    origin=OpportunityOrigin.EVIDENCE,
                    title="Improve Research Tutor health-check reliability",
                    hypothesis=(
                        "The local health endpoint is unavailable or failing; a focused diagnosis "
                        "may identify a reversible reliability improvement."
                    ),
                    component="service-runtime",
                    severity=80,
                    evidence_refs=(snapshot.artifact.artifact_id,),
                    fingerprint=fingerprint,
                    created_at=datetime.now(UTC),
                )
            )
        if snapshot.indexing_error_count is not None and snapshot.indexing_error_count > 0:
            fingerprint = hashlib.sha256(
                (
                    f"indexing-errors:{snapshot.repository_commit}:"
                    f"{snapshot.indexing_error_count}"
                ).encode()
            ).hexdigest()
            self.queue.add(
                Opportunity(
                    opportunity_id=new_id("opportunity"),
                    origin=OpportunityOrigin.EVIDENCE,
                    title="Eliminate one observed document-indexing failure",
                    hypothesis=(
                        f"The sanitized library aggregate reports "
                        f"{snapshot.indexing_error_count} indexing failure(s); one focused "
                        "diagnosis may identify a reproducible reliability fix without exposing "
                        "the affected filename or error text."
                    ),
                    component="reliability",
                    severity=70,
                    evidence_refs=(snapshot.artifact.artifact_id,),
                    fingerprint=fingerprint,
                    created_at=datetime.now(UTC),
                )
            )
        if snapshot.qdrant_status is None or snapshot.qdrant_status >= 500:
            fingerprint = hashlib.sha256(
                f"qdrant-unhealthy:{snapshot.repository_commit}".encode()
            ).hexdigest()
            self.queue.add(
                Opportunity(
                    opportunity_id=new_id("opportunity"),
                    origin=OpportunityOrigin.EVIDENCE,
                    title="Restore Research Tutor vector-store reliability",
                    hypothesis=(
                        "The local Qdrant health endpoint is unavailable or failing while the "
                        "Tutor depends on vector retrieval; a focused diagnosis may identify a "
                        "reproducible reliability improvement."
                    ),
                    component="service-runtime",
                    severity=90,
                    evidence_refs=(snapshot.artifact.artifact_id,),
                    fingerprint=fingerprint,
                    created_at=datetime.now(UTC),
                )
            )
        if snapshot.test_file_count * 3 < max(1, snapshot.python_file_count):
            fingerprint = hashlib.sha256(
                f"test-density:{snapshot.repository_commit}".encode()
            ).hexdigest()
            self.queue.add(
                Opportunity(
                    opportunity_id=new_id("opportunity"),
                    origin=OpportunityOrigin.EVIDENCE,
                    title="Add one missing behavior-focused regression test",
                    hypothesis=(
                        "The repository has substantially fewer test modules than Python modules; "
                        "one evidence-backed invariant may be under-protected."
                    ),
                    component="tests",
                    severity=45,
                    evidence_refs=(snapshot.artifact.artifact_id,),
                    fingerprint=fingerprint,
                    created_at=datetime.now(UTC),
                )
            )

    async def _complete_candidate(self, opportunity: Opportunity, result: AgentRunResult) -> None:
        manager = GitCandidateManager(self.target, self.state / "worktrees")
        base = subprocess.run(
            ("git", "-C", str(result.worktree), "rev-parse", "HEAD"),
            capture_output=True,
            check=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        candidate = CandidateWorktree(result.candidate_id, result.branch, result.worktree, base)
        if result.status != "passed" or not result.changed_files:
            self._record_episode(opportunity, result, EpisodeOutcome.REJECTED, result.final_summary)
            self.queue.finish(opportunity.opportunity_id, OpportunityStatus.REJECTED)
            self._remove_candidate(manager, candidate, delete_branch=True, force=True)
            return
        events = self.ledger.events_for_run(result.run_id)
        diff = manager.diff(candidate)
        meaningfulness = MeaningfulnessGate.evaluate(
            component=opportunity.component,
            changed_files=result.changed_files,
            events=events,
            diff=diff,
        )
        self.ledger.append(
            run_id=result.run_id,
            candidate_id=result.candidate_id,
            event_type=EventType.EVIDENCE_GATE,
            actor=ActorRole.EVALUATOR,
            idempotency_key=f"idem:{result.run_id.split(':', 1)[1]}-evidence-gate",
            payload=meaningfulness.model_dump(mode="json"),
        )
        if not meaningfulness.allowed:
            reason = "Missing deterministic evidence: " + ", ".join(meaningfulness.missing)
            self._record_episode(opportunity, result, EpisodeOutcome.INADEQUATE_TEST, reason)
            self._record_candidate_outcome(
                result, EventType.CANDIDATE_REJECTED, "evidence_gate", reason
            )
            self.queue.finish(opportunity.opportunity_id, OpportunityStatus.REJECTED)
            self._remove_candidate(manager, candidate, delete_branch=True, force=True)
            return
        observer = await IndependentObserver().review(
            diff=diff,
            check_manifest=json.dumps(
                {"status": result.status, "changed_files": result.changed_files}, sort_keys=True
            ),
        )
        observer_summary, _ = sanitize_text(observer.summary)
        self.ledger.append(
            run_id=result.run_id,
            candidate_id=result.candidate_id,
            event_type=EventType.REVIEW,
            actor=ActorRole.REVIEWER,
            idempotency_key=f"idem:{result.run_id.split(':', 1)[1]}-observer",
            payload={
                "decision": observer.decision.value,
                "summary": observer_summary,
                "blocking_findings": sum(
                    finding.startswith("BLOCKER:")
                    for finding in (
                        *observer.correctness_findings,
                        *observer.security_findings,
                        *observer.test_findings,
                    )
                ),
            },
        )
        if observer.decision is not ReviewDecision.APPROVE:
            self._record_episode(opportunity, result, EpisodeOutcome.REJECTED, observer_summary)
            self.queue.finish(opportunity.opportunity_id, OpportunityStatus.REJECTED)
            self._record_candidate_outcome(
                result, EventType.CANDIDATE_REJECTED, "observer", observer_summary
            )
            self._remove_candidate(manager, candidate, delete_branch=True, force=True)
            return
        commit = manager.commit(candidate, opportunity.title[:72])
        diff_digest = hashlib.sha256(diff.encode()).hexdigest()
        artifacts = tuple(
            json.loads(event.payload_json).get("artifact_id")
            for event in self.ledger.events_for_run(result.run_id)
            if event.event_type.value == "observation.recorded"
            and json.loads(event.payload_json).get("artifact_id")
        )
        manifest = EvidenceManifest(
            candidate_id=result.candidate_id,
            base_commit=base,
            candidate_commit=commit,
            changed_files=result.changed_files,
            check_artifacts=artifacts or opportunity.evidence_refs,
            observer_verdict=observer.decision,
            diff_digest=diff_digest,
            rollback_ready=True,
        )
        if os.getenv("KOV_PUBLISH_DRAFTS", "true").lower() == "true":
            body = (
                "## KOV evidence\n\n"
                f"{opportunity.hypothesis}\n\n"
                f"Independent observer: {observer.summary}\n\n"
                f"Manifest digest: `{diff_digest}`\n"
            )
            try:
                publisher = GitHubPublisher(result.worktree, allow_merge=self._auto_merge_enabled())
                publication = publisher.publish_draft(
                    branch=result.branch,
                    title=f"KOV: {opportunity.title}",
                    body=body,
                    manifest=manifest,
                )
            except PermissionError as exc:
                reason, _ = sanitize_text(str(exc))
                self._record_episode(opportunity, result, EpisodeOutcome.REJECTED, reason)
                self._record_candidate_outcome(
                    result, EventType.CANDIDATE_REJECTED, "publication", reason
                )
                self.queue.finish(opportunity.opportunity_id, OpportunityStatus.DEFERRED)
                self._remove_candidate(manager, candidate)
                return
            if self._auto_merge_enabled():
                publisher.mark_ready(publication.pull_request_url)
                publisher.merge(publication.pull_request_url)
            self._record_candidate_outcome(
                result,
                EventType.PUBLISHED,
                "publication",
                publication.pull_request_url,
            )
        else:
            self._record_candidate_outcome(
                result,
                EventType.CANDIDATE_APPROVED,
                "local_only",
                "All local evidence gates and observer review passed.",
            )
        self.queue.finish(opportunity.opportunity_id, OpportunityStatus.COMPLETED)
        self._record_episode(opportunity, result, EpisodeOutcome.SUCCESS, result.final_summary)
        self._remove_candidate(manager, candidate)

    @staticmethod
    def _auto_merge_enabled() -> bool:
        return os.getenv("KOV_AUTO_MERGE", "false").lower() == "true"

    def _sync_target_main(self) -> None:
        status = subprocess.run(
            ("git", "-C", str(self.target), "status", "--porcelain"),
            capture_output=True,
            check=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        if status:
            raise RuntimeError("Research Tutor main checkout is not clean")
        subprocess.run(
            ("git", "-C", str(self.target), "fetch", "origin", "main"),
            capture_output=True,
            check=True,
            text=True,
            timeout=30,
        )
        subprocess.run(
            ("git", "-C", str(self.target), "merge", "--ff-only", "origin/main"),
            capture_output=True,
            check=True,
            text=True,
            timeout=30,
        )

    def _record_candidate_outcome(
        self,
        result: AgentRunResult,
        event_type: EventType,
        stage: str,
        summary: str,
    ) -> None:
        safe_summary, _ = sanitize_text(summary)
        self.ledger.append(
            run_id=result.run_id,
            candidate_id=result.candidate_id,
            event_type=event_type,
            actor=ActorRole.CONTROLLER,
            idempotency_key=(f"idem:{result.run_id.split(':', 1)[1]}-candidate-{event_type.value}"),
            payload={"stage": stage, "summary": safe_summary},
        )

    def _record_episode(
        self,
        opportunity: Opportunity,
        result: AgentRunResult,
        outcome: EpisodeOutcome,
        summary: str,
    ) -> None:
        safe_summary, _ = sanitize_text(summary)
        event_refs = tuple(event.event_id for event in self.ledger.events_for_run(result.run_id))
        self.learning.add_episode(
            LearningEpisode(
                episode_id=new_id("episode"),
                run_id=result.run_id,
                outcome=outcome,
                strategy=opportunity.hypothesis,
                component=opportunity.component,
                summary=safe_summary or outcome.value,
                evidence_refs=event_refs or opportunity.evidence_refs,
                created_at=datetime.now(UTC),
            )
        )
        if outcome is not EpisodeOutcome.SUCCESS:
            lesson = distill_failure_lesson(self.ledger.events_for_run(result.run_id))
            if lesson is not None:
                self.learning.add_lesson(lesson, set(event_refs))

    @staticmethod
    def _remove_candidate(
        manager: GitCandidateManager,
        candidate: CandidateWorktree,
        *,
        delete_branch: bool = False,
        force: bool = False,
    ) -> None:
        try:
            manager.remove(candidate, delete_branch=delete_branch, force=force)
        except (OSError, RuntimeError):
            # Cleanup must not rewrite a durable candidate outcome. Git's own
            # worktree metadata preserves enough information for later pruning.
            return

    async def run(self) -> None:
        scheduler = ContinualScheduler(
            collect=self.collect,
            synthesize=self.synthesize,
            research=self.research,
            preempted=self.preempted,
            blocked=self.blocked,
            on_error=self._record_scheduler_error,
        )
        await scheduler.run_forever()

    def _record_scheduler_error(self, error: Exception) -> None:
        """Expose sanitized background failures without persisting trace content."""

        run_id = new_id("run")
        summary, _ = sanitize_text(f"{type(error).__name__}: {error}")
        self.ledger.append(
            run_id=run_id,
            event_type=EventType.FAILURE,
            actor=ActorRole.CONTROLLER,
            idempotency_key=f"idem:{run_id.split(':', 1)[1]}-scheduler-failure",
            payload={
                "status": "failed",
                "stage": "continual_scheduler",
                "summary": summary or type(error).__name__,
            },
        )


def main() -> None:
    apply_local_privacy_defaults()
    asyncio.run(KOVDaemon().run())


if __name__ == "__main__":
    main()
