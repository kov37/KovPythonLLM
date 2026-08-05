"""Alternate-port canary and atomic release pointer with five-release rollback history."""

from __future__ import annotations

import os
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CanaryResult:
    passed: bool
    samples: int
    failures: int
    maximum_latency_ms: int


class ReleaseManager:
    def __init__(self, release_root: Path, *, keep_releases: int = 5) -> None:
        if not 2 <= keep_releases <= 20:
            raise ValueError("Rollback retention must be between 2 and 20 releases")
        self.release_root = release_root.resolve()
        self.keep_releases = keep_releases
        self.current = self.release_root / "current"
        self.previous = self.release_root / "previous"

    def canary(
        self,
        health_url: str,
        *,
        duration_seconds: int = 60,
        interval_seconds: int = 5,
        maximum_latency_ms: int = 2_000,
    ) -> CanaryResult:
        if not health_url.startswith("http://127.0.0.1:"):
            raise PermissionError("Canary health checks must target loopback")
        deadline = time.monotonic() + duration_seconds
        samples = failures = observed_max = 0
        while time.monotonic() < deadline:
            started = time.monotonic()
            try:
                with urllib.request.urlopen(health_url, timeout=2) as response:
                    response.read(1_024)
                    latency = int((time.monotonic() - started) * 1_000)
                    observed_max = max(observed_max, latency)
                    if response.status >= 400 or latency > maximum_latency_ms:
                        failures += 1
            except (OSError, urllib.error.URLError):
                failures += 1
            samples += 1
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(interval_seconds, remaining))
        return CanaryResult(samples > 0 and failures == 0, samples, failures, observed_max)

    def activate(self, release: Path, canary: CanaryResult) -> None:
        release = release.resolve()
        try:
            release.relative_to(self.release_root)
        except ValueError as exc:
            raise PermissionError("Release must reside below the managed release root") from exc
        if not release.is_dir() or not canary.passed:
            raise PermissionError("Only a passing staged release can be activated")
        self.release_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.current.is_symlink():
            self._replace_link(self.previous, self.current.resolve())
        self._replace_link(self.current, release)
        self._prune()

    def rollback(self) -> None:
        if not self.previous.is_symlink() or not self.previous.resolve().is_dir():
            raise RuntimeError("No previous known-good release is available")
        current = self.current.resolve() if self.current.is_symlink() else None
        prior = self.previous.resolve()
        self._replace_link(self.current, prior)
        if current is not None:
            self._replace_link(self.previous, current)

    @staticmethod
    def _replace_link(link: Path, target: Path) -> None:
        temporary = link.with_suffix(".tmp")
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(target)
        os.replace(temporary, link)

    def _prune(self) -> None:
        protected = {
            link.resolve()
            for link in (self.current, self.previous)
            if link.is_symlink() and link.resolve().is_dir()
        }
        releases = sorted(
            (
                path
                for path in self.release_root.iterdir()
                if path.is_dir() and not path.is_symlink()
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for stale in releases[self.keep_releases :]:
            if stale not in protected:
                shutil.rmtree(stale)
