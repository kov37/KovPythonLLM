# KOV

KOV is a local, deterministic continual-improvement controller for Research
Tutor. Qwen proposes one typed atomic action at a time through Google ADK; KOV's
Python controller owns permissions, worktrees, syntax checks, tests, evidence,
independent review, publication, retention, Pause, and Emergency Stop.

The model is not a shell. KOV continuously refreshes aggregate evidence and
bounded public research, but it does not mutate code merely to remain busy. A
candidate starts only when a typed opportunity has category-specific acceptance
criteria. Reliability requires a reproducing test, performance requires an
executed before/after benchmark, UI work requires a focused frontend test and
production build, and configuration work requires measured behavioral evidence.
Pause, Emergency Stop, interactive GPU use, infrastructure backoff, or one
already-open KOV PR blocks new candidate work.

## Safety and correctness invariants

- Fresh, bounded 32K ADK requests with strict Pydantic structured output.
- Maximum 100-line file views and digest-checked line edits.
- Fixed command profiles inside a networkless Bubblewrap sandbox with a
  30-second default timeout and process-group termination.
- Mandatory AST syntax gate before tests; a syntax failure bypasses pytest.
- Isolated Git worktrees and one small candidate at a time.
- Deterministic meaningfulness gates run before clean-context observer review.
- At most one KOV PR may be open; protected GitHub CI owns final merge authority.
- Raw command output remains in local content-addressed artifacts. CPRS sends a
  redacted, relevance-preserving summary to Qwen.
- No raw conversation excerpts or raw traces are persisted in lessons or sent
  outbound. Publication is blocked when redaction would be required.
- The policy registry, Emergency Stop, evidence ledger, outbound gate, protected
  evaluator, and champion loader are outside recursive write authority.
- KOV has no authority over sudo, packages, power state, kernel, drivers, CUDA
  host software, firmware, boot, disks, encryption, or recovery.

## Setup

```bash
cd /home/digichameleon/codexTest/KovPythonLLM
uv sync --extra test
ollama create qwen3.5-kilo:9b -f models/Modelfile.qwen3.5-kilo
uv run kov doctor
```

The configured model is `qwen3.5-kilo:9b`, fully GPU-resident where available,
with `num_ctx=32768` and flash attention enabled in Ollama.

## Commands

```bash
# Private stateless general chat
uv run kov chat

# One isolated coding candidate
uv run kov improve "Add one focused regression test" \
  --repo /home/digichameleon/adk/research-agent

# Protected controls
uv run kov status
uv run kov pause "maintenance"
uv run kov emergency-stop "operator stop"
uv run kov resume
uv run kov clear-emergency-stop

# Dashboard
uv run kov-dashboard
```

The dashboard binds only to `127.0.0.1:8787`. Its token is stored with mode
`0600` at `.kov-state/control/operator.token`. It presents only typed sanitized
ledger projections: causal timelines, decision reasons, policy results,
candidate outcomes, and measured/unavailable LLM metrics.

## Continuous service

Templates live in `deploy/systemd/`. Install them as user services only after
reviewing paths:

```bash
install -Dm600 deploy/systemd/kov.service ~/.config/systemd/user/kov.service
install -Dm600 deploy/systemd/kov-dashboard.service \
  ~/.config/systemd/user/kov-dashboard.service
systemctl --user daemon-reload
systemctl --user enable --now kov.service kov-dashboard.service
loginctl enable-linger "$USER"
```

Draft publication is enabled by default when the daemon runs and `gh` is
authenticated. The public Research Tutor repository requires the `python-tests`,
`frontend-build`, and `kov-policy` GitHub checks on an up-to-date PR. With
`KOV_AUTO_MERGE=true`, KOV may mark an evidence-qualified draft ready and request
squash auto-merge; it cannot bypass or edit the required workflow, validator, or
branch protection. Set `KOV_PUBLISH_DRAFTS=false` for local-only experiments.

## Verification

```bash
uv run ruff check KOV tests
uv run pyright
uv run pytest -q
npm --prefix dashboard run build
```

Architecture, lifecycle gates, retention, privacy, discovery, learning, release,
and recursive-successor decisions are recorded in
[`docs/research-tutor-improvement-decisions.md`](docs/research-tutor-improvement-decisions.md)
and [`docs/implementation-plan.md`](docs/implementation-plan.md).
