"""Digest-checked line-oriented repository tools."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from KOV.contracts.actions import (
    CreateFileAction,
    DeletePathAction,
    EditLinesAction,
    MovePathAction,
    RepoSnapshotAction,
    SearchCodeAction,
    ViewFileAction,
)
from KOV.workspaces.registry import WorkspaceRegistry


class ToolPreconditionError(RuntimeError):
    """Raised when an atomic tool precondition is stale or unsafe."""


@dataclass(frozen=True, slots=True)
class FileWindow:
    path: str
    line_start: int
    line_end: int
    total_lines: int
    digest: str
    content: str


@dataclass(frozen=True, slots=True)
class SearchPage:
    matches: tuple[str, ...]
    next_cursor: int | None
    total_returned: int


@dataclass(frozen=True, slots=True)
class ChangedFile:
    path: str
    previous_digest: str | None
    digest: str | None
    changed_hunk: str


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AtomicWorkspaceTools:
    """Small line-oriented computer interface with no shell parsing."""

    def __init__(self, registry: WorkspaceRegistry) -> None:
        self.registry = registry

    def repo_snapshot(self, action: RepoSnapshotAction, *, page_size: int = 200) -> SearchPage:
        workspace = self.registry.get(action.workspace)
        try:
            result = subprocess.run(
                [
                    "rg",
                    "--files",
                    "--hidden",
                    "-g",
                    "!.git",
                    "-g",
                    "!.venv",
                    "-g",
                    "!node_modules",
                ],
                cwd=workspace.root,
                capture_output=True,
                check=False,
                text=True,
                timeout=10,
            )
            if result.returncode not in {0, 1}:
                raise RuntimeError(result.stderr.strip() or "rg --files failed")
            files = sorted(line for line in result.stdout.splitlines() if line)
        except FileNotFoundError:
            files = [
                path.relative_to(workspace.root).as_posix()
                for path in self._iter_files(workspace.root)
            ]
        page = tuple(files[action.cursor : action.cursor + page_size])
        next_cursor = action.cursor + len(page) if action.cursor + len(page) < len(files) else None
        return SearchPage(matches=page, next_cursor=next_cursor, total_returned=len(page))

    def view_file(self, action: ViewFileAction) -> FileWindow:
        path = self.registry.resolve(action.workspace, action.path)
        if not path.is_file():
            raise FileNotFoundError(action.path)
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ToolPreconditionError("view_file accepts UTF-8 text files only") from exc
        lines = text.splitlines(keepends=True)
        if action.line_start > max(1, len(lines)):
            raise ToolPreconditionError(
                f"line_start {action.line_start} exceeds file length {len(lines)}"
            )
        selected = lines[action.line_start - 1 : action.line_end]
        numbered = "".join(
            f"{number:>7} | {line}" for number, line in enumerate(selected, start=action.line_start)
        )
        actual_end = action.line_start + len(selected) - 1 if selected else action.line_start
        return FileWindow(
            path=action.path,
            line_start=action.line_start,
            line_end=actual_end,
            total_lines=len(lines),
            digest=hashlib.sha256(raw).hexdigest(),
            content=numbered,
        )

    def search_code(self, action: SearchCodeAction, *, page_size: int = 100) -> SearchPage:
        workspace = self.registry.get(action.workspace)
        search_root = self.registry.resolve(action.workspace, action.path)
        try:
            relative_root = search_root.relative_to(workspace.root)
        except ValueError as exc:
            raise PermissionError("Search root escaped workspace") from exc
        argv = ["rg", "--line-number", "--no-heading", "--color", "never", "--hidden"]
        if action.literal:
            argv.append("--fixed-strings")
        argv.extend(["--glob", "!.git/**", "--glob", "!.venv/**", "--glob", "!node_modules/**"])
        argv.extend(["--", action.pattern, str(relative_root)])
        try:
            result = subprocess.run(
                argv,
                cwd=workspace.root,
                capture_output=True,
                check=False,
                text=True,
                timeout=15,
            )
            if result.returncode not in {0, 1}:
                raise RuntimeError(result.stderr.strip() or "rg search failed")
            matches = [line.removeprefix("./") for line in result.stdout.splitlines() if line]
        except FileNotFoundError:
            matches = self._python_search(
                workspace.root, search_root, action.pattern, literal=action.literal
            )
        page = tuple(matches[action.cursor : action.cursor + page_size])
        next_cursor = (
            action.cursor + len(page) if action.cursor + len(page) < len(matches) else None
        )
        return SearchPage(matches=page, next_cursor=next_cursor, total_returned=len(page))

    def edit_lines(self, action: EditLinesAction) -> ChangedFile:
        path = self.registry.resolve(action.workspace, action.path, for_write=True)
        if not path.is_file():
            raise FileNotFoundError(action.path)
        raw = path.read_bytes()
        current_digest = hashlib.sha256(raw).hexdigest()
        if current_digest != action.expected_digest:
            raise ToolPreconditionError("File digest changed after inspection")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ToolPreconditionError("edit_lines accepts UTF-8 text files only") from exc
        lines = text.splitlines(keepends=True)
        insertion = action.line_end == action.line_start - 1
        if action.line_start > len(lines) + 1:
            raise ToolPreconditionError("line_start exceeds append position")
        if not insertion and action.line_end > len(lines):
            raise ToolPreconditionError("line_end exceeds file length")
        replacement = action.replacement_text
        if replacement and not replacement.endswith("\n"):
            replacement += "\n"
        replacement_lines = replacement.splitlines(keepends=True)
        start_index = action.line_start - 1
        end_index = start_index if insertion else action.line_end
        updated_lines = [*lines[:start_index], *replacement_lines, *lines[end_index:]]
        updated = "".join(updated_lines).encode("utf-8")
        self._atomic_write(path, updated)
        new_digest = hashlib.sha256(updated).hexdigest()
        # Return the authoritative post-edit neighborhood, not merely an echo
        # of model-supplied replacement text. This lets a small model detect a
        # displaced neighbor immediately while keeping the observation bounded.
        preview_start = max(0, start_index - 3)
        preview_end = min(
            len(updated_lines),
            start_index + max(1, len(replacement_lines)) + 3,
        )
        preview_lines = updated_lines[preview_start:preview_end]
        preview = "".join(
            f"{number:>7} | {line}"
            for number, line in enumerate(preview_lines, start=preview_start + 1)
        )
        actual_end = preview_start + len(preview_lines)
        return ChangedFile(
            path=action.path,
            previous_digest=current_digest,
            digest=new_digest,
            changed_hunk=(
                f"@@ post-edit lines {preview_start + 1}-{actual_end}/"
                f"{len(updated_lines)} @@\n{preview}"
            ),
        )

    def create_file(self, action: CreateFileAction) -> ChangedFile:
        path = self.registry.resolve(action.workspace, action.path, for_write=True)
        if action.must_not_exist and path.exists():
            raise ToolPreconditionError("Target already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        content = action.content.encode("utf-8")
        previous = file_digest(path) if path.is_file() else None
        self._atomic_write(path, content)
        return ChangedFile(
            path=action.path,
            previous_digest=previous,
            digest=hashlib.sha256(content).hexdigest(),
            changed_hunk=f"@@ created {len(content)} bytes @@",
        )

    def move_path(self, action: MovePathAction) -> ChangedFile:
        source = self.registry.resolve(action.workspace, action.source, for_write=True)
        destination = self.registry.resolve(action.workspace, action.destination, for_write=True)
        if not source.exists():
            raise FileNotFoundError(action.source)
        if destination.exists():
            raise ToolPreconditionError("Destination already exists")
        if action.expected_digest and (
            not source.is_file() or file_digest(source) != action.expected_digest
        ):
            raise ToolPreconditionError("Source digest changed before move")
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, destination)
        digest = file_digest(destination) if destination.is_file() else None
        return ChangedFile(
            path=action.destination,
            previous_digest=action.expected_digest,
            digest=digest,
            changed_hunk=f"@@ moved {action.source} -> {action.destination} @@",
        )

    def delete_path(self, action: DeletePathAction) -> ChangedFile:
        path = self.registry.resolve(action.workspace, action.path, for_write=True)
        if not path.exists():
            raise FileNotFoundError(action.path)
        if not path.is_file():
            raise ToolPreconditionError("delete_path removes files only")
        current = file_digest(path)
        if current != action.expected_digest:
            raise ToolPreconditionError("File digest changed before deletion")
        path.unlink()
        return ChangedFile(
            path=action.path,
            previous_digest=current,
            digest=None,
            changed_hunk="@@ deleted @@",
        )

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists():
                shutil.copymode(path, temporary_name)
            else:
                os.chmod(temporary_name, 0o600)
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    @staticmethod
    def _iter_files(root: Path):
        ignored = {".git", ".venv", "node_modules", "__pycache__"}
        for directory, directory_names, filenames in os.walk(root, followlinks=False):
            directory_names[:] = sorted(name for name in directory_names if name not in ignored)
            base = Path(directory)
            for filename in sorted(filenames):
                path = base / filename
                if path.is_file() and not path.is_symlink():
                    yield path

    @classmethod
    def _python_search(
        cls, workspace_root: Path, search_root: Path, pattern: str, *, literal: bool
    ) -> list[str]:
        expression = re.compile(re.escape(pattern) if literal else pattern)
        matches: list[str] = []
        roots = (search_root,) if search_root.is_file() else cls._iter_files(search_root)
        for path in roots:
            if path.stat().st_size > 2_000_000:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            relative = path.relative_to(workspace_root).as_posix()
            matches.extend(
                f"{relative}:{number}:{line}"
                for number, line in enumerate(lines, start=1)
                if expression.search(line)
            )
            if len(matches) >= 10_000:
                break
        return matches
