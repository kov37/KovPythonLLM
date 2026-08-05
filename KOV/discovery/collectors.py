"""Deterministic aggregate collectors that never retain raw conversations or traces."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from KOV.storage.artifacts import ArtifactMetadata, ArtifactStore


@dataclass(frozen=True, slots=True)
class CollectionSnapshot:
    collected_at_epoch: int
    repository_commit: str | None
    dirty_file_count: int
    python_file_count: int
    test_file_count: int
    error_file_count: int
    service_status: int | None
    service_latency_ms: int | None
    indexed_document_count: int | None
    indexing_error_count: int | None
    qdrant_status: int | None
    gpu_memory_used_mib: int | None
    gpu_utilization_percent: int | None
    artifact: ArtifactMetadata


class EvidenceCollector:
    """Collects counts and health metrics only; raw bodies are discarded."""

    def __init__(self, repository: Path, artifacts: ArtifactStore) -> None:
        self.repository = repository.resolve()
        self.artifacts = artifacts

    def collect(self, health_url: str = "http://127.0.0.1:8765/api/library") -> CollectionSnapshot:
        files = self._repository_files()
        python_files = sum(path.endswith(".py") for path in files)
        test_files = sum(
            Path(path).name.startswith("test_") or "/tests/" in f"/{path}" for path in files
        )
        error_files = sum(
            any(marker in path.lower() for marker in ("error", "crash", "failure"))
            for path in files
        )
        commit = self._git_optional("rev-parse", "HEAD")
        dirty = len(self._git_optional("status", "--porcelain").splitlines())
        status, latency, indexed, indexing_errors = self._library_health(health_url)
        qdrant_status = self._endpoint_status("http://127.0.0.1:6333/healthz")
        memory, utilization = self._gpu()
        payload = {
            "schema_version": "1.0",
            "repository_commit": commit,
            "dirty_file_count": dirty,
            "python_file_count": python_files,
            "test_file_count": test_files,
            "error_file_count": error_files,
            "service_status": status,
            "service_latency_ms": latency,
            "indexed_document_count": indexed,
            "indexing_error_count": indexing_errors,
            "qdrant_status": qdrant_status,
            "gpu_memory_used_mib": memory,
            "gpu_utilization_percent": utilization,
            "file_inventory_digest": hashlib.sha256("\n".join(files).encode()).hexdigest(),
        }
        artifact = self.artifacts.put(
            json.dumps(payload, sort_keys=True).encode(),
            media_type="application/json",
            privacy_class="aggregate",
            retention_class="aggregate",
        )
        return CollectionSnapshot(
            int(time.time()),
            commit or None,
            dirty,
            python_files,
            test_files,
            error_files,
            status,
            latency,
            indexed,
            indexing_errors,
            qdrant_status,
            memory,
            utilization,
            artifact,
        )

    def _repository_files(self) -> tuple[str, ...]:
        try:
            result = subprocess.run(
                ("rg", "--files", "-g", "!.git", "-g", "!.venv", "-g", "!node_modules"),
                cwd=self.repository,
                capture_output=True,
                check=False,
                text=True,
                timeout=10,
            )
            return tuple(sorted(line for line in result.stdout.splitlines() if line))
        except FileNotFoundError:
            ignored = {".git", ".venv", "node_modules", "__pycache__"}
            files: list[str] = []
            for directory, directory_names, filenames in os.walk(
                self.repository, followlinks=False
            ):
                directory_names[:] = sorted(name for name in directory_names if name not in ignored)
                base = Path(directory)
                files.extend(
                    (base / filename).relative_to(self.repository).as_posix()
                    for filename in sorted(filenames)
                    if not (base / filename).is_symlink()
                )
            return tuple(sorted(files))

    def _git_optional(self, *arguments: str) -> str:
        result = subprocess.run(
            ("git", "-C", str(self.repository), *arguments),
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    @staticmethod
    def _library_health(
        url: str,
    ) -> tuple[int | None, int | None, int | None, int | None]:
        started = time.monotonic()
        try:
            request = urllib.request.Request(
                url, method="GET", headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(request, timeout=2) as response:
                body = response.read(65_537)
                if len(body) > 65_536:
                    raise ValueError("Library health response exceeds aggregate parsing bound")
                indexed, errors = EvidenceCollector._library_aggregates(body)
                return (
                    response.status,
                    int((time.monotonic() - started) * 1000),
                    indexed,
                    errors,
                )
        except (OSError, urllib.error.URLError):
            return None, None, None, None

    @staticmethod
    def _library_aggregates(body: bytes) -> tuple[int | None, int | None]:
        """Extract only non-negative counts; discard filenames and errors."""

        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None, None
        if not isinstance(payload, dict):
            return None, None
        indexed = payload.get("indexed")
        errors = payload.get("errors")
        safe_indexed = indexed if isinstance(indexed, int) and indexed >= 0 else None
        safe_errors = errors if isinstance(errors, int) and errors >= 0 else None
        return safe_indexed, safe_errors

    @staticmethod
    def _endpoint_status(url: str) -> int | None:
        try:
            request = urllib.request.Request(url, method="GET", headers={"Accept": "text/plain"})
            with urllib.request.urlopen(request, timeout=2) as response:
                response.read(256)
                return response.status
        except (OSError, urllib.error.URLError):
            return None

    @staticmethod
    def _gpu() -> tuple[int | None, int | None]:
        result = subprocess.run(
            (
                "nvidia-smi",
                "--query-gpu=memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ),
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            return None, None
        try:
            memory, utilization = result.stdout.splitlines()[0].split(",", 1)
            return int(memory.strip()), int(utilization.strip())
        except (IndexError, ValueError):
            return None, None
