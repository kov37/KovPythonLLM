# Phase 0 Verified Baseline

Verified: 2026-08-04
Repository: `github.com/kov37/KovPythonLLM`
Target: `github.com/kov37/local-research-tutor`

## Delivered

- Added an authoritative Python 3.12 `pyproject.toml` and exact `uv.lock`.
- Created the project `.venv` through `uv sync --extra test`.
- Pinned Google ADK 2.6.1 and LiteLLM 1.94.1 for the future inference boundary.
- Configured pytest, pytest-asyncio, Hypothesis, Ruff, and Pyright.
- Added strict Pydantic readiness contracts and the read-only `kov doctor` CLI.
- Added process-entry privacy defaults that disable ADK message-content capture
  and automatic OpenTelemetry signal exporters.
- Removed the unreachable basic `KOVAgent`, LangGraph, full `langchain`, and
  their unused transitive packages.
- Added a reproducible Modelfile for the 32K `qwen3.5-kilo:9b` alias.
- Preserved the existing uncommitted `AdvancedKOVAgent`, repository-tool, README,
  and test changes.
- Changed the legacy CLI default to the configured `qwen3.5-kilo:9b` alias.

## Reproducible commands

```bash
uv sync --extra test
uv run ruff check KOV tests
uv run pyright
uv run pytest -q
uv run kov doctor
```

## Verified results

- Lock: 102 packages; `uv lock --check` and `uv sync --check --extra test` pass.
- Tests: 26 passed; 17 are the preserved legacy suite and 9 cover Phase 0.
- Ruff: passes for the configured refactor surface.
- Pyright: zero errors for the typed Phase 0 surface.
- Python: 3.12.3.
- Node: 22.23.1; npm: 11.14.1.
- GPU: NVIDIA RTX 4070 Laptop GPU with 8,188 MiB VRAM.
- Ollama service: active with Flash Attention and q8 KV cache enabled.
- Model: `qwen3.5-kilo:9b`, digest prefix `f5b984e67b8d`, alias context 32,768.
- Live generation: returned `OK` with stop reason `stop`.
- Live residency: 6.2 GB, 100 percent GPU, context 32,768; `/api/ps` reported
  `size_bytes == size_vram_bytes == 6,207,559,433`.
- Privacy: no external OTLP endpoint and ADK content capture disabled in the KOV
  process.
- Disk: approximately 635.9 GiB free during verification.

`kov doctor` currently reports overall `WARN`, not `FAIL`, because Research Tutor
was intentionally not running on `127.0.0.1:8765` during this baseline. Every
required Phase 0 machine, repository, Ollama, model, residency, and privacy check
passed.

## Preserved legacy debt

The active CLI still imports `AdvancedKOVAgent`. Before Phase 0 exclusions, that
legacy path produced 49 Ruff findings and 26 Pyright errors. Those are recorded
rather than mechanically rewritten because Phase 1 through Phase 6 replace its
dataclasses, free-form parsing, conversational history, tool loop, and shell
surface. It remains covered by its preserved behavioral tests until the new
deterministic controller becomes the CLI authority.

The old whole-file/string-edit and shell functions are not approved for the
future autonomous path. Their replacement with digest-checked line tools and
named command profiles is Phase 3.
