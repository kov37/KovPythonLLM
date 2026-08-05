"""Named fixed-argv command profiles with bounded artifact capture."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from KOV.contracts.actions import RunCheckAction
from KOV.storage.artifacts import ArtifactMetadata, ArtifactStore
from KOV.workspaces.registry import WorkspaceRegistry


@dataclass(frozen=True, slots=True)
class CommandProfile:
    name: str
    argv: tuple[str, ...]
    timeout_seconds: float = 30.0
    allow_arguments: bool = False
    sandboxed: bool = True
    working_directory: str = "."


@dataclass(frozen=True, slots=True)
class CommandResult:
    profile: str
    argv: tuple[str, ...]
    returncode: int
    timed_out: bool
    duration_ms: int
    stdout: ArtifactMetadata
    stderr: ArtifactMetadata


class CommandRunner:
    """Executes only controller-owned profiles; never accepts a command string."""

    def __init__(
        self,
        registry: WorkspaceRegistry,
        artifacts: ArtifactStore,
        profiles: tuple[CommandProfile, ...] | None = None,
    ) -> None:
        self.registry = registry
        self.artifacts = artifacts
        selected = profiles or self.default_profiles()
        self.profiles = {profile.name: profile for profile in selected}
        if len(self.profiles) != len(selected):
            raise ValueError("Duplicate command profile")

    @staticmethod
    def default_profiles() -> tuple[CommandProfile, ...]:
        return (
            CommandProfile("git.status", ("git", "status", "--short")),
            CommandProfile("git.diff", ("git", "diff", "--check")),
            CommandProfile("python.syntax", ("{python}", "-m", "compileall", "-q", ".")),
            CommandProfile("python.tests", ("{python}", "-m", "pytest", "-q")),
            CommandProfile(
                "frontend.typecheck",
                ("npm", "run", "typecheck", "--if-present"),
                working_directory="frontend",
            ),
            CommandProfile("frontend.build", ("npm", "run", "build"), working_directory="frontend"),
        )

    def run(self, action: RunCheckAction) -> CommandResult:
        try:
            profile = self.profiles[action.profile]
        except KeyError as exc:
            raise PermissionError(f"Unknown command profile: {action.profile}") from exc
        if action.arguments and not profile.allow_arguments:
            raise PermissionError(f"Profile does not accept model arguments: {profile.name}")
        workspace = self.registry.get(action.workspace)
        python = workspace.python_executable
        argv = tuple(
            str(python) if token == "{python}" and python is not None else token
            for token in profile.argv
        )
        if "{python}" in argv:
            raise RuntimeError(f"No Python interpreter configured for {workspace.name}")
        environment = {
            "HOME": str(workspace.root / ".kov-home"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
        Path(environment["HOME"]).mkdir(parents=True, exist_ok=True, mode=0o700)
        working_directory = (workspace.root / profile.working_directory).resolve()
        if not working_directory.is_relative_to(workspace.root) or not working_directory.is_dir():
            raise RuntimeError(f"Invalid profile working directory: {profile.working_directory}")
        execution_argv = self._sandbox_argv(
            argv,
            workspace.root,
            python,
            working_directory,
            workspace.read_only_dependencies,
        )
        started = time.monotonic()
        with (
            tempfile.TemporaryFile() as stdout_file,
            tempfile.TemporaryFile() as stderr_file,
        ):
            process = subprocess.Popen(
                execution_argv,
                cwd=workspace.root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
            timed_out = False
            try:
                returncode = process.wait(timeout=profile.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    returncode = process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    returncode = process.wait(timeout=2)
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout = self.artifacts.put(
                stdout_file.read(), retention_class="candidate", privacy_class="raw_local"
            )
            stderr = self.artifacts.put(
                stderr_file.read(), retention_class="candidate", privacy_class="raw_local"
            )
        return CommandResult(
            profile=profile.name,
            argv=argv,
            returncode=returncode,
            timed_out=timed_out,
            duration_ms=int((time.monotonic() - started) * 1000),
            stdout=stdout,
            stderr=stderr,
        )

    @staticmethod
    def _sandbox_argv(
        argv: tuple[str, ...],
        workspace: Path,
        python: Path | None,
        working_directory: Path,
        read_only_dependencies: tuple[Path, ...],
    ) -> tuple[str, ...]:
        bwrap = shutil.which("bwrap")
        if bwrap is None:
            raise RuntimeError("bubblewrap is required for candidate command isolation")
        required_paths = {workspace}
        if python is not None and not python.is_relative_to("/usr"):
            required_paths.add(python.parent.parent)
        required_paths.update(path.resolve() for path in read_only_dependencies)
        directories: set[Path] = set()
        for path in required_paths:
            directories.update(path.parents)
        create_dirs: list[str] = []
        precreated = {
            Path(path) for path in ("/", "/usr", "/bin", "/lib", "/lib64", "/proc", "/dev", "/tmp")
        }
        for directory in sorted(
            (path for path in directories if path not in precreated),
            key=lambda item: len(item.parts),
        ):
            create_dirs.extend(("--dir", str(directory)))
        bindings: list[str] = []
        if python is not None and not python.is_relative_to("/usr"):
            venv = python.parent.parent
            bindings.extend(("--ro-bind", str(venv), str(venv)))
        for dependency in read_only_dependencies:
            resolved = dependency.resolve()
            if not resolved.is_dir():
                raise RuntimeError(f"Read-only dependency is unavailable: {resolved}")
            bindings.extend(("--ro-bind", str(resolved), str(resolved)))
        return (
            bwrap,
            "--die-with-parent",
            "--new-session",
            "--unshare-net",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/bin",
            "/bin",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
            "--ro-bind",
            "/etc",
            "/etc",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            *create_dirs,
            *bindings,
            "--bind",
            str(workspace),
            str(workspace),
            "--chdir",
            str(working_directory),
            "--",
            *argv,
        )
