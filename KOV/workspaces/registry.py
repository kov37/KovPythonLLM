"""Workspace and permanent deny-zone enforcement."""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

from pydantic import Field, field_validator

from KOV.contracts.common import StrictModel

_DENIED_COMPONENTS = frozenset(
    {
        ".aws",
        ".azure",
        ".config/gcloud",
        ".docker",
        ".git",
        ".gnupg",
        ".kube",
        ".mozilla",
        ".pki",
        ".ssh",
        ".thunderbird",
        "credentials",
        "keyrings",
        "secrets",
    }
)
_DENIED_FILENAMES = frozenset({".env", ".env.local", ".netrc", "id_rsa", "id_ed25519"})
_PROTECTED_WRITE_PREFIXES = (
    ".github",
    ".kov-state",
    "policies/registry",
    "protected_evaluator",
    "KOV/control/stop.py",
    "KOV/promotion/outbound.py",
    "KOV/storage/ledger.py",
    "KOV/self_improvement/successor.py",
    "scripts/validate_kov_pr.py",
)


class WorkspaceMode(StrEnum):
    READ_ONLY = "read_only"
    CANDIDATE = "candidate"
    MANAGED = "managed"


class WorkspaceSpec(StrictModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]+$")
    root: Path
    mode: WorkspaceMode
    python_executable: Path | None = None
    read_only_dependencies: tuple[Path, ...] = ()

    @field_validator("root")
    @classmethod
    def root_must_be_absolute(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("workspace root must be absolute")
        return value.resolve()

    @field_validator("read_only_dependencies")
    @classmethod
    def dependencies_must_be_absolute(cls, values: tuple[Path, ...]) -> tuple[Path, ...]:
        if any(not value.is_absolute() for value in values):
            raise ValueError("Read-only dependency paths must be absolute")
        return tuple(value.resolve() for value in values)


class WorkspaceRegistry:
    """Immutable registry that resolves paths without following escapes."""

    def __init__(self, workspaces: tuple[WorkspaceSpec, ...]) -> None:
        by_name = {workspace.name: workspace for workspace in workspaces}
        if len(by_name) != len(workspaces):
            raise ValueError("Duplicate workspace names")
        self._workspaces = by_name

    def get(self, name: str) -> WorkspaceSpec:
        try:
            return self._workspaces[name]
        except KeyError as exc:
            raise KeyError(f"Unknown workspace: {name}") from exc

    def resolve(self, workspace_name: str, relative_path: str, *, for_write: bool = False) -> Path:
        workspace = self.get(workspace_name)
        if for_write and workspace.mode is WorkspaceMode.READ_ONLY:
            raise PermissionError(f"Workspace is read-only: {workspace_name}")
        if not relative_path or "\x00" in relative_path:
            raise ValueError("Path is empty or contains a null byte")
        candidate_path = Path(relative_path)
        if candidate_path.is_absolute():
            raise PermissionError("Absolute paths are not accepted by workspace tools")
        self._reject_denied_components(candidate_path)
        target = (workspace.root / candidate_path).resolve(strict=False)
        try:
            target.relative_to(workspace.root)
        except ValueError as exc:
            raise PermissionError("Path escapes the workspace root") from exc
        self._reject_existing_symlink_escape(workspace.root, candidate_path)
        if for_write:
            resolved_relative = target.relative_to(workspace.root).as_posix()
            self._reject_protected_write(candidate_path.as_posix(), resolved_relative)
        return target

    @staticmethod
    def _reject_denied_components(relative_path: Path) -> None:
        normalized = relative_path.as_posix()
        if normalized.startswith("./"):
            normalized = normalized[2:]
        parts = relative_path.parts
        if any(part in {"..", ""} for part in parts):
            raise PermissionError("Path traversal is not allowed")
        if relative_path.name.lower() in _DENIED_FILENAMES:
            raise PermissionError("Protected credential or environment file")
        for denied in _DENIED_COMPONENTS:
            if normalized == denied or normalized.startswith(f"{denied}/"):
                raise PermissionError("Path is inside a permanent deny zone")

    @staticmethod
    def _reject_existing_symlink_escape(root: Path, relative_path: Path) -> None:
        current = root
        for component in relative_path.parts:
            current = current / component
            if not current.exists() and not current.is_symlink():
                break
            if current.is_symlink():
                resolved = current.resolve(strict=False)
                try:
                    resolved.relative_to(root)
                except ValueError as exc:
                    raise PermissionError("Symlink escapes the workspace root") from exc

    @staticmethod
    def _reject_protected_write(*relative_paths: str) -> None:
        for relative_path in relative_paths:
            normalized = relative_path.removeprefix("./")
            for protected in _PROTECTED_WRITE_PREFIXES:
                if normalized == protected or normalized.startswith(f"{protected}/"):
                    raise PermissionError("Path belongs to KOV's immutable root of trust")

    @classmethod
    def default(cls) -> WorkspaceRegistry:
        kov_root = Path(__file__).resolve().parents[2]
        tutor_root = Path(
            os.getenv("KOV_RESEARCH_TUTOR_ROOT", "/home/digichameleon/adk/research-agent")
        ).resolve()
        tutor_python = tutor_root / ".venv" / "bin" / "python"
        return cls(
            (
                WorkspaceSpec(
                    name="kov",
                    root=kov_root,
                    mode=WorkspaceMode.MANAGED,
                    python_executable=kov_root / ".venv" / "bin" / "python",
                ),
                WorkspaceSpec(
                    name="research_tutor",
                    root=tutor_root,
                    mode=WorkspaceMode.MANAGED,
                    python_executable=tutor_python,
                ),
            )
        )
