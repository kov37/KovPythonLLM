"""Independent successor evaluation and atomic champion activation."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from KOV.contracts.promotion import SelfChangeDossier


@dataclass(frozen=True, slots=True)
class SuccessorVerdict:
    passed: bool
    returncode: int
    report_path: Path


class SuccessorEvaluator:
    """Runs protected tests located outside the candidate's write authority."""

    def __init__(self, protected_suite: Path, reports: Path) -> None:
        self.protected_suite = protected_suite.resolve()
        self.reports = reports.resolve()

    def evaluate(
        self,
        candidate: Path,
        dossier: SelfChangeDossier,
        *,
        python_executable: Path,
    ) -> SuccessorVerdict:
        candidate = candidate.resolve()
        try:
            self.protected_suite.relative_to(candidate)
        except ValueError:
            pass
        else:
            raise PermissionError("Protected evaluator must be outside the candidate")
        if not self.protected_suite.is_dir():
            raise FileNotFoundError(self.protected_suite)
        self.reports.mkdir(parents=True, exist_ok=True, mode=0o700)
        report = self.reports / f"{dossier.candidate_id}.txt"
        with tempfile.TemporaryFile() as output:
            result = subprocess.run(
                (
                    str(python_executable),
                    "-m",
                    "pytest",
                    "-q",
                    str(self.protected_suite),
                    "--rootdir",
                    str(candidate),
                ),
                cwd=candidate,
                env={
                    "PATH": "/usr/local/bin:/usr/bin:/bin",
                    "PYTHONPATH": str(candidate),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONHASHSEED": "0",
                },
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=180,
            )
            output.seek(0)
            data = output.read(1_000_000)
        report.write_bytes(data)
        os.chmod(report, 0o600)
        return SuccessorVerdict(result.returncode == 0, result.returncode, report)


class ChampionActivator:
    """Atomically switches version symlinks while retaining the prior champion."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.champion = self.root / "champion"
        self.previous = self.root / "previous"

    def activate(self, successor: Path, verdict: SuccessorVerdict) -> None:
        if not verdict.passed:
            raise PermissionError("Defective successor cannot be activated")
        successor = successor.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.champion.is_symlink():
            prior = self.champion.resolve()
            temporary_previous = self.root / ".previous.tmp"
            temporary_previous.unlink(missing_ok=True)
            temporary_previous.symlink_to(prior)
            os.replace(temporary_previous, self.previous)
        temporary = self.root / ".champion.tmp"
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(successor)
        os.replace(temporary, self.champion)
