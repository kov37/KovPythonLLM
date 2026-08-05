"""Deterministic autonomous repository coding loop."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from KOV.contracts.actions import (
    CreateFileAction,
    DeletePathAction,
    EditLinesAction,
    MovePathAction,
    RepoSnapshotAction,
    RunCheckAction,
    SearchCodeAction,
    SubmitCandidateAction,
    ViewArtifactAction,
    ViewFileAction,
)
from KOV.contracts.common import new_id
from KOV.contracts.events import ActorRole, EventType
from KOV.contracts.observations import Observation, ObservationStatus
from KOV.contracts.state import LifecycleState
from KOV.control.policies import PolicyRegistry
from KOV.control.state_machine import LifecycleMachine
from KOV.control.stop import StopController
from KOV.git.candidates import CandidateWorktree, GitCandidateManager
from KOV.learning.store import LearningStore
from KOV.models.adk_gateway import ADKActionGateway, StructuredOutputError
from KOV.observations.compressor import CPRSCompressor
from KOV.observations.redaction import sanitize_text
from KOV.storage.artifacts import ArtifactStore
from KOV.storage.ledger import EventLedger
from KOV.tools.atomic import AtomicWorkspaceTools
from KOV.tools.commands import CommandResult, CommandRunner
from KOV.tools.syntax import SyntaxResult, SyntaxVerifier
from KOV.workspaces.registry import WorkspaceMode, WorkspaceRegistry, WorkspaceSpec


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    run_id: str
    candidate_id: str
    status: str
    iterations: int
    worktree: Path
    branch: str
    changed_files: tuple[str, ...]
    final_summary: str


class AgentLoopError(RuntimeError):
    """Controller-owned terminal failure."""


class RepositoryAgentController:
    """Owns the loop; the model can only propose one typed atomic action."""

    def __init__(
        self,
        *,
        gateway: ADKActionGateway,
        state_root: Path,
        policy_directory: Path,
        max_iterations: int = 80,
        max_wall_seconds: int = 900,
    ) -> None:
        self.gateway = gateway
        self.state_root = state_root
        self.max_iterations = max_iterations
        self.max_wall_seconds = max_wall_seconds
        self.policies = PolicyRegistry.load(policy_directory)
        self.ledger = EventLedger(state_root / "ledger.sqlite3")
        self.artifacts = ArtifactStore(state_root / "artifacts", state_root / "artifacts.sqlite3")
        self.stop = StopController(state_root / "control")
        self.compressor = CPRSCompressor()
        self.learning = LearningStore(state_root / "learning.sqlite3")
        self.ledger.initialize()
        self.artifacts.initialize()
        self.learning.initialize()
        self.stop.initialize()

    async def run(self, task_description: str, repo_path: str) -> AgentRunResult:
        repository = Path(repo_path).resolve()
        sanitized_task, _ = sanitize_text(task_description)
        if not sanitized_task.strip() or len(sanitized_task) > 8_000:
            raise ValueError("Task description is empty or exceeds 8000 characters")
        run_id = new_id("run")
        candidate_slug = f"candidate-{run_id.split(':', 1)[1][:12]}"
        candidate_manager = GitCandidateManager(repository, self.state_root / "worktrees")
        candidate = candidate_manager.create(candidate_slug)
        python = repository / ".venv" / "bin" / "python"
        frontend_dependencies = repository / "frontend" / "node_modules"
        candidate_frontend = candidate.path / "frontend"
        if frontend_dependencies.is_dir() and candidate_frontend.is_dir():
            (candidate_frontend / "node_modules").symlink_to(
                frontend_dependencies, target_is_directory=True
            )
        registry = WorkspaceRegistry(
            (
                WorkspaceSpec(
                    name="candidate",
                    root=candidate.path,
                    mode=WorkspaceMode.CANDIDATE,
                    python_executable=python if python.is_file() else Path(sys.executable),
                    read_only_dependencies=(frontend_dependencies,)
                    if frontend_dependencies.is_dir()
                    else (),
                ),
            )
        )
        tools = AtomicWorkspaceTools(registry)
        commands = CommandRunner(registry, self.artifacts)
        syntax = SyntaxVerifier(registry)
        machine = LifecycleMachine(run_id)
        task_digest = hashlib.sha256(sanitized_task.encode()).hexdigest()
        self._event(
            run_id,
            EventType.RUN_CREATED,
            "run-created",
            {
                "task_digest": task_digest,
                "candidate": candidate_slug,
                "repository": repository.name,
            },
        )
        self._advance_to_implementation(machine)
        started = time.monotonic()
        matched_lessons = self.learning.retrieve(sanitized_task, limit=3)
        lessons_by_id = {lesson.lesson_id: lesson for lesson in matched_lessons}
        for lesson in self.learning.recent_lessons(limit=2):
            lessons_by_id.setdefault(lesson.lesson_id, lesson)
        lessons = tuple(lessons_by_id.values())[:3]
        learning_packet = "\n".join(
            f"LESSON {lesson.lesson_id}: {lesson.guidance} (confidence={lesson.confidence:.2f})"
            for lesson in lessons
        )
        state_packet = (
            "Workspace: candidate\nNo evidence has been collected. Begin with repo_snapshot or "
            "a narrow search."
            + (f"\nRELEVANT PRIOR LEARNING\n{learning_packet}" if learning_packet else "")
        )
        invalid_count = 0
        repeated_action_count = 0
        previous_fingerprint = ""
        dirty = False
        file_digests: dict[str, str] = {}
        file_lengths: dict[str, int] = {}

        for iteration in range(1, self.max_iterations + 1):
            self._check_control(machine)
            if time.monotonic() - started > self.max_wall_seconds:
                return self._terminal(
                    machine,
                    candidate_manager,
                    candidate,
                    iteration - 1,
                    "failed",
                    "Protected wall-time budget expired.",
                )
            try:
                turn = await self.gateway.propose(
                    task=sanitized_task,
                    state_packet=self._bounded_state(
                        machine.state,
                        state_packet,
                        dirty,
                        candidate_manager.changed_files(candidate),
                        file_digests,
                        file_lengths,
                    ),
                )
            except StructuredOutputError as exc:
                invalid_count += 1
                state_packet = self._append_state(
                    state_packet, f"SCHEMA REJECTION {invalid_count}/3: {exc}"
                )
                self._event(
                    run_id,
                    EventType.ACTION_REJECTED,
                    f"schema-{iteration}",
                    {"reason": str(exc)[:1_000]},
                )
                if invalid_count >= 3:
                    return self._terminal(
                        machine,
                        candidate_manager,
                        candidate,
                        iteration,
                        "failed",
                        "Model failed the structured-output contract three times.",
                    )
                continue
            invalid_count = 0
            proposal = turn.proposal
            action = proposal.requested_action
            fingerprint = hashlib.sha256(
                action.model_dump_json(exclude={"replacement_text", "content"}).encode()
            ).hexdigest()
            repeated_action_count = (
                repeated_action_count + 1 if fingerprint == previous_fingerprint else 0
            )
            previous_fingerprint = fingerprint
            self._event(
                run_id,
                EventType.DECISION,
                f"decision-{iteration}",
                {
                    "summary": proposal.decision_summary,
                    "expected_outcome": proposal.expected_outcome,
                    "uncertainty": proposal.uncertainty.value,
                    "action_kind": action.kind,
                    "model_duration_ms": turn.duration_ms,
                    "input_tokens": turn.input_tokens,
                    "output_tokens": turn.output_tokens,
                },
                actor=ActorRole.IMPLEMENTER,
            )
            if repeated_action_count >= 3:
                state_packet = self._append_state(
                    state_packet,
                    "NO-PROGRESS GUARD: choose a different evidence-backed action.",
                )
                continue

            if isinstance(action, RunCheckAction):
                observation, syntax_result = self._syntax_gate(
                    machine, syntax, candidate_manager.changed_files(candidate), iteration
                )
                if not syntax_result.passed:
                    state_packet = self._append_state(state_packet, observation.summary)
                    continue
                self._transition(machine, LifecycleState.TESTING, "Syntax gate passed")
            authorization = self.policies.authorize_action(action, machine.state)
            self._event(
                run_id,
                EventType.ACTION_AUTHORIZED if authorization.allowed else EventType.ACTION_REJECTED,
                f"authorization-{iteration}",
                {
                    "kind": action.kind,
                    "allowed": authorization.allowed,
                    "reason": authorization.reason,
                },
            )
            if not authorization.allowed:
                state_packet = self._append_state(
                    state_packet, f"POLICY REJECTION: {authorization.reason}"
                )
                if machine.state in {LifecycleState.TESTING, LifecycleState.VALIDATING_SYNTAX}:
                    self._transition(
                        machine, LifecycleState.IMPLEMENTING, "Return to implementation"
                    )
                continue

            if isinstance(action, SubmitCandidateAction):
                if not dirty:
                    state_packet = self._append_state(
                        state_packet, "Candidate cannot be submitted before a focused change."
                    )
                    continue
                observation, syntax_result = self._syntax_gate(
                    machine, syntax, candidate_manager.changed_files(candidate), iteration
                )
                if not syntax_result.passed:
                    state_packet = self._append_state(state_packet, observation.summary)
                    continue
                self._transition(machine, LifecycleState.TESTING, "Submission syntax passed")
                test_action = RunCheckAction(workspace="candidate", profile="python.tests")
                test_observation = self._execute(test_action, tools, commands, sanitized_task)
                self._record_observation(run_id, iteration, test_observation)
                if test_observation.exit_code == 0:
                    return self._terminal(
                        machine,
                        candidate_manager,
                        candidate,
                        iteration,
                        "passed",
                        action.summary,
                    )
                self._transition(machine, LifecycleState.IMPLEMENTING, "Tests failed")
                state_packet = self._append_state(state_packet, test_observation.summary)
                continue

            observation = self._execute(action, tools, commands, sanitized_task)
            self._record_observation(run_id, iteration, observation)
            if isinstance(action, (ViewFileAction, EditLinesAction, CreateFileAction)):
                if observation.content_digest:
                    file_digests[action.path] = observation.content_digest
                if isinstance(action, ViewFileAction):
                    length_match = re.search(r"\[lines \d+-\d+/(\d+); digest=", observation.summary)
                    if length_match:
                        file_lengths[action.path] = int(length_match.group(1))
            elif isinstance(action, DeletePathAction):
                if observation.status is ObservationStatus.SUCCESS:
                    file_digests.pop(action.path, None)
            elif (
                isinstance(action, MovePathAction)
                and observation.status is ObservationStatus.SUCCESS
            ):
                file_digests.pop(action.source, None)
                if observation.content_digest:
                    file_digests[action.destination] = observation.content_digest
            if isinstance(
                action, (EditLinesAction, CreateFileAction, MovePathAction, DeletePathAction)
            ):
                dirty = observation.status is ObservationStatus.SUCCESS or dirty
            if isinstance(action, RunCheckAction):
                if observation.exit_code == 0 and action.profile == "python.tests":
                    return self._terminal(
                        machine,
                        candidate_manager,
                        candidate,
                        iteration,
                        "passed",
                        "Designated test command passed.",
                    )
                self._transition(machine, LifecycleState.IMPLEMENTING, "Check completed")
            state_packet = self._append_state(
                state_packet,
                f"ACTION {action.kind} -> {observation.status.value}\n{observation.summary}",
            )

        return self._terminal(
            machine,
            candidate_manager,
            candidate,
            self.max_iterations,
            "failed",
            "Protected iteration budget exhausted.",
        )

    def _execute(
        self,
        action: object,
        tools: AtomicWorkspaceTools,
        commands: CommandRunner,
        objective: str,
    ) -> Observation:
        started = time.monotonic()
        status = ObservationStatus.SUCCESS
        artifact_id: str | None = None
        digest: str | None = None
        exit_code: int | None = None
        try:
            if isinstance(action, RepoSnapshotAction):
                result = tools.repo_snapshot(action)
                text = "\n".join(result.matches) or "Repository contains no visible files."
            elif isinstance(action, ViewFileAction):
                result = tools.view_file(action)
                text, digest = result.content, result.digest
                text += (
                    f"\n[lines {result.line_start}-{result.line_end}/{result.total_lines}; "
                    f"digest={result.digest}]"
                )
            elif isinstance(action, SearchCodeAction):
                result = tools.search_code(action)
                text = "\n".join(result.matches) or "No matches."
            elif isinstance(action, EditLinesAction):
                result = tools.edit_lines(action)
                text, digest = result.changed_hunk, result.digest
            elif isinstance(action, CreateFileAction):
                result = tools.create_file(action)
                text, digest = result.changed_hunk, result.digest
            elif isinstance(action, MovePathAction):
                result = tools.move_path(action)
                text, digest = result.changed_hunk, result.digest
            elif isinstance(action, DeletePathAction):
                result = tools.delete_path(action)
                text = result.changed_hunk
            elif isinstance(action, RunCheckAction):
                command = commands.run(action)
                text, artifact_id, exit_code, status = self._command_text(command, commands)
            elif isinstance(action, ViewArtifactAction):
                raw = self.artifacts.read(action.artifact_id).decode("utf-8", errors="replace")
                lines = raw.splitlines()
                text = "\n".join(lines[action.line_start - 1 : action.line_end])
            else:
                raise TypeError(f"Unsupported controller action: {type(action).__name__}")
        except Exception as exc:
            status = ObservationStatus.REJECTED
            text = f"{type(exc).__name__}: {exc}"
        reduced = self.compressor.compress(text, objective=objective)
        return Observation(
            observation_id=new_id("observation"),
            action_kind=getattr(action, "kind", "unknown"),
            status=status
            if not reduced.compressed
            else (
                status if status is not ObservationStatus.SUCCESS else ObservationStatus.TRUNCATED
            ),
            summary=reduced.text[:12_000] or "No output.",
            artifact_id=artifact_id,
            content_digest=digest,
            exit_code=exit_code,
            duration_ms=int((time.monotonic() - started) * 1000),
            byte_count=len(text.encode()),
            line_count=reduced.original_lines,
            hidden_line_count=reduced.hidden_lines,
            redacted=reduced.redacted,
        )

    def _command_text(
        self, result: CommandResult, commands: CommandRunner
    ) -> tuple[str, str, int, ObservationStatus]:
        stdout = commands.artifacts.read(result.stdout.artifact_id).decode("utf-8", "replace")
        stderr = commands.artifacts.read(result.stderr.artifact_id).decode("utf-8", "replace")
        status = (
            ObservationStatus.TIMEOUT
            if result.timed_out
            else ObservationStatus.SUCCESS
            if result.returncode == 0
            else ObservationStatus.FAILURE
        )
        text = f"$ {' '.join(result.argv)}\n{stdout}\n{stderr}\nexit code: {result.returncode}"
        return text, result.stdout.artifact_id, result.returncode, status

    def _syntax_gate(
        self,
        machine: LifecycleMachine,
        verifier: SyntaxVerifier,
        changed_files: tuple[str, ...],
        iteration: int,
    ) -> tuple[Observation, SyntaxResult]:
        if machine.state is LifecycleState.IMPLEMENTING:
            self._transition(machine, LifecycleState.VALIDATING_SYNTAX, "Mandatory syntax gate")
        result = verifier.verify("candidate", changed_files)
        observation = Observation(
            observation_id=new_id("observation"),
            action_kind="syntax_gate",
            status=ObservationStatus.SUCCESS if result.passed else ObservationStatus.FAILURE,
            summary=result.summary(),
            line_count=len(result.failures),
        )
        self._record_observation(machine.run_id, iteration, observation, suffix="syntax")
        if not result.passed:
            self._transition(machine, LifecycleState.IMPLEMENTING, "Syntax failure requires repair")
        return observation, result

    def _advance_to_implementation(self, machine: LifecycleMachine) -> None:
        for target, reason in (
            (LifecycleState.COLLECTING, "Run initialized"),
            (LifecycleState.TRIAGING, "Candidate selected"),
            (LifecycleState.HYPOTHESIZING, "Bounded coding task accepted"),
            (LifecycleState.BASELINING, "Repository worktree isolated"),
            (LifecycleState.IMPLEMENTING, "Atomic action loop ready"),
        ):
            self._transition(machine, target, reason)

    def _transition(self, machine: LifecycleMachine, target: LifecycleState, reason: str) -> None:
        record = machine.transition(target, reason)
        self._event(
            machine.run_id,
            EventType.STATE_TRANSITION,
            record.transition_id.replace(":", "-"),
            {"from": record.from_state.value, "to": record.to_state.value, "reason": reason},
        )

    def _check_control(self, machine: LifecycleMachine) -> None:
        control = self.stop.status()
        if control.emergency_stopped:
            if machine.can_transition(LifecycleState.STOPPED):
                self._transition(machine, LifecycleState.STOPPED, "Emergency Stop sentinel present")
            raise AgentLoopError("Emergency Stop is active")
        if control.paused:
            if machine.can_transition(LifecycleState.PAUSED):
                self._transition(machine, LifecycleState.PAUSED, "Pause sentinel present")
            raise AgentLoopError("KOV is paused")

    def _record_observation(
        self, run_id: str, iteration: int, observation: Observation, *, suffix: str = "tool"
    ) -> None:
        self._event(
            run_id,
            EventType.OBSERVATION,
            f"observation-{iteration}-{suffix}",
            observation.model_dump(mode="json"),
        )

    def _terminal(
        self,
        machine: LifecycleMachine,
        manager: GitCandidateManager,
        candidate: CandidateWorktree,
        iterations: int,
        status: str,
        summary: str,
    ) -> AgentRunResult:
        event_type = EventType.COMPLETED if status == "passed" else EventType.FAILURE
        self._event(
            machine.run_id,
            event_type,
            f"terminal-{status}",
            {"status": status, "summary": summary},
        )
        return AgentRunResult(
            run_id=machine.run_id,
            candidate_id=candidate.candidate_id,
            status=status,
            iterations=iterations,
            worktree=candidate.path,
            branch=candidate.branch,
            changed_files=manager.changed_files(candidate),
            final_summary=summary,
        )

    def _event(
        self,
        run_id: str,
        event_type: EventType,
        suffix: str,
        payload: dict[str, object],
        *,
        actor: ActorRole = ActorRole.CONTROLLER,
    ) -> None:
        safe_suffix = "".join(character if character.isalnum() else "-" for character in suffix)
        self.ledger.append(
            run_id=run_id,
            event_type=event_type,
            actor=actor,
            idempotency_key=f"idem:{run_id.split(':', 1)[1]}-{safe_suffix}"[:96],
            payload=payload,
        )

    @staticmethod
    def _bounded_state(
        state: LifecycleState,
        previous: str,
        dirty: bool,
        changed_files: tuple[str, ...],
        file_digests: dict[str, str],
        file_lengths: dict[str, int],
    ) -> str:
        packet = {
            "lifecycle_state": state.value,
            "candidate_dirty": dirty,
            "changed_files": changed_files,
            "file_digests": file_digests,
            "file_lengths": file_lengths,
            "observation": previous,
        }
        encoded = json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) <= 24_000:
            return encoded
        packet["observation"] = "[older evidence compacted]\n" + previous[-10_000:]
        return json.dumps(packet, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _append_state(previous: str, new_evidence: str, *, limit: int = 18_000) -> str:
        combined = f"{previous}\n\n--- NEXT EVIDENCE ---\n{new_evidence}"
        if len(combined) <= limit:
            return combined
        return "[older evidence compacted]\n" + combined[-limit:]


async def run_agent_async(task_description: str, repo_path: str) -> AgentRunResult:
    project = Path(__file__).resolve().parents[2]
    controller = RepositoryAgentController(
        gateway=ADKActionGateway(),
        state_root=project / ".kov-state",
        policy_directory=project / "policies" / "registry",
    )
    return await controller.run(task_description, repo_path)


def run_agent(task_description: str, repo_path: str) -> AgentRunResult:
    """Synchronous production entrypoint requested by the local harness API."""

    return asyncio.run(run_agent_async(task_description, repo_path))
