"""Read-only readiness checks for the local KOV runtime."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

type JsonScalar = str | int | float | bool | None

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESEARCH_TUTOR_ROOT = Path("/home/digichameleon/adk/research-agent")
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3.5-kilo:9b"
EXPECTED_CONTEXT = 32_768
EXPECTED_KV_CACHE = "q8_0"
EXPECTED_REPOSITORY_REMOTES = {
    "kov": "https://github.com/kov37/KovPythonLLM",
    "research_tutor": "https://github.com/kov37/local-research-tutor.git",
}


class CheckStatus(StrEnum):
    """Severity of a readiness check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class CheckResult(BaseModel):
    """One deterministic readiness result."""

    model_config = ConfigDict(extra="forbid", strict=True)

    check_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_.-]+$")
    status: CheckStatus
    summary: str = Field(min_length=1, max_length=300)
    details: dict[str, JsonScalar] = Field(default_factory=dict)


class DoctorReport(BaseModel):
    """Complete read-only machine readiness report."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: str = "1.0"
    generated_at: datetime
    overall_status: CheckStatus
    ready: bool
    checks: tuple[CheckResult, ...]

    @classmethod
    def from_checks(cls, checks: Iterable[CheckResult]) -> DoctorReport:
        materialized = tuple(checks)
        statuses = {check.status for check in materialized}
        if CheckStatus.FAIL in statuses:
            overall = CheckStatus.FAIL
        elif CheckStatus.WARN in statuses:
            overall = CheckStatus.WARN
        else:
            overall = CheckStatus.PASS
        return cls(
            generated_at=datetime.now(UTC),
            overall_status=overall,
            ready=overall is not CheckStatus.FAIL,
            checks=materialized,
        )


def _run(argv: Sequence[str], timeout_seconds: float = 5.0) -> subprocess.CompletedProcess[str]:
    """Run one fixed-argv diagnostic command without a shell."""

    return subprocess.run(
        list(argv),
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout_seconds,
    )


def _http_json(url: str, timeout_seconds: float = 3.0) -> dict[str, object]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "KOV-Doctor/1"})
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    return payload


def _command_version(command: str, version_args: Sequence[str]) -> CheckResult:
    path = shutil.which(command)
    if path is None:
        return CheckResult(
            check_id=f"toolchain.{command}",
            status=CheckStatus.FAIL,
            summary=f"Required command is unavailable: {command}",
        )
    try:
        result = _run([path, *version_args])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(
            check_id=f"toolchain.{command}",
            status=CheckStatus.FAIL,
            summary=f"Could not execute {command}",
            details={"error": str(exc), "path": path},
        )
    output = (result.stdout or result.stderr).strip().splitlines()
    summary = output[0][:200] if output else f"{command} exited {result.returncode}"
    return CheckResult(
        check_id=f"toolchain.{command}",
        status=CheckStatus.PASS if result.returncode == 0 else CheckStatus.FAIL,
        summary=summary,
        details={"path": path, "returncode": result.returncode},
    )


def _check_python() -> CheckResult:
    supported = sys.version_info >= (3, 12)
    return CheckResult(
        check_id="runtime.python",
        status=CheckStatus.PASS if supported else CheckStatus.FAIL,
        summary=f"Python {platform.python_version()}",
        details={"executable": sys.executable, "minimum": "3.12"},
    )


def _normalize_remote(remote: str) -> str:
    return remote.strip().removesuffix(".git").removesuffix("/")


def _check_repository(check_id: str, root: Path, expected_remote: str) -> CheckResult:
    if not root.is_dir():
        return CheckResult(
            check_id=check_id,
            status=CheckStatus.FAIL,
            summary=f"Repository directory is missing: {root}",
        )
    try:
        result = _run(["git", "-C", str(root), "remote", "get-url", "origin"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(
            check_id=check_id,
            status=CheckStatus.FAIL,
            summary="Could not inspect repository remote",
            details={"path": str(root), "error": str(exc)},
        )
    remote = result.stdout.strip()
    matches = result.returncode == 0 and _normalize_remote(remote) == _normalize_remote(
        expected_remote
    )
    return CheckResult(
        check_id=check_id,
        status=CheckStatus.PASS if matches else CheckStatus.FAIL,
        summary="Repository and expected origin are available"
        if matches
        else "Repository origin mismatch",
        details={"path": str(root), "origin": remote or None, "expected": expected_remote},
    )


def _check_disk(root: Path) -> CheckResult:
    usage = shutil.disk_usage(root)
    free_gib = usage.free / (1024**3)
    if free_gib < 5:
        status = CheckStatus.FAIL
    elif free_gib < 20:
        status = CheckStatus.WARN
    else:
        status = CheckStatus.PASS
    return CheckResult(
        check_id="runtime.disk",
        status=status,
        summary=f"{free_gib:.1f} GiB free on KOV filesystem",
        details={"free_gib": round(free_gib, 2), "path": str(root)},
    )


def _check_gpu() -> CheckResult:
    argv = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version,temperature.gpu,power.limit",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = _run(argv)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(
            check_id="runtime.gpu",
            status=CheckStatus.FAIL,
            summary="NVIDIA GPU inspection failed",
            details={"error": str(exc)},
        )
    values = [value.strip() for value in result.stdout.strip().split(",")]
    if result.returncode != 0 or len(values) != 5:
        return CheckResult(
            check_id="runtime.gpu",
            status=CheckStatus.FAIL,
            summary="NVIDIA GPU information is unavailable",
            details={"error": result.stderr.strip() or result.stdout.strip()},
        )
    name, memory_mib, driver, temperature_c, power_limit_w = values

    def optional_float(value: str) -> float | None:
        try:
            return float(value)
        except ValueError:
            return None

    return CheckResult(
        check_id="runtime.gpu",
        status=CheckStatus.PASS,
        summary=f"{name}, {memory_mib} MiB VRAM",
        details={
            "driver": driver,
            "temperature_c": optional_float(temperature_c),
            "power_limit_w": optional_float(power_limit_w),
        },
    )


def _check_ollama_service() -> CheckResult:
    try:
        result = _run(["systemctl", "is-active", "ollama"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(
            check_id="ollama.service",
            status=CheckStatus.FAIL,
            summary="Could not inspect Ollama service",
            details={"error": str(exc)},
        )
    active = result.returncode == 0 and result.stdout.strip() == "active"
    return CheckResult(
        check_id="ollama.service",
        status=CheckStatus.PASS if active else CheckStatus.FAIL,
        summary="Ollama service is active" if active else "Ollama service is not active",
        details={"state": result.stdout.strip() or result.stderr.strip()},
    )


def _check_ollama_environment() -> CheckResult:
    try:
        result = _run(["systemctl", "show", "ollama", "-p", "Environment", "--no-pager"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(
            check_id="ollama.environment",
            status=CheckStatus.FAIL,
            summary="Could not inspect Ollama service environment",
            details={"error": str(exc)},
        )
    environment = result.stdout.strip()
    flash_ok = "OLLAMA_FLASH_ATTENTION=1" in environment
    kv_ok = f"OLLAMA_KV_CACHE_TYPE={EXPECTED_KV_CACHE}" in environment
    status = CheckStatus.PASS if result.returncode == 0 and flash_ok and kv_ok else CheckStatus.FAIL
    return CheckResult(
        check_id="ollama.environment",
        status=status,
        summary="Flash Attention and q8 KV cache are enabled"
        if status is CheckStatus.PASS
        else "Ollama acceleration settings are incomplete",
        details={"flash_attention": flash_ok, "kv_cache_q8": kv_ok},
    )


def _parse_num_ctx(modelfile: str) -> int | None:
    match = re.search(r"^PARAMETER\s+num_ctx\s+(\d+)\s*$", modelfile, flags=re.MULTILINE)
    return int(match.group(1)) if match else None


def _check_model(ollama_url: str, model: str) -> CheckResult:
    try:
        tags = _http_json(f"{ollama_url.rstrip('/')}/api/tags")
        models_value = tags.get("models", [])
        models = models_value if isinstance(models_value, list) else []
        installed = {
            item.get("name"): item
            for item in models
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return CheckResult(
            check_id="ollama.model",
            status=CheckStatus.FAIL,
            summary="Could not query installed Ollama models",
            details={"error": str(exc), "url": ollama_url},
        )
    if model not in installed:
        return CheckResult(
            check_id="ollama.model",
            status=CheckStatus.FAIL,
            summary=f"Required model is not installed: {model}",
        )
    try:
        result = _run(["ollama", "show", "--modelfile", model], timeout_seconds=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(
            check_id="ollama.model",
            status=CheckStatus.FAIL,
            summary="Could not inspect model configuration",
            details={"model": model, "error": str(exc)},
        )
    context = _parse_num_ctx(result.stdout)
    context_ok = result.returncode == 0 and context == EXPECTED_CONTEXT
    model_info = installed[model]
    digest = model_info.get("digest") if isinstance(model_info, dict) else None
    return CheckResult(
        check_id="ollama.model",
        status=CheckStatus.PASS if context_ok else CheckStatus.FAIL,
        summary=f"{model} is installed with {context or 'unknown'} context",
        details={
            "model": model,
            "digest": str(digest) if digest else None,
            "num_ctx": context,
            "expected_num_ctx": EXPECTED_CONTEXT,
        },
    )


def _check_residency(ollama_url: str, model: str) -> CheckResult:
    try:
        payload = _http_json(f"{ollama_url.rstrip('/')}/api/ps")
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return CheckResult(
            check_id="ollama.residency",
            status=CheckStatus.FAIL,
            summary="Could not query Ollama model residency",
            details={"error": str(exc)},
        )
    models = payload.get("models", [])
    active = [item for item in models if isinstance(item, dict)] if isinstance(models, list) else []
    target = next((item for item in active if item.get("name") == model), None)
    if target is None:
        active_names = ", ".join(str(item.get("name")) for item in active) or "none"
        return CheckResult(
            check_id="ollama.residency",
            status=CheckStatus.WARN,
            summary=f"{model} is not currently loaded",
            details={"active_models": active_names, "verification": "requires live generation"},
        )
    size = target.get("size")
    size_vram = target.get("size_vram")
    context = target.get("context_length")
    fully_resident = isinstance(size, int) and isinstance(size_vram, int) and size_vram >= size
    context_ok = context == EXPECTED_CONTEXT
    status = CheckStatus.PASS if fully_resident and context_ok else CheckStatus.FAIL
    return CheckResult(
        check_id="ollama.residency",
        status=status,
        summary="Target model is fully GPU-resident at 32K"
        if status is CheckStatus.PASS
        else "Loaded model does not satisfy residency contract",
        details={
            "context_length": int(context) if isinstance(context, int) else None,
            "size_bytes": int(size) if isinstance(size, int) else None,
            "size_vram_bytes": int(size_vram) if isinstance(size_vram, int) else None,
        },
    )


def _check_privacy_environment() -> CheckResult:
    exporter_keys = (
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
        "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT",
    )
    configured_exporters = [key for key in exporter_keys if os.getenv(key)]
    legacy_capture_off = os.getenv("ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS", "").lower() == "false"
    genai_capture = os.getenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "").upper()
    genai_capture_off = genai_capture in {"", "NO_CONTENT", "FALSE"}
    if configured_exporters:
        return CheckResult(
            check_id="privacy.telemetry",
            status=CheckStatus.FAIL,
            summary="External OpenTelemetry exporter is configured",
            details={"exporter_variables": ", ".join(configured_exporters)},
        )
    if not legacy_capture_off:
        return CheckResult(
            check_id="privacy.telemetry",
            status=CheckStatus.WARN,
            summary=(
                "No exporter is configured, but ADK legacy span content is not explicitly disabled"
            ),
            details={"required": "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false"},
        )
    return CheckResult(
        check_id="privacy.telemetry",
        status=CheckStatus.PASS if genai_capture_off else CheckStatus.FAIL,
        summary="External telemetry is unset and ADK content capture is disabled",
        details={"genai_capture": genai_capture or "NO_CONTENT(default)"},
    )


def _port_is_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def _check_research_tutor_port() -> CheckResult:
    open_ = _port_is_open("127.0.0.1", 8765)
    return CheckResult(
        check_id="research_tutor.port",
        status=CheckStatus.PASS if open_ else CheckStatus.WARN,
        summary="Research Tutor is listening on 127.0.0.1:8765"
        if open_
        else "Research Tutor is not currently listening on port 8765",
        details={"host": "127.0.0.1", "port": 8765},
    )


def run_doctor() -> DoctorReport:
    """Execute the Phase 0 read-only readiness suite."""

    tutor_root = Path(os.getenv("KOV_RESEARCH_TUTOR_ROOT", str(DEFAULT_RESEARCH_TUTOR_ROOT)))
    ollama_url = os.getenv("KOV_OLLAMA_URL", DEFAULT_OLLAMA_URL)
    model = os.getenv("KOV_MODEL", DEFAULT_MODEL)
    checks = [
        _check_python(),
        _command_version("uv", ["--version"]),
        _command_version("git", ["--version"]),
        _command_version("node", ["--version"]),
        _command_version("npm", ["--version"]),
        _check_disk(REPOSITORY_ROOT),
        _check_gpu(),
        _check_repository("repository.kov", REPOSITORY_ROOT, EXPECTED_REPOSITORY_REMOTES["kov"]),
        _check_repository(
            "repository.research_tutor",
            tutor_root,
            EXPECTED_REPOSITORY_REMOTES["research_tutor"],
        ),
        _check_ollama_service(),
        _check_ollama_environment(),
        _check_model(ollama_url, model),
        _check_residency(ollama_url, model),
        _check_privacy_environment(),
        _check_research_tutor_port(),
    ]
    return DoctorReport.from_checks(checks)
