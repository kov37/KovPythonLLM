# KOV Autonomous Improvement Harness Implementation Plan

Status: initial implementation plan
Companion specification: `docs/research-tutor-improvement-decisions.md`
Initial target: `/home/digichameleon/adk/research-agent`
Model: `qwen3.5-kilo:9b` through Ollama, 32K context, Google ADK boundary

## 1. Outcome

Refactor KOV from its current conversational LangChain/LangGraph prototype into
an event-driven, deterministic repository-engineering controller that can:

1. Observe sanitized Research Tutor evidence continuously.
2. Discover and research improvement opportunities autonomously.
3. Implement one isolated candidate at a time with atomic tools.
4. Evaluate candidates through protected deterministic gates.
5. Explain every positive and negative decision in a polished local dashboard.
6. Publish, merge, deploy, monitor, and roll back qualifying changes.
7. Learn from outcomes through durable episodes, compact lessons, and retrieval.
8. Build and promote isolated successor versions of KOV itself while preserving
   an immutable root of trust.

The implementation must never depend on Qwen remembering the complete product
specification. Pydantic contracts, policy code, state transitions, capability
boundaries, tests, and durable evidence enforce the specification.

## 2. Current baseline and migration posture

The current repository contains approximately 1,350 lines across:

- `KOV/core/agent.py`: an unused basic LangGraph tool loop, removed during Phase 0.
- `KOV/core/advanced_agent.py`: a prompt-driven six-stage agent using dataclasses,
  string parsing, and conversational history.
- `KOV/tools/operations.py`: whole-file operations, string replacement, URL
  fetching, and string-based shell execution.
- `KOV/cli/main.py`: a Rich/Typer interactive terminal.
- Two small test modules.

The working tree already contains user changes adding repository navigation,
multi-edit, Git status, Git diff, and tests. Those changes are preserved as
baseline evidence. They are not silently discarded during the refactor.

The repository has no managed virtual environment or modern `pyproject.toml`.
Python 3.12.3 is installed, but the system interpreter currently has no `pytest`.
Phase 0 therefore establishes a reproducible environment before behavior is
changed.

The unused basic `KOVAgent` and its LangGraph dependency were removed in Phase 0.
The old `AdvancedKOVAgent` remains available behind a legacy entry point until a
deterministic vertical slice replaces its chat behavior. It is then removed in a
focused cleanup PR rather than edited into the new controller incrementally.

## 3. Target runtime architecture

```text
systemd user service
        |
        v
Deterministic Supervisor ---- Pause / Emergency Stop
        |
        +-- Policy Registry and Capability Authorizer
        +-- Lifecycle State Machine
        +-- Scheduler and GPU Lease
        +-- SQLite Event and Learning Store
        +-- Sanitized Artifact Store
        +-- Dashboard API and Projections
        |
        +-- Google ADK Adapter --> Ollama --> Qwen 3.5:9B
        |                         one typed proposal per invocation
        |
        +-- Atomic Workspace Tools
        +-- Deterministic Evaluator
        +-- Protected GitHub Publisher
        +-- Guarded Deployment and Rollback
        +-- Continual Learning and Self-Improvement
```

Google ADK is an inference adapter, not the orchestrator. It receives one fresh,
bounded role request and returns one typed proposal. The KOV supervisor owns all
state, authority, execution, retries, memory, publication, and deployment.

## 4. Proposed package structure

```text
KOV/
  api/                 # localhost dashboard API, auth, SSE projections
  cli/                 # chat, status, pause, stop, resume, doctor
  config/              # strict settings and machine profile
  contracts/           # Pydantic actions, observations, events, decisions
  control/             # supervisor, state machine, scheduler, policy registry
  discovery/           # collectors, opportunity queue, research evidence
  evaluation/          # syntax, tests, benchmarks, privacy, promotion
  inference/           # Google ADK adapter, Ollama client, role context builder
  learning/            # episode builder, compaction, lessons, retrieval
  observations/        # redaction, CPRS reduction, artifact slicing
  publishing/          # GitHub App publisher and branch state
  recursive/           # KOV successor build, replay, activation, rollback
  runtime/             # GPU/Ollama metrics and protected capability client
  storage/             # SQLite ledger, projections, content-addressed artifacts
  tools/               # atomic filesystem and named command profiles
  workspaces/          # path policy, repositories, worktrees, digests
frontend/
  src/                 # React/TypeScript operator dashboard
policies/
  registry/            # versioned machine-readable policy definitions
scripts/
  run_kov.py
  setup_check.py
  install_user_service.py
tests/
  unit/
  integration/
  policy/
  replay/
```

The local API uses FastAPI and server-sent events. The dashboard uses
React/TypeScript with Vite and a purpose-built light/dark design system. SQLite
WAL and content-addressed files avoid another database service.

## 5. Delivery phases

Each phase ends in a runnable, testable checkpoint. Pull requests remain focused;
no phase authorizes a single monolithic implementation PR.

### Phase 0 - Reproducible baseline

Status: completed and verified on 2026-08-04. See `docs/phase-0-baseline.md`.

Deliverables:

- Replace `setup.py` and `requirements.txt` as authority with a Python 3.12
  `pyproject.toml` and `uv.lock`.
- Pin Google ADK, LiteLLM, Pydantic v2, FastAPI, HTTPX, Typer, and test tooling.
- Configure Ruff, Pyright, pytest, and pytest-asyncio.
- Preserve and run the current tests inside `.venv`.
- Add `kov doctor` for Python, Ollama, model tag, context, Flash Attention,
  q8 KV cache, Git, Node, GPU, repositories, ports, and disk checks.
- Capture the current dirty diff as an explicit migration input.

Exit criteria:

- One documented `uv sync --extra test` setup path.
- Existing tests pass or every inherited failure has a recorded baseline issue.
- No user change is overwritten.

### Phase 1 - Typed kernel and executable policies

Deliverables:

- Pydantic v2 contracts for IDs, events, decisions, actions, observations,
  artifacts, state transitions, policy verdicts, and failures.
- Discriminated action union with no generic `dict[str, Any]` execution path.
- Bounded transparency envelope: decision summary, evidence references, expected
  outcome, uncertainty, alternatives, and requested action.
- Versioned policy registry with immutable, protected, adaptive, and
  informational classes.
- Explicit lifecycle transition table and fail-closed authorization.
- Pause, Emergency Stop, degraded mode, idempotency, and no-progress primitives.

Initial lifecycle states:

```text
IDLE -> COLLECTING -> TRIAGING -> RESEARCHING -> HYPOTHESIZING
     -> BASELINING -> IMPLEMENTING -> VALIDATING_SYNTAX -> TESTING
     -> REVIEWING -> PUBLISHING -> WAITING_CI -> DEPLOYING -> CANARY
     -> MONITORING -> COMPLETED
```

Every state also has typed `DEFERRED`, `REJECTED`, `FAILED`, `PAUSED`, and
`ROLLING_BACK` transitions where applicable.

Exit criteria:

- Property tests prove illegal transitions and unknown action fields fail.
- Each initial policy has an owner, enforcement test, and dashboard status.
- Restarting the controller rehydrates state without duplicating an action.

### Phase 2 - Append-only evidence and local learning substrate

Deliverables:

- SQLite WAL schema and migrations for events, decisions, policies, episodes,
  lessons, projections, deployments, and model runs.
- Append-only sequencing and triggers preventing event update or deletion.
- SHA-256 content-addressed artifact store with privacy class and retention class.
- Atomic backups, integrity checks, and restore tests.
- FTS5 indexing and deterministic metadata filtering.
- Retention enforcement: raw analysis evidence 30 days, routine logs 14 days,
  security/error evidence 30 days after resolution, redacted aggregates 12
  months, and durable promotion/rollback evidence for project lifetime.

Exit criteria:

- Crash-recovery and concurrent-reader tests pass.
- Corruption, missing artifacts, and sequence gaps produce degraded mode.
- The 10 GiB telemetry cap is enforced without deleting protected evidence.

### Phase 3 - Atomic SWE-agent computer interface

Deliverables:

- Workspace registry covering KOV, Research Tutor, and read-only discovered
  development workspaces with canonical path and deny-zone enforcement.
- `repo_snapshot` with bounded tree and trusted manifest entry points.
- `view_file` with numbered windows of at most 100 lines and file digest.
- `search_code` backed by `rg`, capped, ranked, paginated, and artifact-linked.
- `edit_lines` using exact inclusive line ranges, expected digest, atomic replace,
  and compact changed hunk.
- `create_file`, `move_path`, and `delete_path` with explicit preconditions in a
  disposable candidate worktree.
- `run_check` using named manifest-derived profiles, fixed argv, `shell=False`,
  minimal environment, process-group termination, and resource limits.
- `view_artifact` and `submit_candidate`.

Exit criteria:

- Symlink, traversal, race, stale-digest, oversized-view, command-injection, and
  timeout tests pass.
- The model cannot request arbitrary Bash or package installation.
- Existing string replacement and `run_shell` are absent from the autonomous
  path before that path can mutate a real repository.

### Phase 4 - Bounded observation and CPRS layer

Deliverables:

- Streaming stdout/stderr capture directly into artifact files.
- ANSI stripping, secret and personal-data redaction, encoding normalization,
  metadata, hashes, and truncation markers.
- Tool-specific reducers for tests, compilers, search, file views, diffs, build
  output, and generic commands.
- Conservative token estimator that invokes reduction before a result can exceed
  the 1,500-token model-observation target.
- Exact preservation of diagnostics, failing assertions, traceback frames,
  signatures, changed hunks, exit status, and hidden-line counts.
- Structured rolling checkpoints for context eviction.

Exit criteria:

- Golden tests cover large pytest traces, compiler failures, warnings, diffs,
  binary output, secrets, and personal data.
- Reducers are deterministic and never use an LLM.
- Raw evidence remains locally recoverable by artifact ID but never enters model
  history or outbound GitHub content.

### Phase 5 - Google ADK and Qwen inference boundary

Deliverables:

- Thin ADK adapter for fresh role invocations against local Ollama.
- Fixed POC model contract for `qwen3.5-kilo:9b`, 32K context, Flash Attention,
  q8 KV cache, and full GPU residency checks.
- Generated JSON Schema from the Pydantic action union.
- Two-attempt schema-repair path using exact validation diagnostics.
- Role-specific context builder for discovery, planning, coding, review,
  learning, and self-improvement.
- Metrics for prompt evaluation, decoding, TTFT, load time, context usage, stop
  reason, schema failures, retries, and Ollama/GPU state.
- Explicitly disabled ADK content capture and external telemetry exporters.

Exit criteria:

- Real local structured-output calls validate through Pydantic.
- Invalid output never executes and repair behavior is reproducible.
- No ADK, LiteLLM, or OpenTelemetry network export occurs.
- The full decision specification is never inserted into one prompt.

### Phase 6 - Deterministic coding state machine

Deliverables:

- One-action-at-a-time controller loop over isolated Git worktrees.
- Baseline, hypothesis, acceptance criterion, and champion digest requirements.
- Python AST/`py_compile` and TypeScript compilation before broader tests.
- Syntax failure routes directly to a bounded repair observation.
- Project-derived test/build profiles for Research Tutor.
- One active candidate globally, interactive GPU preemption, AC/thermal policy,
  and unrestricted productive GPU use without aggregate quotas.
- Multi-objective promotion evidence with immutable hard gates.

Exit criteria:

- A fixture repository completes view, edit, syntax, test, and success paths.
- Syntax errors cannot consume a test run.
- Repeated idempotency keys cannot duplicate edits or external state.
- A no-progress loop terminates without limiting materially new repair work.

### Phase 7 - Opportunity discovery and research

Deliverables:

- Sanitized collectors for Research Tutor errors, performance, resource data,
  conversation-derived aggregates, tool traces, Git history, dependency notices,
  and evaluation outcomes.
- Work-conserving deterministic collection, immediate triage, continuous
  evidence-triggered synthesis and exploratory research, plus bounded
  exponential backoff only after infrastructure failure.
- Opportunity queue enforcing the rolling 80/20 evidence/exploration mix.
- Tiered web evidence, source provenance, bounded downloads, prompt-injection
  treatment, and private outbound-query construction.
- Typed opportunity decisions, including no-op, duplicate, deferred, and
  insufficient-evidence outcomes.

Exit criteria:

- Synthetic evidence produces ranked opportunities without repository mutation.
- Research never sends conversations, traces, repository code, or credentials.
- A quiet controller is distinguishable from a stalled controller.

### Phase 8 - Continual learning, test evolution, and compaction

Deliverables:

- Deterministic episode builder and failure taxonomy.
- Failure fingerprints and changed-champion retry suppression.
- Evidence-backed lesson synthesis with provenance validation.
- Versioned operating summaries, contradiction preservation, supersession, FTS
  retrieval, and bounded role-specific learning packets.
- Historical outcome statistics for strategies, sources, components, and tools.
- Separate test-only candidate lane that promotes meaningful tests into protected
  benchmark history before a later production candidate can satisfy them.

Exit criteria:

- Lessons cannot cite missing evidence or mutate prior ledger events.
- Historical replay shows that retrieval supplies relevant prior failures.
- Repeated compaction does not convert unsupported inference into fact.
- Test candidates cannot approve simultaneous production changes.

### Phase 9 - Operator dashboard and chat

Deliverables:

- Authenticated localhost-only FastAPI service and React dashboard.
- Overview, causal timeline, candidate, evidence, policy coverage, resource,
  archive, deployment, rollback, and learning views.
- Granular LLM metrics and measured/estimated/unavailable labels.
- First-class positive and negative decision records with evidence links,
  alternatives, policy authority, predictions, and actual outcomes.
- Intentional light/dark themes, responsive layout, keyboard navigation,
  accessible charts, reduced motion, and progressive disclosure.
- No raw token stream; only sanitized typed activity and summaries.
- General chat for explanation, evidence search, and authenticated typed control
  requests without bypassing the state machine.

Exit criteria:

- UI state derives exclusively from typed ledger projections.
- Accessibility and redaction tests pass.
- Pause and Emergency Stop remain usable through CLI/sentinel if the UI fails.
- The primary dashboard remains readable under a dense synthetic event load.

### Phase 10 - GitHub App, CI, deployment, and rollback

Deliverables:

- Dedicated KOV GitHub App under `kov37` with short-lived installation tokens.
- Protected publisher for idempotent branch push, draft PR, PR update, merge
  request, CI observation, and evidence manifest.
- Branch protection checks specified in the decision record.
- Alternate-port Research Tutor deployment, pre-switch validation, atomic switch,
  60-second live canary, continued monitoring, and automatic rollback.
- Five immediately restorable known-good releases.
- Reversible migration workflow and isolated dependency-upgrade workflow.

Exit criteria:

- Qwen and candidate processes cannot read GitHub credentials.
- Replayed publication requests do not create duplicate PRs.
- Failed CI, missing evidence, migration rehearsal failure, or canary regression
  prevents or reverses promotion.
- The commissioning run opens a real sanitized draft PR and cannot merge.

### Phase 11 - Service hardening and capability broker

Deliverables:

- Hardened lingering `systemd` user service with bounded restart backoff.
- Authenticated local Pause, Emergency Stop, resume, status, and doctor commands.
- Root-owned typed capability broker only for approved KOV, Research Tutor,
  Ollama, backup, and guarded release operations.
- Explicit absence of arbitrary sudo, APT/DPKG, power-state, kernel, driver, CUDA
  host stack, firmware, bootloader, disk, encryption, and recovery operations.
- Guarded Ollama configuration/restart with live generation proof and restoration.
- Desktop notifications for the agreed high-value lifecycle events.

Exit criteria:

- Candidate code cannot invoke or widen broker capabilities.
- Emergency Stop terminates the process tree and prevents restart while Research
  Tutor stays available.
- Broker integration tests verify exact targets, idempotency, audit, postconditions,
  denial behavior, and rollback.

### Phase 12 - Recursive self-improvement

Deliverables:

- Separate KOV self-candidate lifecycle and typed self-change dossier.
- Immutable historical, adversarial, schema, privacy, tool, liveness, performance,
  and rollback replay suite outside candidate write authority.
- Successor build, independent clean-process evaluation, clean restart activation,
  heightened monitoring, and prior-champion rollback.
- Self-updating adaptive playbooks and evidence-triggered model-promotion lane.
- Champion, previous champion, and one challenger model retention.

Exit criteria:

- The running KOV version never edits itself in place.
- A self-candidate cannot modify the checks judging that candidate.
- A deliberately defective successor is rejected or rolled back in simulation.
- Every self-change links initiating lessons, prediction, measured outcome, and
  future retrieval evidence.

## 6. Initial implementation sequence

The first working vertical slice should be built in this order:

1. Environment and baseline tests.
2. Typed contracts, event ledger, and policy registry.
3. Atomic file/search/edit/check tools and observation reduction.
4. Google ADK structured-output adapter.
5. Deterministic state machine over a disposable fixture repository.
6. Research Tutor syntax/test profiles and isolated worktree validation.
7. Minimal dashboard with lifecycle, decisions, gates, resources, and kill switch.
8. One manually seeded local candidate with no GitHub publication.
9. One autonomously discovered local candidate with no publication.
10. GitHub App commissioning run that opens the first real draft PR.

Automatic merge, deployment, continual research, learning, and recursive
self-improvement are enabled only after the preceding layer has executable policy
coverage and passing protected tests. This is staged activation, not human review
of each candidate.

## 7. Test strategy

### Unit and property tests

- Pydantic strictness, bounds, and discriminated unions.
- State transitions and policy authorization.
- Canonical path, deny-zone, symlink, digest, and atomic-write behavior.
- Output reducers, redaction, retention, compaction, and failure fingerprints.
- Command-profile expansion and shell-token rejection.

### Integration tests

- SQLite crash recovery and artifact integrity.
- Real Git worktrees and idempotent mutations.
- Timed process-group termination and output caps.
- Mock ADK/Ollama schema repair and real local smoke tests.
- Dashboard API projections and authentication.
- GitHub and deployment adapters against fakes before live commissioning.

### Replay and adversarial tests

- Historical accepted, rejected, failed, and rolled-back candidate episodes.
- Reward-hacking attempts: skipped tests, weakened assertions, hidden errors,
  fabricated evidence, reduced work, and metric manipulation.
- Prompt injection in source files, logs, web pages, issues, and tool output.
- Privacy attacks, credential paths, symlink escape, command injection, and
  candidate attempts to modify its evaluator or publisher.

### Real-machine proofs

- `ollama ps` confirms 32K allocation and full GPU residency.
- NVIDIA metrics confirm lease, thermal, and preemption behavior.
- A real structured Qwen action passes ADK and Pydantic validation.
- A real Research Tutor alternate-port deployment passes and rolls back.
- The GitHub commissioning run creates exactly one sanitized draft PR.

## 8. Commissioning definition of done

The proof of concept is commissioned when:

- KOV starts at boot and its dashboard accurately reports health and policy
  coverage.
- It discovers a bounded Research Tutor opportunity from sanitized evidence.
- It records the hypothesis, alternatives, evidence, acceptance criterion, and
  expected outcome.
- It creates an isolated candidate using only atomic tools.
- Syntax, protected tests, privacy, security, change-scope, and review-finding
  checks pass from real artifacts.
- It explains every lifecycle transition and resource measurement in the UI.
- It opens one real draft PR through the KOV GitHub App with no raw private data.
- The commissioning policy prevents that first PR from merging.
- Pause, Emergency Stop, restart recovery, and rollback simulation all pass.

After commissioning, automatic merge and guarded deployment can be enabled by a
versioned policy activation. The first recursive KOV successor remains a later
milestone and cannot be conflated with the Research Tutor commissioning PR.

## 9. Remaining implementation-time calibration

The architecture is sufficiently specified to begin. These values should be
measured during implementation rather than guessed in advance:

- Exact command-profile timeouts and output-byte caps per Research Tutor task.
- Noise bands and soft regression ceilings for latency, VRAM, and UI metrics.
- SQLite checkpoint and backup intervals under observed event volume.
- CPRS estimator margins for Qwen tokenization.
- Active and idle hardware metric sampling frequencies.
- Exact dashboard design tokens and chart density.
- Model challenger comparison margins after a historical evaluation corpus exists.

None of these calibration items changes the protected authority boundaries or
blocks Phase 0 through Phase 3.
