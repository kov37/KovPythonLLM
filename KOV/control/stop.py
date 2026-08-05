"""Filesystem-backed Pause and Emergency Stop primitives."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ControlStatus:
    paused: bool
    emergency_stopped: bool


class StopController:
    """Durable local controls whose state survives controller restarts."""

    def __init__(self, runtime_directory: Path) -> None:
        self.runtime_directory = runtime_directory
        self.pause_path = runtime_directory / "paused"
        self.stop_path = runtime_directory / "emergency-stop"

    def initialize(self) -> None:
        self.runtime_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.runtime_directory, 0o700)

    def status(self) -> ControlStatus:
        return ControlStatus(
            paused=self.pause_path.is_file(),
            emergency_stopped=self.stop_path.is_file(),
        )

    def pause(self, reason: str) -> None:
        self._write_sentinel(self.pause_path, reason)

    def emergency_stop(self, reason: str) -> None:
        self._write_sentinel(self.stop_path, reason)

    def resume(self, *, locally_authorized: bool) -> None:
        if not locally_authorized:
            raise PermissionError("Local authorization is required to resume KOV")
        self.pause_path.unlink(missing_ok=True)

    def clear_emergency_stop(self, *, locally_authorized: bool) -> None:
        if not locally_authorized:
            raise PermissionError("Local authorization is required to clear Emergency Stop")
        self.stop_path.unlink(missing_ok=True)

    def _write_sentinel(self, target: Path, reason: str) -> None:
        self.initialize()
        temporary = target.with_suffix(".tmp")
        temporary.write_text(reason[:500] + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
