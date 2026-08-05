"""Idempotent draft-PR publisher using a credential-isolated command boundary."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from KOV.contracts.promotion import EvidenceManifest, ReviewDecision
from KOV.git.candidates import KOV_GIT_EMAIL
from KOV.promotion.outbound import OutboundGate


@dataclass(frozen=True, slots=True)
class PublicationResult:
    branch: str
    pull_request_url: str
    created: bool


@dataclass(frozen=True, slots=True)
class CandidatePullRequest:
    number: int
    branch: str
    state: str
    merged_at: str | None
    url: str


class GitHubPublisher:
    """The model never receives credentials or arbitrary publisher arguments."""

    def __init__(self, repository: Path, *, allow_merge: bool = False) -> None:
        self.repository = repository.resolve()
        self.allow_merge = allow_merge
        self.outbound = OutboundGate()

    def publish_draft(
        self,
        *,
        branch: str,
        title: str,
        body: str,
        manifest: EvidenceManifest,
    ) -> PublicationResult:
        if not re.fullmatch(r"kov/[a-z0-9][a-z0-9-]{2,62}", branch):
            raise ValueError("Publisher accepts only controller-owned KOV branches")
        if not 3 <= len(title) <= 160 or "\n" in title or len(body) > 20_000:
            raise ValueError("Pull-request metadata exceeds protected bounds")
        if manifest.observer_verdict is not ReviewDecision.APPROVE:
            raise PermissionError("Independent observer did not approve publication")
        if not manifest.rollback_ready:
            raise PermissionError("Candidate has no verified rollback point")
        diff = self._run(
            "git",
            "diff",
            "--no-ext-diff",
            f"{manifest.base_commit}..{manifest.candidate_commit}",
        )
        author_email = self._run(
            "git", "show", "-s", "--format=%ae", str(manifest.candidate_commit)
        )
        if author_email != KOV_GIT_EMAIL:
            raise PermissionError("Candidate commit does not use the protected noreply identity")
        self.outbound.verify(
            title,
            body,
            json.dumps(manifest.model_dump(mode="json")),
            diff,
        )
        existing = self._run(
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "url",
            "--jq",
            ".[0].url // empty",
        )
        if existing:
            return PublicationResult(branch, existing, False)
        open_pull_requests = json.loads(
            self._run("gh", "pr", "list", "--state", "open", "--json", "headRefName,url") or "[]"
        )
        if any(
            str(item.get("headRefName", "")).startswith("kov/")
            and item.get("headRefName") != branch
            for item in open_pull_requests
        ):
            raise PermissionError("Another KOV pull request is already open")
        self._run("git", "push", "--set-upstream", "origin", branch)
        url = self._run(
            "gh", "pr", "create", "--draft", "--head", branch, "--title", title, "--body", body
        )
        return PublicationResult(branch, url, True)

    def open_candidate_url(self) -> str | None:
        pull_requests = json.loads(
            self._run("gh", "pr", "list", "--state", "open", "--json", "headRefName,url") or "[]"
        )
        for item in pull_requests:
            if str(item.get("headRefName", "")).startswith("kov/"):
                url = item.get("url")
                return str(url) if url else None
        return None

    def candidate_pull_requests(self) -> tuple[CandidatePullRequest, ...]:
        raw = self._run(
            "gh",
            "pr",
            "list",
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "number,state,headRefName,mergedAt,url",
        )
        parsed = json.loads(raw or "[]")
        if not isinstance(parsed, list):
            raise RuntimeError("GitHub PR response is not a list")
        pull_requests: list[CandidatePullRequest] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            branch = item.get("headRefName")
            if not isinstance(branch, str) or not re.fullmatch(
                r"kov/candidate-[a-f0-9]{12}", branch
            ):
                continue
            number = item.get("number")
            state = item.get("state")
            url = item.get("url")
            merged_at = item.get("mergedAt")
            if (
                not isinstance(number, int)
                or number < 1
                or state not in {"OPEN", "CLOSED", "MERGED"}
                or not isinstance(url, str)
                or (merged_at is not None and not isinstance(merged_at, str))
            ):
                raise RuntimeError("GitHub PR response violates the protected schema")
            self._validate_pull_request_url(url)
            pull_requests.append(CandidatePullRequest(number, branch, state, merged_at, url))
        return tuple(pull_requests)

    def mark_ready(self, pull_request_url: str) -> None:
        self._validate_pull_request_url(pull_request_url)
        self._run("gh", "pr", "ready", pull_request_url)

    def merge(self, pull_request_url: str) -> None:
        if not self.allow_merge:
            raise PermissionError("Automatic merge is disabled for this commissioning profile")
        self._validate_pull_request_url(pull_request_url)
        self._run("gh", "pr", "merge", pull_request_url, "--squash", "--auto")

    @staticmethod
    def _validate_pull_request_url(pull_request_url: str) -> None:
        pull_request_pattern = r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/\d+"
        if not re.fullmatch(pull_request_pattern, pull_request_url):
            raise ValueError("Invalid GitHub pull-request URL")

    def _run(self, *argv: str) -> str:
        result = subprocess.run(
            argv, cwd=self.repository, capture_output=True, check=False, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Publisher command failed: {argv[0]}")
        return result.stdout.strip()
