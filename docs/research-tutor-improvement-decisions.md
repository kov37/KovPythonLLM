# KOV Continuous Research Tutor Improvement Decisions

Status: planning record

Last updated: 2026-08-04

## Product boundary

- KOV is initially a proof of concept and will be built and validated in small,
  reversible iterations rather than as a complete autonomous platform at once.
- KOV remains a general chat, web, and file assistant, but its primary role is
  autonomous repository engineering.
- General chat may explain current activity, search sanitized evidence, answer
  questions, and formulate typed action requests, but chat text is untrusted
  input rather than policy or execution authority. It cannot bypass the state
  machine, tool schemas, or protected gates.
- Natural-language requests for Pause, resume, rollback, publish, deploy, or
  other privileged controls are converted into explicit typed control requests
  and require the same fresh local authorization as their dashboard equivalents.

## Filesystem scope

- KOV is not confined to only the KOV and Research Tutor repository paths. It may
  discover and work with user-owned development repositories, source trees,
  notebooks, test fixtures, and application data under `/home/digichameleon`
  when they are relevant to an authorized interactive or autonomous objective.
- Workspace discovery uses deterministic project markers and canonical paths;
  access remains auditable and path-contained rather than becoming an arbitrary
  shell view of the entire home directory.
- Permanent deny zones include SSH and GPG material, desktop keyrings, browser
  profiles, authentication and cloud credential stores, unrelated mail and
  personal-document collections, protected `.env` and secret files, and system
  paths outside explicitly brokered service operations.
- The path policy records every granted workspace, access mode, purpose, actor,
  and causal task. Symlink and mount resolution cannot be used to escape a deny
  zone, and autonomous jobs do not inherit temporary interactive access merely
  because it existed in another session.
- Autonomous write authority remains limited to the KOV and Research Tutor
  repositories and their managed runtime, candidate, deployment, learning, and
  backup areas. Other discovered development projects are read-only context and
  cannot be edited, committed, published, deployed, or used as an implicit
  additional improvement target.
- KOV's long-term goal includes autonomous recursive improvement of its own
  implementation. Self-changes use a distinct meta-improvement lane: KOV fully
  documents the trigger, evidence, hypothesis, expected benefit, alternatives,
  implementation, evaluation, uncertainty, and rollback plan before an isolated
  successor version can be activated.
- KOV never edits the running controller in place. A self-candidate is built and
  evaluated as a separate version, replayed against historical work, activated
  only through a clean restart, and retained alongside the prior champion for
  immediate rollback.
- The continuously improved target is the Local Research Tutor repository at
  `/home/digichameleon/adk/research-agent`.
- KOV and Research Tutor remain separate repositories under the existing
  `kov37` GitHub account. The framework repository is
  `github.com/kov37/KovPythonLLM`; autonomous product-change branches and pull
  requests target `github.com/kov37/local-research-tutor`.
- GitHub automation uses a dedicated KOV GitHub App installed by the existing
  `kov37` account rather than a personal access token. GitHub actions are
  attributed to the app's bot identity, clearly separating autonomous actions
  from the operator's personal activity.
- The improvement controller runs continuously while the machine is powered on.
  Lightweight discovery and scheduling may remain active while expensive model
  and evaluation jobs must be bounded by explicit resource policies.
- Exactly one candidate experiment may be active at a time. KOV does not run a
  parallel evolutionary candidate pool in the proof of concept.
- Continuous operation keeps sanitized collection, research, and opportunity
  evaluation alive. It does not require continuous mutation. A candidate starts
  only when evidence crosses a deterministic category-specific threshold, no
  other KOV PR is open, and protected resources are available. Qwen still
  operates through bounded typed invocations rather than an uninterruptible
  generation stream.
- The proof of concept completes its first vertical slice by opening a real
  GitHub draft pull request after local validation and observer approval. Draft
  status does not authorize merge or deployment during that first slice. This
  is a one-time commissioning run used to validate publication redaction,
  evidence completeness, lifecycle state, and rollback metadata; it does not
  require the operator to review or approve the candidate code.
- After the commissioning run validates the protected pipeline, later pull
  requests may merge automatically when every deterministic gate passes, review
  findings are resolved or cleared, GitHub branch protection succeeds, and the
  candidate remains within promotion policy.

## Local-model execution constraints

- KOV uses the installed `qwen3.5-kilo:9b` alias, which shares the
  `qwen3.5:9b` weight blob and pins `num_ctx=32768`.
- During the proof of concept, KOV may autonomously research and run bounded,
  matched evaluations of alternative local models, quantizations, and inference
  configurations, but `qwen3.5-kilo:9b` remains the protected production
  workhorse. Discovery of a promising model does not authorize changing the
  active controller model.
- Model replacement will use a later protected promotion lane that validates
  typed-action reliability, tool-use correctness, coding outcomes, review
  quality, latency, context behavior, VRAM residency, and rollback against the
  accumulated KOV evaluation history. The candidate model cannot define or
  modify that evaluation.
- The model-promotion lane has no arbitrary minimum number of completed KOV
  cycles. KOV may initiate due diligence whenever its research identifies a
  credible challenger that could be materially better for this machine and
  workload.
- Due diligence requires verified model provenance and licensing, Ollama and
  Google ADK compatibility, structured-output reliability, matched historical
  candidate replays, tool-selection and editing correctness, clean-context
  review quality, repeated warm latency and throughput measurements, 32K context
  behavior, full-GPU residency without CPU offload, VRAM and thermal headroom,
  and a successful rollback rehearsal.
- KOV records why the challenger is expected to be better, competing models it
  considered, complete matched measurements, uncertainty, and machine-fit
  evidence. The protected controller independently verifies those artifacts and
  applies the multi-objective promotion policy; a model opinion alone cannot
  replace the active workhorse.
- A promoted model runs as a reversible champion change. The prior Qwen model
  and configuration remain immediately available until post-promotion
  monitoring demonstrates stable controller behavior.
- Local model storage retains the active champion, the immediately previous
  champion, and at most one current challenger. After due diligence completes,
  rejected challenger weights may be removed while their provenance,
  configuration, benchmark evidence, decision record, and failure lessons remain
  durable. A newly selected challenger replaces the prior rejected challenger,
  not either rollback-capable champion.
- Ollama must run with `OLLAMA_FLASH_ATTENTION=1` and
  `OLLAMA_KV_CACHE_TYPE=q8_0`. Startup verification checks both service settings
  and a live `ollama ps` allocation before autonomous work begins.
- The 32K allocation is capacity, not a target to fill. Normal prompts remain
  deliberately below the ceiling and reserve space for structured output and
  recovery observations so speed and responsiveness remain primary goals.
- Research Tutor retains its separate hard 16,384-token contract. KOV's 32K
  allocation may not silently raise the tutor's context or run concurrently with
  an interactive tutor generation.
- Only one Qwen invocation or GPU-heavy evaluation job runs at a time.
- New Qwen generations and GPU-heavy evaluations run only while the machine is
  connected to AC power. Lightweight collection, scheduling, redaction, and the
  local dashboard may continue on battery.
- The protected scheduler blocks new GPU work at the configured thermal limit
  and checkpoints or cancels resumable background work when sustained
  temperature, power, or throttling signals exceed policy. It resumes only
  after a lower hysteresis threshold is sustained, preventing rapid pause/resume
  cycling. All such events are visible in the resource timeline.
- For the current RTX 4070 Laptop GPU, KOV stops starting background GPU work at
  80 degrees Celsius, checkpoints or cancels active resumable background work at
  84 degrees, and resumes only after the GPU remains at or below 72 degrees for
  60 seconds. An atomic filesystem transaction finishes before yielding. These
  controller thresholds intentionally remain below the GPU's reported 87-degree
  target temperature and do not rely on invalid hard-limit fields exposed by the
  current laptop driver.
- Deterministic collectors, redactors, deduplicators, metric aggregation,
  scheduling, Git operations, and policy gates run without an LLM.
- Raw telemetry is reduced locally into bounded evidence packets before a model
  invocation. The model never receives an unbounded log, trace, repository, or
  conversation archive.
- Each role uses a fresh minimal session and explicit input/output schemas. State
  persists in the run ledger and artifact store rather than chat history.
- KOV has no aggregate GPU-time, daily-token, model-invocation, or candidate
  wall-clock budget. When the protected GPU lease is available, it may continue
  productive work without an arbitrary compute quota.
- Individual model responses, commands, tool observations, and filesystem
  transactions remain bounded so one hung operation cannot monopolize the
  machine or exhaust memory. A deterministic progress watchdog interrupts
  identical retries and cycles with no new evidence; this is a liveness control,
  not a limit on materially progressing work.
- Interactive Research Tutor requests always take priority over KOV background
  model work. The supervisor pauses or cancels a resumable background Qwen job
  before granting the GPU lease to an interactive request; lightweight evidence
  collection may continue without using the model.
- Allocation and prompt-policy claims require live verification. On 2026-08-04,
  a direct KOV-alias request loaded with context 32,768 at 100% GPU; `ollama ps`
  reported a 6.2 GB runner and NVIDIA reported 7,092 MiB process memory.

## Interpretability and transparency

- Every improvement run emits an append-only structured event stream with a run
  ID, candidate ID, timestamp, actor role, action type, sanitized inputs,
  sanitized outputs, duration, resource use, and causal parent event.
- The interface must show the current lifecycle stage, active hypothesis,
  acceptance criteria, tool activity, changed files, validation results,
  observer findings, PR state, deployment state, and rollback status.
- KOV records concise decision rationales and evidence references. Hidden model
  reasoning is neither required nor treated as reliable evidence.
- Every meaningful decision renders as a first-class dashboard record answering:
  what KOV decided, why it acted now, which sanitized observations and artifacts
  support the decision, which alternatives were considered, why they were not
  selected, what uncertainty remains, which protected policy allowed the action,
  what result was expected, and which state transition followed.
- Decision records use a strict typed schema with a decision ID, causal parent,
  actor and role, timestamp, concise rationale, evidence references, alternative
  summaries, policy references, predicted outcome, uncertainty classification,
  and resulting action or deferral. The dashboard links each claim to its
  sanitized source artifact and later compares the prediction with the measured
  outcome.
- The same schema records negative decisions. Deferred, rejected, duplicate,
  superseded, insufficient-evidence, policy-blocked, and no-op opportunities
  remain visible with the exact reason, missing evidence, reconsideration
  condition, and next eligible review time. A quiet controller must be
  explainable rather than indistinguishable from a stalled one.
- The model supplies a concise decision summary rather than hidden
  chain-of-thought. The controller separately records its deterministic policy
  evaluation, so the UI clearly distinguishes a model's stated rationale from
  the actual rule that authorized or rejected the action.
- Every promotion decision must be reconstructable from durable artifacts:
  baseline, candidate diff, commands, exit codes, benchmark measurements,
  hard-gate results, observer verdict, CI result, and post-deployment checks.
- Raw private conversations and traces remain behind the local privacy boundary;
  the observer dashboard presents redacted summaries and aggregate evidence.
- The event schema and audit store belong to the protected control plane and
  cannot be rewritten or selectively erased by the candidate agent.
- The proof-of-concept interface should favor a simple local run ledger and
  lifecycle view before adding complex distributed tracing infrastructure.
- The KOV operator UI is a first-class product surface, distinct from Research
  Tutor's user interface, and must express current and historical activity in
  precise, polished detail rather than exposing a scrolling terminal dump.
- Its overview shows controller health, kill-switch state, GPU lease, active and
  queued work, current champion, candidate branch, lifecycle stage, elapsed time,
  resource budgets, and the next permitted transition.
- A causal timeline groups opportunity evidence, model actions, tool calls,
  observations, file changes, gates, observer review, publication, CI, and
  deployment events. Every item exposes timestamps, duration, status, parent
  event, sanitized structured payload, and artifact links.
- The candidate view shows the hypothesis and acceptance criteria beside a file
  list and line-level diff, plus syntax, tests, benchmarks, privacy, security,
  change-budget, observer, and CI gates with their exact evidence.
- The evidence view distinguishes raw-local, redacted, compressed, and externally
  publishable representations and makes every hidden-line count or truncation
  explicit. Only the human operator may expand sanitized raw artifacts.
- The resource view charts model load and generation time, prompt and output
  tokens, context use, GPU memory, command duration, retries, and cumulative
  candidate cost. Interactive-preemption events are visible.
- The first dashboard includes a granular LLM runtime-state panel. It reports
  the configured and currently loaded model tag and digest, quantization,
  allocated context, GPU/CPU residency, GPU lease holder, queue depth, active
  role, invocation phase, request and run identifiers, and whether generation
  is loading, prompting, decoding, waiting on a tool, preempted, or idle.
- Per invocation it records prompt-evaluation tokens and duration, generated
  tokens and duration, prompt-processing rate, decode rate, time to first token,
  total and load duration, context utilization, stop reason, retry count,
  structured-output validation failures, and rolling latency percentiles.
- Hardware sampling records VRAM used and available, GPU utilization,
  temperature, power, clocks, and process residency when exposed by the local
  NVIDIA and Ollama interfaces. Active generations use a finer sampling cadence
  than idle periods, and durable history stores downsampled aggregates rather
  than an unbounded high-frequency stream.
- The UI distinguishes measured values, controller-derived estimates, and
  unavailable signals. It does not label hidden activations, private
  chain-of-thought, confidence, or intent as observable model state.
- The dashboard never streams raw model tokens or unredacted intermediate text.
  During generation it shows live counters, runtime phase, typed action state,
  and sanitized summaries only after the privacy boundary has processed them.
- Visual quality is a first-version acceptance criterion. The dashboard uses a
  coherent design system with deliberate typography, spacing, color semantics,
  iconography, elevation, chart styling, and responsive composition. It should
  feel like a calm precision observatory, not a terminal wrapped in cards.
- Dense operational detail uses progressive disclosure: the primary surface
  remains legible and flowing, while exact metrics, evidence, and event payloads
  are available through stable drill-down panels. Motion communicates state
  transitions and causality but remains restrained and respects reduced-motion
  preferences.
- The dashboard ships with intentionally designed light and dark themes. It
  follows the operating-system preference initially and provides a persistent
  manual override; neither theme is treated as a mechanical inversion of the
  other.
- The archive supports comparison with the champion and earlier rejected runs,
  including why a candidate stopped, failed, was superseded, or rolled back.
- UI state is rendered from the append-only event ledger and typed projections;
  it does not infer success or activity from model prose.
- Accessibility, keyboard operation, responsive layout, reduced-motion support,
  and an explicit redaction indicator are acceptance criteria for the KOV UI.
- KOV sends desktop notifications only when the first draft PR is created, a PR
  is automatically merged and deployed, an automatic rollback occurs, Emergency
  Stop activates, the controller reaches an unrecoverable failure, a serious
  privacy or security finding is detected, or a candidate remains stuck after
  materially different repair strategies.
- Routine research, tests, rejected hypotheses, successful background checks,
  and ordinary lifecycle transitions remain visible in the dashboard and ledger
  without generating interruptive notifications.

## Protected control plane

- The supervisor, kill switch, evaluator definitions, protected benchmarks,
  promotion policy, privacy controls, and rollback mechanism are immutable from
  KOV's tool surface.
- The external kill switch must stop the full improvement process tree, block
  new promotions, and permit restoration of the last known-good release.
- The operator has two separate controls. Pause allows the current atomic action
  to finish or reach a safe checkpoint, then blocks new research, candidates,
  merges, and deployments. Emergency Stop immediately terminates the KOV
  process group, revokes its GPU lease, cancels candidate commands, disables the
  publisher, and inhibits automatic restart.
- Pause and Emergency Stop affect KOV, not the live Research Tutor service.
  Resumption requires an explicit local operator action and presents the
  interrupted run, last durable event, worktree state, and next permissible
  transition before execution continues.
- Dashboard controls are backed by a local CLI and protected filesystem sentinel
  so loss or corruption of the UI cannot remove operator control.
- KOV runs as a hardened `systemd` user service with lingering enabled so the
  controller starts at boot without requiring an interactive login. Unexpected
  controller crashes use bounded restart backoff; an Emergency Stop sentinel
  suppresses automatic restart until explicit local clearance.
- The service uses a dedicated runtime directory, a minimal explicit
  environment, and a dashboard bound to localhost. Research Tutor remains a
  separate service so pausing, restarting, or stopping KOV does not interrupt
  normal tutor use.
- The dashboard binds only to `127.0.0.1` and never opens a LAN or public
  listener automatically. A local launcher supplies a private service-generated
  session credential; the web application uses secure session cookies and CSRF
  protection.
- Pause, Emergency Stop, resume, rollback, and credential-management actions
  require a fresh local authorization check and are recorded in the protected
  audit ledger without storing the credential itself.
- A candidate cannot change the checks used to judge or promote that candidate.

## Unattended elevated capabilities

- KOV is designed to operate without routine human approval and receives the
  capabilities needed to maintain its own service, Research Tutor, isolated
  environments, repositories, local model runtime, guarded deployment, and
  recovery. Unattended authority does not mean that Qwen or candidate code
  receives an unrestricted root shell.
- Qwen proposes typed actions; ordinary candidate commands run as a dedicated
  unprivileged identity. Administrative operations cross a separate root-owned
  capability broker over a protected local interface.
- The broker accepts only discriminated, schema-validated operations with exact
  targets, policy IDs, preconditions, idempotency keys, timeouts, audit events,
  postcondition checks, and rollback information. It never accepts a shell
  string, arbitrary executable, unresolved path, or model-supplied privilege
  policy.
- Pre-authorized capabilities may manage only named KOV and Research Tutor user
  services, approved runtime and repository paths, isolated Python and frontend
  environments, Ollama model lifecycle, guarded release switching, backups, and
  verified restoration. More invasive host changes require a distinct protected
  capability and stronger rehearsal; they are not obtained by falling back to
  general `sudo`.
- KOV is never granted authority to install, remove, upgrade, or reconfigure the
  operating-system kernel, NVIDIA host driver, system CUDA stack, firmware,
  bootloader, recovery partition, disk layout, encryption, or other host-critical
  components. It may research and report relevant updates, but cannot stage,
  activate, or reboot into them.
- Reboot, shutdown, suspend, hibernate, logout, and firmware-reboot operations
  are operator-only capabilities and are absent from KOV's broker interface.
  KOV may checkpoint its own work in response to an externally observed power
  transition but cannot initiate that transition.
- KOV has no system-wide APT, DPKG, package-repository, or host package-removal
  authority. Python and frontend dependencies are installed only inside isolated
  project environments through the protected dependency workflow. A missing
  host package is reported as a blocked capability rather than installed by KOV.
- The capability broker, its authorization policy, Emergency Stop integration,
  credential boundary, and audit sink belong to the immutable root of trust.
  KOV can research and propose broker improvements, but the active candidate
  cannot grant itself a new privilege or alter the evidence used to authorize
  its own operation.
- Every elevated action and denial is visible in the dashboard with its reason,
  authorizing policy, exact target, before-and-after state, and recovery status.
- KOV may automatically restart and reconfigure the Ollama service when no
  interactive Research Tutor request holds or is waiting for the GPU lease. The
  controller captures the prior service and model configuration, validates the
  proposed configuration, drains or checkpoints background work, applies the
  exact typed change, and performs health, model-residency, structured-output,
  and real generation checks.
- Failed Ollama startup, residency, context, performance, or generation checks
  restore the previous configuration and service state. Restart, verification,
  interruption, and restoration events appear in the dashboard.

## Executable policy registry

- Every architectural and operational requirement has a machine-readable policy
  record with a stable policy ID and schema version, normative requirement,
  enforcement mechanism, owning controller component, applicable lifecycle
  states, linked verification tests, last verification result, mutability class,
  failure behavior, and dashboard presentation metadata.
- Policies are classified as immutable-root, protected-controller,
  self-updatable-adaptive, or informational. KOV may propose and evaluate changes
  only through the lane permitted by the policy's class; a candidate cannot
  relabel a protected policy to gain write authority.
- Startup validates the policy graph, required component registrations, schema
  compatibility, enforcement-test presence, and conflicting requirements. A
  missing or unverifiable required policy fails closed.
- The dashboard exposes a live policy coverage matrix distinguishing documented,
  implemented, enabled, tested, passing, degraded, and unverified requirements,
  including the last successful proof artifact. This makes specification drift
  and incomplete implementation visible.
- If a required policy is documented but missing, disabled, incompatible, or
  failing verification, KOV enters degraded mode. Dashboard operation,
  sanitized evidence collection, research, and non-mutating planning may
  continue, while code mutation, self-update activation, publication, merge,
  deployment, and policy-sensitive external actions fail closed.
- Degraded mode identifies the exact policy, missing enforcement, affected
  capabilities, and restoration test. KOV may prepare an isolated repair
  candidate, but normal autonomy resumes only after the protected verifier proves
  that enforcement is restored.

## Non-negotiable deterministic scaffolding

- Deterministic scaffolding is a mandatory architectural invariant, not an
  optional reliability enhancement.
- Qwen proposes one typed action at a time. The protected controller validates,
  authorizes, executes, records, and returns the observation.
- The model cannot choose or skip state-machine transitions, declare a gate
  passed, mark a task complete, publish content, merge code, deploy, or alter
  retry and resource limits.
- Every tool has a strict Pydantic argument model with forbidden extra fields,
  bounded strings and integers, canonical workspace-local paths, and explicit
  error results. Invalid or ambiguous output fails closed and is never repaired
  by guessing the model's intent.
- File inspection uses numbered windows of at most 100 lines. File changes use
  exact line ranges plus an expected file digest, are written atomically, and
  fail if the file changed after inspection.
- Commands run with an explicit working directory, timeout, process-group
  cancellation, output-byte cap, environment allowlist, and command policy.
- KOV has no general-purpose Bash terminal. The model requests a named command
  profile with typed arguments; the executor expands it into a fixed argv and
  always runs with `shell=False`.
- Each action and state transition has a run ID, sequence number, idempotency
  key, causal parent, timestamps, and sanitized result in the append-only ledger.
- Deterministic syntax or type checks run before tests. Python changes use AST or
  `py_compile`; frontend changes use TypeScript compilation. A syntax failure
  blocks later gates and returns a compact compiler observation to Qwen.
- Test, benchmark, privacy, observer, CI, deployment, and rollback outcomes are
  read from real exit codes and artifacts, never from model narration.
- Repeated actions, stale edits, limit exhaustion, malformed schemas, missing
  evidence, and uncertain privacy classification stop or defer the run.
- Replaying a completed action with the same idempotency key must not duplicate
  file changes, commits, pull requests, deployments, or external messages.

## Google ADK boundary

- The deterministic KOV controller is the sole owner of lifecycle state,
  orchestration, scheduling, authorization, tools, memory, retries, evaluation,
  promotion, publication, deployment, and rollback.
- Google ADK sits behind a thin inference adapter and performs one bounded Qwen
  role invocation at a time. It does not run an independent autonomous loop or
  persist an authoritative conversational session.
- Discovery, planning, implementation, review, learning synthesis, and
  self-improvement roles use fresh minimal ADK sessions. Each request contains
  only the current objective, relevant bounded evidence and lessons, permitted
  action schema, and applicable policy summaries.
- ADK returns a typed proposal that must pass structured-output parsing,
  Pydantic validation, current-state authorization, and deterministic policy
  checks before the controller performs any action. Model or ADK narration has
  no execution authority.

## Typed protocol contracts

- Pydantic v2 models define every boundary between Qwen, Google ADK, tools, the
  state machine, the observer, the audit ledger, and the protected publisher.
- Model actions use a discriminated union of concrete action models. Each tool
  has its own argument type; execution code never accepts an unvalidated generic
  `dict[str, Any]` merely because a tool name is present.
- Models use strict field types, `extra="forbid"`, bounded values, enums and
  literals, schema versions, and cross-field validators. Coercion and unknown
  fields fail closed.
- Tool observations, compiler diagnostics, test failures, benchmark evidence,
  observer verdicts, state transitions, artifact references, and draft-PR
  requests are typed as rigorously as tool inputs.
- Ollama Structured Outputs receives the generated JSON Schema. Successful JSON
  parsing is followed by Pydantic validation and controller authorization;
  schema validity alone never grants permission to execute.
- The model returns a concise decision summary, not private chain-of-thought.
  Interpretability comes from typed actions, cited evidence, and recorded state
  transitions.
- Model action contracts contain no free-form `thought` field. Their
  transparency envelope uses bounded typed fields for `decision_summary`,
  `evidence_refs`, `expected_outcome`, `uncertainty`, and
  `alternatives_considered`, alongside a discriminated `requested_action`.
  These fields populate decision records but do not grant execution authority.
- Malformed model output has no execution authority. The controller returns only
  exact JSON Schema and Pydantic validation diagnostics to a fresh repair
  invocation and permits at most two structured-output repair attempts for that
  action.
- After two failed repairs, the action closes as a typed schema failure and feeds
  the continual-learning layer. The controller never guesses missing arguments,
  coerces unsafe values, parses a tool call from surrounding prose, or executes
  a partially valid object.

## Pull-request scope discipline

- One pull request makes one measurable claim and addresses one concern. Do not
  combine a feature, unrelated refactor, dependency update, and formatting pass.
- The first Research Tutor candidate may change at most three production files
  and 200 production lines, plus at most two focused test files. Generated files
  and lockfiles are measured and reported separately rather than hiding their
  size. Later budgets may be calibrated from observed success without being
  widened by the candidate model itself.
- Crossing the budget does not authorize a larger patch. KOV stops implementation
  and produces a typed decomposition proposal with risks, dependencies,
  acceptance criteria, and a sequence of independently useful PRs.
- Every step in a large-change sequence must keep the application buildable,
  pass protected gates, be independently reviewable, and have a rollback path.
- Later PRs cannot rely on an unmerged candidate, and evidence is recalculated
  against the current champion before each step begins.
- Mass formatting and incidental cleanup are prohibited unless they are the
  explicit, measured purpose of the PR.

## Bounded tool-observation pipeline

- Tool and command output is durable evidence, not conversation history. Capture
  stdout and stderr separately into protected local artifacts while streaming so
  large output is never accumulated as one unbounded in-memory string.
- Before model exposure, strip terminal control sequences, redact secrets and
  personal data, classify the result by tool type, and attach byte count, line
  count, exit code, duration, truncation state, and a content digest.
- Observations at or below the conservative 1,500-token budget may be returned
  directly. Larger observations use deterministic, tool-specific reduction.
- Test reduction preserves failing test identifiers, assertion messages,
  relevant traceback frames, captured-output tails, and the final test summary.
- Compiler reduction preserves every diagnostic's file, line, column, error code,
  and message. Warning clusters are deduplicated and counted rather than copied.
- Search results are ranked, capped, and paginated. File views remain explicit
  numbered windows of at most 100 lines. Diffs preserve changed hunks and elide
  only unchanged context with exact hidden-line markers.
- Each reduced observation includes an artifact handle. Qwen may request another
  bounded numbered slice, but cannot request an entire oversized artifact in one
  action.
- Reduction is objective-aware only after invariant evidence is retained. Exact
  errors, failing assertions, changed lines, signatures, and exit status cannot
  be discarded merely because they do not match task keywords.
- A rolling context budget evicts older observations into structured checkpoints
  containing established facts, unresolved failures, changed-file digests, and
  the next permitted state. Raw artifacts stay outside model context.
- Compression is deterministic code. A second LLM is not used to summarize tool
  output in the proof of concept.

## Bounded command execution

- Security policy must contain blast radius without preventing ordinary coding.
  The model-facing tool surface stays small and orthogonal but supports complete
  inspect, edit, create, move, delete, validate, and review workflows inside the
  disposable candidate worktree.
- Command profiles cover repository inspection, `git status` and `git diff`,
  Python syntax checks, backend tests, TypeScript compilation, and frontend
  builds. The controller also derives profiles from trusted, versioned project
  manifests such as `pyproject.toml` and `package.json`; it does not hard-code a
  separate policy for every task.
- Reject shell operators, substitutions, redirects, arbitrary interpreters,
  inline programs, package installation, privilege changes, destructive Git
  subcommands, process-control utilities, and commands not in the profile set.
- Autonomous dependency upgrades use a separate protected controller workflow;
  they do not grant the model-facing command runner general package-installation
  authority.
- Run candidate commands as a dedicated unprivileged service identity inside the
  candidate worktree with a minimal environment, no inherited secrets, no GitHub
  credentials, no privilege escalation, and no network unless a specific
  immutable profile requires it.
- Apply per-command wall-time, CPU, memory, process-count, open-file, and output-
  byte limits. Timeouts and limit violations terminate the whole process group.
  There is no cumulative command-count or GPU-use quota for a candidate that
  continues to make measurable progress.
- The protected publisher—not KOV and not the command runner—owns the GitHub token
  and performs idempotent branch pushes and draft-PR creation after every local
  gate and the observer review pass.
- The publisher obtains short-lived installation tokens for the explicitly
  installed repositories. Qwen, candidate processes, command profiles, and
  worktrees never receive the app private key or installation token, and
  revoking the app does not affect the operator's personal GitHub access.
- A missing command capability defers the candidate and records the requested
  profile. The model cannot widen its own command policy during a run.

## Minimal capable tool surface

- `repo_snapshot`: bounded tree, repository state, languages, and trusted build
  or test entry points.
- `view_file`: numbered windows of at most 100 lines with a file digest.
- `search_code`: ripgrep-backed, capped and paginated text or path search, with
  optional deterministic AST verification for supported languages.
- `edit_lines`: digest-checked exact line insertion or replacement with an atomic
  write and a compact changed-hunk result.
- `create_file`, `move_path`, and `delete_path`: workspace-contained operations
  in the disposable worktree with explicit preconditions and reversible Git
  evidence.
- `run_check`: execute an authorized manifest-derived or protected command
  profile with typed arguments and bounded observations.
- `view_artifact`: retrieve another numbered slice of a sanitized output artifact.
- `submit_candidate`: stop editing and request deterministic validation; it does
  not itself declare success, commit, publish, merge, or deploy.

GitHub publication, policy changes, credentials, service control, and promotion
remain controller capabilities rather than model-facing tools.

## Dependency upgrades

- KOV may autonomously propose dependency upgrades in response to research,
  security advisories, compatibility needs, or measured performance evidence.
  Upgrade candidates remain separate from unrelated feature work.
- The protected dependency workflow resolves packages only from configured
  official registries, verifies package identity, detects suspicious name
  substitutions, records pinned resolutions and lockfile changes, and evaluates
  upstream release notes, breaking changes, licenses, known vulnerabilities,
  transitive dependencies, and install-time behavior.
- Installation and evaluation occur in an isolated candidate environment with
  restricted credentials and network access. Promotion requires the applicable
  correctness, security, privacy, performance, and behavioral gates, while the
  previous environment remains immediately restorable.

## Candidate and promotion workflow

1. Discover an opportunity from Research Tutor conversations, feedback,
   telemetry, logs, traces, source code, tests, Git history, dependency notices,
   or public research.
2. State a bounded hypothesis and a measurable acceptance criterion.
3. Reproduce the current behavior and record a baseline.
4. Implement the candidate in an isolated Git branch and worktree.
5. Run syntax, correctness, security, privacy, regression, performance, context,
   VRAM, and UI gates as applicable.
6. Review the candidate with Qwen 3.5:9B in a fresh, minimal, read-only context.
   The reviewer receives the objective, acceptance criteria, diff, relevant code,
   test evidence, and a fixed rubric, but not the author's reasoning or verdict.
   This review is advisory rather than an independent promotion authority. Each
   finding must identify concrete evidence such as a file and line, violated
   invariant, or reproducible failure scenario.
   The deterministic controller converts review findings into protected checks
   where possible. A confirmed finding blocks or returns the candidate for
   repair; an unsupported model opinion cannot approve a failing candidate or
   permanently veto a candidate that passes the protected gates. A potentially
   severe but not-yet-verifiable finding defers promotion for bounded additional
   investigation rather than being silently ignored.
7. Open a GitHub pull request only after review findings are resolved or
   deterministically cleared and all protected local gates pass.
8. Require GitHub CI and branch-protection checks before automatic merge.
9. Record the champion revision and rollback manifest, start the merged candidate
   on an alternate local port, and run deterministic health, API, UI, privacy,
   behavioral, latency, and resource checks before switching live traffic.
10. Promote the candidate locally only after pre-switch checks pass, monitor it
    through a 60-second live canary, and automatically restore the recorded
    champion when protected crash, behavior, latency, or resource limits are
    crossed. Deterministic health, routing, and lightweight behavioral probes
    run throughout that minute; comprehensive checks have already passed on the
    alternate port before the switch.
11. After the one-minute canary clears, Research Tutor remains live without a
    longer promotion hold. Non-blocking regression monitoring continues and may
    still trigger automatic rollback when later evidence crosses a protected
    threshold.
- KOV retains the five most recent known-good deployed releases and their
  validated rollback manifests in immediately restorable local form. Older
  revisions remain recoverable from Git, while disposable build artifacts are
  removed under the artifact-cap policy.

## Persistent-data migrations

- KOV may autonomously propose and execute persistent-data or schema migrations;
  they are not excluded merely because they carry additional risk.
- Before promotion, the controller creates and verifies a recoverable backup,
  rehearses the migration against a copied dataset, validates forward and
  rollback paths, and records schema and data-integrity evidence.
- Migrations use expand-and-contract compatibility where practical so the old
  and new Research Tutor revisions can both operate during the transition.
  Obsolete data is quarantined through a retention window rather than being
  immediately destroyed.
- A failed migration restores both the application champion and its compatible
  data state. The dashboard exposes the migration plan, backup verification,
  rehearsal outcome, active schema version, compatibility window, and recovery
  status.

## GitHub branch protection

- Automatic merge requires protected checks for Python syntax and typing,
  backend and frontend tests, privacy and secret scanning, dependency and
  security scanning, change-budget enforcement, deterministic Research Tutor
  behavioral evaluation, candidate evidence-manifest validation, resolution of
  verifiable reviewer findings, and guarded-deployment preparation.
- The KOV GitHub App cannot administer the repository, alter workflows or branch
  protection, dismiss required checks, force-push protected branches, or bypass
  the required-check set. Missing, stale, skipped, neutral, or inconclusive
  required evidence fails closed.

## Proof-of-concept discovery scope

- Initial opportunity discovery uses local Research Tutor evidence and official
  dependency changelogs.
- Over completed candidate cycles, KOV allocates approximately 80 percent of
  improvement work to evidence-driven opportunities and 20 percent to
  exploratory research-derived opportunities. This ratio is measured by
  candidate cycles rather than wall-clock time or model tokens.
- The scheduler enforces the rolling allocation; an exploratory candidate may
  not displace a higher-severity correctness, privacy, security, or reliability
  opportunity.
- KOV has broad autonomy to search across official documentation, standards,
  academic papers, source repositories, reproducible benchmarks, engineering
  publications, issue trackers, forums, blogs, and other public sources so it
  can maintain a diverse opportunity portfolio rather than converging on one
  narrow design tradition.
- Research evidence is tiered. Official primary sources, standards, source code,
  and peer-reviewed work receive the highest evidentiary weight; reproducible
  engineering reports are supporting evidence; forums, blogs, social media, and
  unverified claims may generate hypotheses but cannot alone justify promotion.
- KOV may autonomously follow citations, compare competing paradigms, revisit
  previously deferred ideas when new evidence appears, and investigate several
  options during discovery. The one-active-candidate rule applies to code
  experiments, not to the breadth of the research opportunity queue.
- External pages and downloaded artifacts are untrusted, bounded by size and
  time, sanitized before model exposure, and never executed merely because a
  source recommends it. Research requests disclose no conversations, traces,
  repository code, credentials, or personal information.
- Broad research begins after the protected single-candidate pipeline, privacy
  boundary, observer review, and draft-PR path work reliably end to end.
- The deterministic evidence collector refreshes at each candidate boundary and
  whenever the work-conserving loop has no selectable opportunity. Crash,
  security, and repeated-failure signals receive immediate bounded triage.
- Qwen begins a qualified opportunity as soon as protected resources are
  available; an empty evidence-qualified queue is a healthy idle state, not a
  reason to generate a generic change.
- Exploratory research may contribute to the rolling 80/20 portfolio only after
  it yields concrete acceptance criteria and the same category-specific proof as
  evidence-originated work. Interactive Research Tutor use preempts it.
- The first candidate should be bounded, reversible, and testable, but KOV is
  not categorically prohibited from considering dependencies, data models,
  authentication, security policy, or backend behavior merely because it is the
  first run. Risk determines the required evidence and decomposition; it does
  not remove an entire problem class from autonomous discovery.

## Learning from failures

- KOV learns across runs through protected external memory rather than claiming
  that the fixed Qwen model weights update themselves. Logs and traces provide
  evidence; deterministic extraction turns that evidence into reusable records.
- Every failed, rejected, reverted, or abandoned candidate produces a typed
  learning record containing the sanitized triggering evidence, hypothesis,
  attempted strategy, changed components, executed checks, exact failure class,
  causal evidence, resource cost, disposition, and conditions under which the
  idea might be worth revisiting.
- Failure fingerprints prevent identical retries against an unchanged champion.
  Before proposing or implementing a candidate, retrieval supplies the model
  with relevant prior failures, successful patterns, repository invariants, and
  unresolved risks in a bounded evidence packet.
- KOV maintains outcome statistics for strategy classes, tools, affected
  components, research sources, and repair patterns. These statistics influence
  opportunity ranking and planning but cannot weaken protected gates.
- A failed experiment is not automatically labeled a bad idea. KOV distinguishes
  invalid hypotheses, implementation errors, inadequate tests, environmental
  failures, budget exhaustion, noisy measurements, and changes that require
  decomposition, then selects a different next action accordingly.
- Post-merge traces and rollback events are linked back to the promoting
  candidate so delayed regressions update its learning record and future
  retrieval. Raw conversations and traces still follow the confirmed retention
  and privacy policy; durable lessons contain redacted structured facts rather
  than raw excerpts.
- KOV may automatically revise its unprotected research playbooks, planning
  templates, retrieval rules, failure taxonomies, strategy priors, and
  opportunity-ranking heuristics in response to accumulated outcome evidence.
- Adaptive-layer revisions are versioned, diffable, reversible, and evaluated by
  replaying historical runs before activation. Their measured effect and
  rollback point appear in the operator dashboard.
- The adaptive layer cannot change protected benchmarks, hard promotion gates,
  privacy or redaction controls, resource ceilings, command policy, publisher
  authority, rollback guarantees, or the external kill switch.

## Continual learning and compaction layer

- KOV has a dedicated continual-learning subsystem rather than relying on chat
  history or a growing system prompt. Its durable hierarchy is: immutable event
  ledger, sanitized episode records, compact lessons, reusable strategy and
  repository knowledge, and versioned operating summaries.
- Deterministic collectors first convert logs, traces, decisions, tool results,
  evaluations, deployments, user outcomes, and rollbacks into typed episodes.
  Each episode preserves causal event and artifact references, outcome labels,
  timestamps, affected versions, and privacy classification.
- A bounded fresh-context synthesis role periodically proposes compact lessons
  from related episodes. Every lesson states the situation, attempted approach,
  outcome, causal evidence, reusable guidance, counterexamples, confidence,
  applicability conditions, and source references. Unsupported claims fail
  validation and do not enter active memory.
- Compaction is hierarchical and append-only. New summaries never overwrite the
  evidence they summarize; they supersede earlier summaries by version while
  retaining provenance. Deterministic checks verify referenced artifacts,
  preserve unresolved contradictions, and prevent repeated summarization from
  silently turning inference into fact.
- Retrieval selects only lessons relevant to the current role, repository area,
  failure fingerprint, and lifecycle state. Qwen receives a bounded learning
  packet rather than the full ledger, raw conversations, raw traces, or the
  complete operating summary.
- KOV continually measures whether retrieved lessons improve planning,
  implementation, review, resource use, and promotion outcomes. Harmful or stale
  lessons are demoted or superseded through evidence-backed revisions, not
  deleted from history.
- Redacted durable lessons and operating summaries may outlive the raw 30-day
  evidence window. They contain no raw conversation excerpts, trace bodies,
  credentials, personal data, or externally publishable private content.
- A candidate episode is closed and classified immediately when its lifecycle
  ends. Significant failures, rollbacks, model promotions, and KOV self-updates
  trigger focused lesson synthesis as soon as their evidence is stable.
- Broader cross-episode consolidation runs once daily during an idle window and
  may run earlier when configured size, duplication, or retrieval-noise
  thresholds are crossed. Active unresolved evidence is never compacted into a
  concluded lesson until its lifecycle reaches a durable disposition.
- The local learning store uses SQLite in WAL mode for typed events, decisions,
  episodes, lessons, policies, retrieval metadata, and dashboard projections.
  Large sanitized outputs, diffs, benchmark reports, and other artifacts live as
  checksum-addressed files referenced by the database.
- Retrieval begins with deterministic metadata filters and SQLite FTS5. Local
  embeddings are optional and may be introduced only when matched retrieval
  evaluation demonstrates that they materially improve relevant-lesson recall
  or ranking enough to justify their runtime and storage cost.
- Monotonic event sequencing, content digests, integrity checks, and periodic
  atomic backups make rewritten or corrupted history detectable. Restore tests
  are part of the protected maintenance workflow.

## Recursive self-improvement lane

- KOV may propose changes to its own agents, prompts, retrieval and compaction
  logic, tools, orchestration, UI, evaluators, and other implementation modules.
  Self-candidates are visibly distinguished from Research Tutor candidates and
  cannot share an approval context with the version that authored them.
- Every self-candidate includes a typed self-change dossier: initiating lessons,
  decision rationale, affected capabilities and policies, threat analysis,
  predicted benefits and regressions, changed files, matched replay evidence,
  migration needs, activation procedure, rollback manifest, and post-activation
  measurements. Predicted and observed outcomes are linked so later KOV versions
  can learn from the change.
- A minimal immutable root of trust remains outside recursive write authority:
  the external Pause and Emergency Stop controls, append-only evidence
  provenance, privacy and outbound redaction boundary, evaluator isolation,
  publisher credential boundary, atomic champion activation, and rollback
  loader. KOV may research and document proposed changes to this kernel but
  cannot activate a version that removes or bypasses it.
- Self-promotion uses an independent clean process with protected historical,
  adversarial, schema, tool-use, privacy, security, liveness, performance, and
  rollback evaluations. The active version cannot modify those checks for its
  own candidate or write directly to the successor's promotion verdict.
- After activation, the successor operates under heightened local monitoring.
  Any loss of schema reliability, tool correctness, privacy guarantees,
  liveness, or rollback readiness restores the previous KOV champion and adds a
  failure episode to continual learning.

## Improvement threshold

- Model confidence alone never qualifies a change for promotion.
- KOV uses separate exploration and promotion thresholds. Exploration is
  intentionally creative: unconventional hypotheses, prototypes, and failed
  experiments are allowed inside an isolated candidate worktree as long as they
  remain within resource, privacy, and safety limits.
- Production promotion remains evidence-driven. A creative idea is not rejected
  because it is novel, but novelty does not excuse correctness, privacy,
  security, rollback, or protected-regression failures.
- Soft metrics such as latency, VRAM, usability, and code complexity use
  noise-aware tolerances and an overall candidate score instead of requiring
  every metric to improve. Small bounded regressions may be accepted when a
  candidate delivers a larger demonstrated product benefit and all hard gates
  pass. Promotion does not depend on one scalar score that a candidate can
  optimize at the expense of unrepresented behavior.
- A candidate with a demonstrated benefit and no measurable soft regression may
  qualify directly after all hard gates pass. A candidate with a soft regression
  must remain below protected per-metric ceilings and provide materially greater
  evidence of user benefit. Ambiguous or noisy trade-offs trigger a bounded
  follow-up experiment rather than an operator decision or model guess.
- KOV records useful negative results and may refine or decompose a promising
  failed experiment. It may not weaken a gate or rewrite the acceptance
  criterion after seeing a disappointing result.
- A bug fix requires a reproduced failure and a regression test that passes only
  after the fix.
- A performance change requires repeated matched measurements against a recorded
  baseline.
- A behavior or UX change requires replay evaluations, explicit feedback
  evidence, or another predetermined outcome metric.
- Architectural or paradigm changes require a higher evidence bar than localized
  fixes and must not weaken existing contracts merely to improve one score.
- Failed and rejected candidates remain as sanitized experiment records so KOV
  does not repeatedly explore the same dead end.

## Autonomous test evolution

- KOV may autonomously discover missing invariants, regressions, edge cases, and
  adversarial inputs and propose focused test-only candidates.
- A test-evolution candidate is separate from any production implementation it
  may later motivate. It must demonstrate the intended failure against an
  appropriate historical or current revision and identify the product invariant
  being protected.
- The protected evaluator validates that the test is deterministic, meaningful,
  non-duplicative, resistant to trivial shortcuts, and does not merely encode
  one preferred implementation. Metamorphic, property-based, boundary, and
  replay tests are preferred where appropriate.
- After acceptance, the new test joins the protected benchmark history. A later
  production candidate may satisfy it but cannot modify, skip, loosen, or delete
  it during that candidate's evaluation.
- Test-only candidates and production candidates have distinct provenance,
  lifecycle events, approval evidence, commits, and pull requests.

## Data and privacy boundary

- Autonomous analysis may use Research Tutor conversations, performance
  telemetry, application logs, tool traces, exceptions, and evaluation history.
- Autonomous access does not extend to unrelated personal files, credentials,
  `.env` files, or protected control-plane data.
- Raw conversation excerpts and raw trace contents never leave the machine.
- Commits, pull requests, issues, research queries, uploaded artifacts, and other
  outbound content may contain only redacted aggregates or synthetic examples.
- An immutable outbound gate scans diffs and GitHub metadata for secrets and
  personal data and blocks publication when uncertain.
- Personal data should be redacted or irreversibly pseudonymized whenever it is
  not required for the local user-facing feature.

## Confirmed retention policy

- Keep raw improvement-analysis copies of conversations and traces for 30 days.
- Keep verbose routine logs for 14 days and security/error logs for 30 days after
  resolution.
- Retain redacted aggregate metrics for 12 months to measure long-term trends.
- Retain compact benchmark baselines, promotion evidence, and rollback manifests
  for the lifetime of the project.
- Enforce a 10 GiB telemetry cap with oldest-first deletion inside each retention
  class. Candidate worktrees and build artifacts require a separate bounded cap.
- User-visible saved conversation history persists until explicit user deletion.
  KOV's improvement-analysis access to its raw content expires after 30 days.

## Open decisions

- The architecture is sufficiently specified to begin implementation. Remaining
  values are implementation-time calibration rather than unresolved authority or
  product-boundary decisions: per-profile command limits, measured noise bands
  for soft metrics, storage checkpoint intervals, CPRS estimator margins,
  hardware sampling cadence, final dashboard design tokens, and challenger-model
  comparison margins after a replay corpus exists.
- The first Research Tutor improvement is selected autonomously from real
  evidence after the protected vertical slice is operational; it is not
  preselected in this planning document.
