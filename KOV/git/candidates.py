"""Controller-owned Git worktrees and commits with fixed argument vectors."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_CANDIDATE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}$")
KOV_GIT_NAME = "KOV"
KOV_GIT_EMAIL = "4297262+kov37@users.noreply.github.com"


@dataclass(frozen=True, slots=True)
class CandidateWorktree:
    candidate_id: str
    branch: str
    path: Path
    base_commit: str


class GitCandidateManager:
    """Creates isolated branches without touching the user's primary checkout."""

    def __init__(self, repository: Path, worktree_root: Path) -> None:
        self.repository = repository.resolve()
        self.worktree_root = worktree_root.resolve()

    def create(self, candidate_id: str, *, base_ref: str = "HEAD") -> CandidateWorktree:
        if not _CANDIDATE.fullmatch(candidate_id):
            raise ValueError("Invalid candidate identifier")
        self._ensure_repository()
        target = self.worktree_root / candidate_id
        if target.exists():
            raise FileExistsError(target)
        branch = f"kov/{candidate_id}"
        base_commit = self._git("rev-parse", "--verify", f"{base_ref}^{{commit}}")
        self.worktree_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._git("worktree", "add", "-b", branch, str(target), base_commit)
        return CandidateWorktree(candidate_id, branch, target, base_commit)

    def changed_files(self, candidate: CandidateWorktree) -> tuple[str, ...]:
        result = self._git_in(candidate.path, "status", "--porcelain=v1", "-z")
        entries = result.split("\x00")
        paths: list[str] = []
        for entry in entries:
            if not entry:
                continue
            path = entry[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            paths.append(path)
        return tuple(sorted(set(paths)))

    def diff(self, candidate: CandidateWorktree, *, max_bytes: int = 250_000) -> str:
        result = self._git_in(candidate.path, "diff", "--no-ext-diff", "--unified=3")
        encoded = result.encode("utf-8")
        if len(encoded) > max_bytes:
            raise ValueError("Candidate diff exceeds protected review bound")
        return result

    def commit(self, candidate: CandidateWorktree, message: str) -> str:
        if not 3 <= len(message) <= 120 or "\n" in message:
            raise ValueError("Commit subject must be a single bounded line")
        self._git_in(candidate.path, "add", "--all")
        self._run(
            (
                "git",
                "-C",
                str(candidate.path),
                "-c",
                f"user.name={KOV_GIT_NAME}",
                "-c",
                f"user.email={KOV_GIT_EMAIL}",
                "commit",
                "-m",
                message,
                "--author",
                f"{KOV_GIT_NAME} <{KOV_GIT_EMAIL}>",
            )
        )
        return self._git_in(candidate.path, "rev-parse", "HEAD")

    def remove(
        self,
        candidate: CandidateWorktree,
        *,
        delete_branch: bool = False,
        force: bool = False,
    ) -> None:
        arguments = ["worktree", "remove"]
        if force:
            arguments.append("--force")
        arguments.append(str(candidate.path))
        self._git(*arguments)
        if delete_branch:
            self._git("branch", "-D", candidate.branch)

    def _ensure_repository(self) -> None:
        result = subprocess.run(
            ["git", "-C", str(self.repository), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        if result.returncode != 0 or result.stdout.strip() != "true":
            raise ValueError(f"Not a Git worktree: {self.repository}")

    def _git(self, *arguments: str) -> str:
        return self._run(("git", "-C", str(self.repository), *arguments))

    def _git_in(self, directory: Path, *arguments: str) -> str:
        return self._run(("git", "-C", str(directory), *arguments))

    @staticmethod
    def _run(argv: tuple[str, ...]) -> str:
        result = subprocess.run(
            argv,
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Command failed: {argv[1]}")
        return result.stdout.rstrip("\n")
