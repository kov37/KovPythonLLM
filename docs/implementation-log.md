# KOV implementation log

This log records implementation facts, failed experiments, corrections, and
commissioning evidence. It contains sanitized structured facts only—never raw
conversation excerpts, raw trace bodies, credentials, or personal data.

## 2026-08-04 — Complete deterministic refactor and first real draft PR

### Baseline and dependency migration

- Replaced the legacy free-form LangChain agent with a typed Google ADK and
  Ollama boundary. Removed `AdvancedKOVAgent`, broad legacy operations, obsolete
  tests, `setup.py`, and `requirements.txt`.
- Added `pyproject.toml`, a reproducible `uv.lock`, Python 3.12 environment, and
  exact Google ADK/LiteLLM versions.
- Removed LangChain and its transitive packages from the runtime.
- Configured `qwen3.5-kilo:9b` for a 32,768-token context. Live Ollama proof
  showed full GPU residency and approximately 7.1 GiB VRAM use during
  commissioning.
- Disabled ADK content capture and OpenTelemetry exporters at package startup.

### Typed kernel, evidence, and controls

- Added strict Pydantic contracts for actions, observations, lifecycle state,
  policies, opportunities, learning episodes, lessons, review verdicts,
  manifests, and self-change dossiers.
- Added an explicit lifecycle state machine and machine-readable JSON policy
  registry.
- Added durable filesystem Pause and Emergency Stop sentinels. Clearing either
  protected state requires an explicit locally authorized call.
- Added an append-only SQLite WAL event ledger with sequence, digest,
  idempotency, update/delete denial triggers, and integrity verification.
- Added checksum-addressed artifacts, atomic backups, retention classes, the
  confirmed 14/30/365-day policy, permanent evidence classes, and a 10 GiB cap.

### Atomic Agent–Computer Interface

- Added canonical workspace resolution, traversal protection, symlink-escape
  rejection, credential deny zones, read-only modes, and immutable root-of-trust
  paths.
- Added 100-line `view_file`, paged repository snapshots and search, exact
  digest-checked `edit_lines`, safe create/move/delete, and content digests.
- Added fixed command profiles with no shell parsing, 30-second default timeout,
  process-group termination, raw local artifact capture, and deterministic
  environment variables.
- Candidate commands now execute in a networkless Bubblewrap namespace. Only
  the candidate worktree is writable; host `/tmp` writes are discarded with the
  namespace. Candidate commands cannot read the user home or GitHub keyring.
- Added a Python fallback inventory/search engine for service environments where
  `rg` is not on `PATH`; this was discovered during real systemd commissioning
  and is pending final restart verification at the time of this entry.

### CPRS and privacy boundary

- Added deterministic ANSI removal, credential/token/email/IP/private-key
  redaction, warning de-duplication, objective relevance matching, traceback and
  error preservation, hidden-line markers, and a hard bounded-output fallback.
- Outputs above 1,500 estimated tokens are reduced before model exposure. Raw
  stdout/stderr remains local in content-addressed artifacts.
- Added an outbound gate that blocks content requiring redaction, raw traceback
  bodies, raw conversation/trace labels, secrets, and personal email addresses.

### Google ADK and small-model adaptation

- Google ADK is the thin invocation boundary; the deterministic Python
  controller owns the loop, policy, state, tools, Git, and promotion.
- The first live call proved that Ollama could not compile the large
  discriminated-union grammar. The model-facing schema was reduced to the
  requested SWE-agent envelope: a tool-call enum plus bounded JSON arguments.
  The controller then validates the envelope into the richer concrete action
  union.
- Live Qwen structured output subsequently succeeded in 5.9 seconds with 333
  input tokens and 140 output tokens.
- Deterministic normalization added during live candidate runs:
  - controller-owned canonical workspace identity;
  - safe cursor and 100-line view normalization;
  - fixed search defaults for blank small-model arguments;
  - removal of all model-supplied command flags;
  - controller-owned path-to-digest cache for edit preconditions;
  - controller-owned file lengths and append-range normalization;
  - changed-file lists and bounded accumulated evidence packets.
- These normalizers reduce symbolic/numeric burden without weakening the exact
  digest, syntax, policy, test, review, or publication gates.

### Syntax-first coding loop

- Every changed Python file is parsed by the protected AST verifier before any
  test profile runs.
- Live commissioning demonstrated the gate catching an indentation error and
  returning directly to implementation without spending another pytest loop.
- A designated `python.tests` exit code of zero terminates the coding loop
  immediately. Compressed successful output still terminates based on the real
  exit code rather than display status.
- One-active-candidate Git worktrees leave the Research Tutor `main` checkout
  clean. Failed uncommitted commissioning worktrees were explicitly removed;
  their structured evidence remains in the ledger and learning store.

### Discovery and continual learning

- Added aggregate-only Research Tutor health, repository, test-density, and GPU
  collectors. No raw response body, conversation, or trace is retained.
- Added 15-minute collection, evidence-triggered six-hour synthesis, daily
  public research, interactive GPU preemption, and bounded exponential backoff.
- Added a persistent opportunity queue that enforces one exploratory selection
  after four evidence selections (rolling 80/20 candidate mix).
- Added bounded HTTPS-only public research with public-IP validation, MIME/size
  limits, redirect denial, CPRS, and no private outbound queries.
- Added typed episodes, failure fingerprints, evidence-validated lessons,
  SQLite FTS5 retrieval, high-confidence recent lesson fallback, and bounded
  per-candidate learning packets.
- Commissioning recorded and reused lessons for workspace-alias drift,
  ungrounded test symbols, create-versus-edit repair behavior, and failed syntax
  repair attempts.

### Dashboard, chat, web, and file assist

- Added an authenticated localhost-only FastAPI control plane and a production
  React/Vite dashboard.
- Dashboard views derive exclusively from typed ledger projections and show
  causal events, the model’s concise decision reason, expected outcome,
  uncertainty, outcomes, and measured/unavailable token and latency metrics.
- Added intentional responsive styling, keyboard-native controls, reduced-motion
  behavior, and no external font or telemetry requests.
- Added typed private general chat, 100-line Research Tutor file assist, and
  bounded public web assist. Raw chat prompts are not written to KOV’s ledger.
- Production frontend build completed successfully (about 196 KiB JavaScript,
  5.5 KiB CSS before gzip). Real token-authenticated HTTP probes returned 200 for
  overview, control status, and dashboard HTML.

### Independent review and first GitHub draft PR

- The first passing test candidate was rejected by the clean-context observer
  because its name could imply an overly broad all-or-nothing invariant. It was
  not published.
- A refined candidate made the invariant explicit: each individual evidence
  chunk is 11 tokens while the entire packet limit is 10, so no chunk can fit;
  the existing test already covers partial retention.
- The refined candidate passed the AST gate and the full Research Tutor suite
  (35 tests) in four model decisions.
- The first observer result contained positive findings but an inconsistent
  `reject` enum. Observer contracts now require every negative verdict to cite a
  concrete `BLOCKER:` finding. A new clean-context review returned `approve`.
- KOV created a real draft PR, still unmergeable by the commissioning profile:
  <https://github.com/kov37/local-research-tutor/pull/1>
- Draft evidence at publication:
  - branch: `kov/candidate-668f4ca2ffcd`;
  - current commit: `79cd3e70f6d826dadabdeafa12959f3103d19224`;
  - one changed test file and 17 inserted lines;
  - diff digest:
    `4733a5e386002988be9227c427fa1f4be23d8a939d6c8212e3cbc7de61211d6c`;
  - syntax passed, full pytest passed, clean observer approved, rollback ready.
- Remote verification found that Git initially inherited a personal global
  author email. The branch was immediately amended and force-with-lease updated
  to `4297262+kov37@users.noreply.github.com`. Publisher code now refuses commits
  that do not use this protected noreply identity.
- GitHub currently reports the PR as `OPEN` and `isDraft=true`; the repository
  has no remote status checks configured. KOV did not merge it.

### Deployment, service, and recursive-successor boundaries

- Added atomic release/current/previous pointers, 60-second loopback canary
  support, five-release retention, and rollback swapping.
- Added a read-only fixed-target capability broker. It exposes service and GPU
  status only; it has no sudo, package, power, kernel, driver, CUDA host stack,
  firmware, boot, disk, encryption, or recovery mutation.
- Added isolated self-candidate dossiers, an evaluator suite outside successor
  write authority, atomic champion/previous activation, and rejection of failed
  successors.
- Added five protected root-of-trust tests covering action schemas, workspace
  escape/root mutation, outbound privacy, Emergency Stop authority, and
  commissioning merge denial.
- Installed and enabled lingering user services for KOV and the dashboard. The
  dashboard service is active. The daemon initially failed because a declared
  writable directory did not exist, then exposed the missing-system-`rg` issue
  described above. The directory was created and the deterministic Python
  inventory/search fallback was implemented; final restart proof follows in the
  next log entry.

### Verification snapshot before final service restart

- Ruff: passed.
- Pyright: 0 errors and 0 warnings.
- Main implementation tests: 54 passed before the latest commissioning
  normalizers; focused normalization/controller suites continued passing after
  each fix.
- Protected evaluator: 5 passed.
- React production build: passed.
- Live ADK/Ollama structured output: passed after grammar reduction.
- Research Tutor main checkout: remained clean throughout candidate work.
- Research Tutor live health: HTTP 200 on `/` and `/api/library`.

## 2026-08-04 — Final verification and service commissioning

- Added runtime/build ignores for `.kov-state`, dashboard dependencies, and the
  built dashboard so durable local evidence and generated assets cannot be
  accidentally committed.
- Extended the daemon's systemd write allowlist only to the KOV state roots and
  the Research Tutor repository. `ProtectHome=read-only`, `ProtectSystem=strict`,
  `NoNewPrivileges=true`, and the other service restrictions remain enabled.
- Formatted and statically validated the completed tree:
  - Ruff check: passed;
  - Pyright: 0 errors, 0 warnings;
  - main suite: 58 passed;
  - protected evaluator: 5 passed;
  - React TypeScript/Vite production build: passed.
- Reinstalled and restarted both lingering user services. The daemon is active
  with `NRestarts=0` after its successful start, and the dashboard is active on
  loopback port 8787.
- Token-authenticated probes against the actual systemd dashboard returned HTTP
  200 for `/api/overview`, `/api/control`, and `/`. The token itself was never
  printed or placed in a command argument.
- Verified the append-only ledger with SQLite quick-check, per-run sequence
  continuity, and all payload digests: 399 events passed.
- The read-only doctor reported `ready=true` and every check passed, including:
  Python/toolchain readiness, repository identities, active Ollama, disabled
  content capture, Research Tutor health, GPU availability, and storage.
- Ollama reported `qwen3.5-kilo:9b` resident indefinitely at 32,768 context,
  100% GPU allocation, and 6.2 GB model residency. Doctor independently
  confirmed Flash Attention and q8 KV cache configuration.
- Research Tutor's `main` checkout remained clean. The only additional worktree
  is the intentionally retained draft-PR candidate worktree.
- GitHub final state for PR 1:
  - URL: <https://github.com/kov37/local-research-tutor/pull/1>;
  - state: open and draft;
  - head: `kov/candidate-668f4ca2ffcd` at
    `79cd3e70f6d826dadabdeafa12959f3103d19224`;
  - author identity: `KOV <4297262+kov37@users.noreply.github.com>`;
  - remote checks: none configured;
  - merge: not performed.
- Two pre-existing spreadsheet files in the KOV checkout were left untouched
  because they are unrelated user data.

## 2026-08-04 — Work-conserving continuous improvement mode

- Replaced the 15-minute collection, six-hour synthesis, and daily research
  gates with a work-conserving supervisor. A completed candidate now returns
  immediately to evidence collection, research, opportunity selection, and the
  next candidate.
- Added a durable monotonic discovery counter and five rotating focused
  opportunity classes: tests, reliability, usability, performance, and modest
  exploration. Rotation deterministically supplies four evidence-oriented
  cycles followed by one exploratory cycle while higher-severity rule-derived
  opportunities retain queue priority.
- Normal lack of queued work no longer imposes a synthesis cadence. Five-second
  polling is only a liveness wait when no selectable work exists. Exponential
  backoff is used only after infrastructure failures.
- Pause and Emergency Stop now leave the supervisor process alive while blocking
  collection, research, model calls, and candidate execution. This allows the
  dashboard and local controls to remain available for a later authorized
  resume. Interactive GPU utilization still preempts background work.
- Rejected and completed candidate worktrees are removed after their durable
  outcome. Published Git branches and ledger/artifact evidence remain available;
  cleanup failure cannot rewrite a completed outcome.
- The dashboard now identifies the runtime as `continuous` and
  `work-conserving`. Corrected the login explanation: the bearer token is sent
  only to KOV's localhost API on this computer, rather than literally remaining
  inside the browser process.
- Automatic merge remains fail-closed until required GitHub CI and branch
  protection exist. Continuous mode advances bounded candidates and draft PRs;
  it does not weaken syntax, full-test, privacy, observer, publication, or merge
  gates.

### Verification and live activation

- Ruff: passed.
- Pyright: 0 errors and 0 warnings.
- Main suite: 64 passed, including new scheduler, blocking, preemption, durable
  queue-counter, queue-liveness, and 80/20 rotation tests.
- Protected evaluator: 5 passed.
- React TypeScript/Vite production build: passed.
- Reinstalled and restarted both user services; KOV and the dashboard reported
  active, and the daemon reported `NRestarts=0`.
- The live ledger advanced from 399 to 405 events immediately after restart.
  KOV created and activated a new evidence-driven candidate, opened its isolated
  worktree, and began typed repository inspection. A distinct exploratory
  research opportunity was already queued behind it.

## 2026-08-04 — Meaningfulness retrofit and protected automatic merge

### Continuous-mode findings and containment

- Live continuous mutation produced three additional draft PRs and one active
  performance candidate. Manual evidence review found that activity exceeded
  demonstrated value:
  - PR 2 changed model temperature without a matched behavioral measurement;
  - PR 3 could preserve stale invocation counters and did not establish the
    concurrency safety claimed by its observer summary;
  - PR 4 was a modest label improvement without visual or accessibility proof;
  - the active performance experiment changed the wrong token threshold and
    entered a repair loop without a baseline benchmark.
- Paused KOV, discarded the active uncommitted performance worktree, and closed
  PRs 2 through 4 with concise evidence-based explanations. Only the stronger
  focused regression-test PR 1 was retained. No weak candidate reached `main`.
- Removed the generic rotating mutation generator. Continuous operation now
  means continuous sanitized collection, research, and opportunity evaluation;
  an empty evidence-qualified queue is healthy.

### Deterministic meaningfulness gates

- Added a typed `MeaningfulnessVerdict` evaluated before observer review or
  publication. Model confidence and prose cannot satisfy it.
- Test-density work must be test-only and pass the full Python suite.
- Reliability work must include both a source fix and reproducing regression
  test.
- Usability work must include frontend source, a focused frontend test, the
  production frontend build, and the full Python suite.
- Performance work must include source and regression changes plus an executed
  reproducible benchmark artifact. Configuration/runtime changes require
  measured before/after behavioral evidence.
- Added one-open-KOV-PR enforcement, protected candidate outcome events,
  observer outcome events, and correction of learning episodes so observer or
  evidence-gate rejection is not mislabeled as success.
- Rejected dirty worktrees now use force only inside their exact isolated
  candidate path. Published and merged evidence remains durable.
- Candidate worktrees may use the Tutor's existing frontend dependencies through
  an explicit read-only sandbox bind; frontend command profiles now execute from
  the actual `frontend` directory.

### Dashboard interpretation correction

- Relabeled the latest model rationale as `LATEST MODEL CLAIM - NOT YET
  VERIFIED`.
- Separated test-loop passes from evidence-qualified candidate approvals and
  rejections.
- Added a latest verified outcome panel and an on-screen interpretation legend:
  model claim, action authorization, evidence gate, observer review, and
  publication are distinct stages.
- The header now shows actual Pause/Emergency Stop state and describes active
  operation as evidence-gated rather than implying every event is progress.

### Public repository and immutable GitHub merge gate

- Before visibility change, scanned the current tracked tree and full Git patch
  history for credential, token, and private-key patterns without printing
  candidate secret values. Only the expected `.env.example` name appeared and
  both content scans were clear.
- Changed `kov37/local-research-tutor` from private to public after explicit
  operator authorization.
- Added and merged bootstrap PR 5 with three GitHub Actions jobs:
  `python-tests`, `frontend-build`, and `kov-policy`. All passed on the PR and
  on the resulting `main` push.
- The policy job performs a filename-only credential scan and, for `kov/*` PRs,
  validates evidence markers, protected paths, changed-file count, and diff
  size. KOV cannot edit `.github` or `scripts/validate_kov_pr.py` through its
  workspace interface.
- Activated `main` branch protection with strict up-to-date required checks,
  PR-only changes, zero human approvals, resolved conversations, linear history,
  admin enforcement, and force-push/deletion denial.
- Enabled squash-only repository auto-merge and automatic remote branch cleanup.
  Merge commits and rebase merges are disabled.
- Updated PR 1 to the enforced evidence-body format. Its first policy run failed
  closed on missing markers; metadata was corrected without bypassing the check.
  The repeated run passed all three jobs, and GitHub auto-merged PR 1 as
  `146777348eaf750364264823800b3ade7006c600`.
- Fast-forwarded the clean local Research Tutor checkout to the protected merged
  commit and removed the now-merged candidate worktree and local branch.

### Final local verification for the retrofit

- Ruff: passed.
- Pyright: 0 errors and 0 warnings.
- Main KOV suite: 68 passed.
- Protected evaluator: 5 passed, including autonomous denial for CI workflow
  and PR-validator mutation.
- KOV dashboard production build: passed.
- Research Tutor bootstrap local suite: 33 passed; production frontend build:
  passed. GitHub independently repeated the Python, frontend, and policy jobs.
- Reinstalled the hardened user services with `KOV_AUTO_MERGE=true`. Both became
  active with zero daemon restarts while the durable Pause sentinel remained in
  force during deployment.
- Authenticated dashboard overview, control, and HTML probes returned HTTP 200;
  the dashboard reported the paused state rather than presenting it as live
  mutation. Ledger integrity passed across 578 events at that checkpoint.
- Cleared Pause after verification. KOV remained stable with zero restarts and
  selected only the new-main evidence-derived test-density opportunity. No
  generic exploratory mutation or open PR existed at resume time.

## 2026-08-04 — Live supervision and small-model trajectory hardening

### Observed failures and containment

- Began a 24-hour operator supervision window with ten-minute health, candidate,
  PR, model, GPU, and resource checks. Raw conversations and trace bodies remain
  excluded from operator reporting.
- A test-density candidate repeatedly requested an empty `edit_lines`
  replacement to delete a range. The schema rejected the otherwise valid atomic
  operation three times, so the run failed without publishing.
- A retry then replaced an existing PowerPoint/PDF behavior test with a redundant
  unsupported-extension test. The full suite passed, demonstrating that a green
  suite alone did not prove the candidate was meaningful. The independent clean
  observer also rejected the diff, and no PR was created.
- A performance candidate expanded a 97-line module to 245 lines with duplicated
  definitions, then entered wrong-path repair attempts without producing the
  required benchmark. The trajectory was stopped, its isolated worktree and
  branch were removed, and Research Tutor `main` remained unchanged.

### Deterministic harness improvements

- `edit_lines` now accepts an empty replacement as an exact range deletion.
- Both the inspected replacement range and emitted replacement are capped at 100
  lines. A single mutation cannot exceed the file context the model could inspect.
- Successful edits return a bounded authoritative post-edit neighborhood rather
  than merely echoing model-supplied replacement text. This follows the ACI design
  direction documented by SWE-agent and gives the 9B model immediate visibility
  into displaced neighboring code.
- Test-focused promotion now rejects deletion of an existing test definition and
  requires a net-new test definition in the unified diff. This closes the observed
  test-replacement reward shortcut before observer review or publication.
- Deferred opportunities receive at most one durable retry. Restart recovery
  converts abandoned active opportunities to deferred state, preventing both
  infinite retries and permanently wedged queue entries.
- Confirmed orphan candidate worktrees with no open PR were force-removed only
  from the generated KOV worktree root; Research Tutor `main` and remote history
  were not modified.

### Research and dashboard observability

- Public ADK and Ollama release research now emits a sanitized
  `research.completed` event containing only artifact references, source count,
  stage, and a six-hour refresh interval. Source text remains outside the ledger.
- Scheduler exceptions now emit sanitized `run.failed` events with an explicit
  `continual_scheduler` stage instead of disappearing inside exponential backoff.
- Daemon startup closes nonterminal historical runs with append-only
  `restart_recovery` events. The dashboard now treats `run.completed` and
  `research.completed` as terminal, correcting a false `activeRuns: 11` display
  to the verified live value of zero while no candidate is executing.
- Restarted the daemon and dashboard together after the shared event-schema
  change. Authenticated overview and timeline requests returned HTTP 200, and a
  real sanitized two-source research event appeared in the timeline.

### Verification checkpoint

- KOV suite: 79 passed.
- Ruff: passed.
- Pyright: 0 errors and 0 warnings.
- `kov.service` and `kov-dashboard.service`: active with zero automatic restarts.
- Qwen `qwen3.5-kilo:9b`: 100% GPU-resident with a 32,768-token context.
- Research Tutor: clean protected `main`, no open PR, no candidate worktree.

### Deterministic continual-learning activation

- Confirmed that the production path recorded episodes but never created new
  lessons; the two existing lessons were bootstrap records and could permanently
  outrank later experience.
- Added a fixed-pattern failure distiller over sanitized controller event fields.
  It recognizes repeated missing paths, stale line coordinates, exact deletion
  schema failures, test-regression removal, and overlarge atomic edits. Guidance
  is controller-authored text, never model-authored trace summarization.
- Lesson IDs are deterministic, insertion is idempotent, and every lesson cites
  only durable event IDs that already exist. Original paths and trace bodies are
  not copied into lesson guidance.
- Bounded startup backfill distilled four lessons from actual historical failures.
  Live retrieval returned the missing-path lesson for a relevant query, and the
  latest two lessons are now inserted into fresh agent contexts.
- Changed `recent_lessons` to recency-first ordering so high-confidence bootstrap
  records cannot permanently starve newer evidence-backed experience.

### Idle-state dashboard clarity

- Added `latestDecisionActive` and `latestDecisionAt` to the overview projection.
  When no run is active, the primary panel now says `SYSTEM STATUS - NO ACTIVE
  MODEL CLAIM` and shows the quiet evidence-collection state instead of presenting
  the last failed trajectory's rationale as current work. Historical rationale
  remains available in the causal timeline.
- Production dashboard build passed and the authenticated live overview reported
  `activeRuns: 0`, `latestDecisionActive: false`, and HTTP 200 after deployment.
- Updated verification checkpoint: 84 KOV tests passed; Ruff and Pyright remained
  clean; the production dashboard build completed successfully.

### Privacy-safe Tutor runtime discovery

- Expanded the evidence collector beyond a binary Tutor HTTP response. It now
  extracts only `indexed` and `errors` integer aggregates from `/api/library`,
  discarding filenames, per-file states, and error strings before artifact
  persistence.
- Added an independent aggregate health probe for local Qdrant. A healthy Tutor
  shell can return HTTP 200 while retrieval is unavailable, so vector-store
  status is evaluated separately.
- Nonzero indexing errors create one fingerprinted reliability opportunity; an
  unavailable Qdrant endpoint creates a higher-severity service-runtime
  opportunity. Both retain only the aggregate artifact reference.
- Live verification recorded Tutor HTTP 200 in 16 ms, one indexed document, zero
  indexing errors, and Qdrant HTTP 200. The stored artifact contained aggregate
  keys only, and KOV correctly created no candidate from healthy state.
- Updated verification checkpoint: 88 KOV tests passed; Ruff and Pyright remained
  clean; both opportunity triggers have deterministic regression coverage.

### Low-allocation dashboard aggregates and PR reconciliation

- Replaced overview polling that loaded and parsed 500 unrelated event payloads
  every 2.5 seconds with typed SQLite queries for total events, distinct terminal
  runs, latest events by type, and the latest event per run.
- The authenticated overview now returns in approximately 10-16 ms and reports
  the actual ledger total (772 at this checkpoint) rather than a hard-capped 500.
- Added a read-only GitHub PR listing contract restricted to validated
  `kov/candidate-<12 hex>` branches and canonical GitHub PR URLs. It runs at most
  once per five minutes and has no create, close, ready, or merge side effects.
- Reconciled external terminal PR state to existing run IDs with idempotent
  append-only outcomes: merged PR 1 became `candidate.published`; manually closed
  PRs 2-4 became `candidate.rejected`. The dashboard funnel now correctly reports
  one approved and three rejected candidates, with merged PR 1 as the latest
  verified outcome.
- Updated verification checkpoint: 92 KOV tests passed; Ruff and Pyright remained
  clean. Both services were active with zero automatic restarts, no open PR or
  candidate worktree, and the dashboard overview returned HTTP 200 in 10 ms.

### Independent Research Tutor baseline checkpoint

- Ran the protected target directly rather than inferring health from KOV:
  34 Python tests passed, the PR policy validator accepted the non-PR context,
  and the Vite production build completed in 748 ms.
- The frontend build reported non-blocking chunk-size warnings for bundles above
  500 kB. This is recorded as exploratory performance evidence only; KOV did not
  create a candidate because the current frontend path lacks a matched
  before/after bundle benchmark and focused UI regression-test prerequisite.
- Research Tutor remained on clean protected `main` at
  `146777348eaf750364264823800b3ade7006c600`, with no open PR or worktree.
