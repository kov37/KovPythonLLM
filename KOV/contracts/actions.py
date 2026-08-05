"""Model proposals and concrete atomic action contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from KOV.contracts.common import Digest, EvidenceRef, RelativePath, StrictModel

BoundedText = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=16_000)]
ReplacementText = Annotated[str, StringConstraints(strict=True, max_length=16_000)]
ShortText = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=600)]


class Uncertainty(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolName(StrEnum):
    REPO_SNAPSHOT = "repo_snapshot"
    VIEW_FILE = "view_file"
    SEARCH_CODE = "search_code"
    EDIT_LINES = "edit_lines"
    CREATE_FILE = "create_file"
    MOVE_PATH = "move_path"
    DELETE_PATH = "delete_path"
    RUN_CHECK = "run_check"
    VIEW_ARTIFACT = "view_artifact"
    SUBMIT_CANDIDATE = "submit_candidate"


class RepoSnapshotAction(StrictModel):
    kind: Literal["repo_snapshot"] = "repo_snapshot"
    workspace: str = Field(min_length=1, max_length=64)
    cursor: int = Field(default=0, ge=0, le=100_000)


class ViewFileAction(StrictModel):
    kind: Literal["view_file"] = "view_file"
    workspace: str = Field(min_length=1, max_length=64)
    path: RelativePath
    line_start: int = Field(ge=1, le=10_000_000)
    line_end: int = Field(ge=1, le=10_000_000)

    @model_validator(mode="after")
    def validate_window(self) -> ViewFileAction:
        if self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")
        if self.line_end - self.line_start + 1 > 100:
            raise ValueError("view_file windows cannot exceed 100 lines")
        return self


class SearchCodeAction(StrictModel):
    kind: Literal["search_code"] = "search_code"
    workspace: str = Field(min_length=1, max_length=64)
    pattern: str = Field(min_length=1, max_length=500)
    path: RelativePath = "."
    cursor: int = Field(default=0, ge=0, le=100_000)
    literal: bool = False


class EditLinesAction(StrictModel):
    kind: Literal["edit_lines"] = "edit_lines"
    workspace: str = Field(min_length=1, max_length=64)
    path: RelativePath
    line_start: int = Field(ge=1, le=10_000_000)
    line_end: int = Field(ge=0, le=10_000_000)
    # Empty text is a valid surgical edit: it deletes the inspected line range.
    replacement_text: ReplacementText
    expected_digest: Digest

    @model_validator(mode="after")
    def validate_range(self) -> EditLinesAction:
        if self.line_end < self.line_start - 1:
            raise ValueError("line_end must be at least line_start - 1")
        replaced_lines = max(0, self.line_end - self.line_start + 1)
        if replaced_lines > 100:
            raise ValueError("edit_lines cannot replace more than 100 lines")
        if len(self.replacement_text.splitlines()) > 100:
            raise ValueError("edit_lines replacement cannot exceed 100 lines")
        return self


class CreateFileAction(StrictModel):
    kind: Literal["create_file"] = "create_file"
    workspace: str = Field(min_length=1, max_length=64)
    path: RelativePath
    content: BoundedText
    must_not_exist: bool = True


class MovePathAction(StrictModel):
    kind: Literal["move_path"] = "move_path"
    workspace: str = Field(min_length=1, max_length=64)
    source: RelativePath
    destination: RelativePath
    expected_digest: Digest | None = None


class DeletePathAction(StrictModel):
    kind: Literal["delete_path"] = "delete_path"
    workspace: str = Field(min_length=1, max_length=64)
    path: RelativePath
    expected_digest: Digest


class RunCheckAction(StrictModel):
    kind: Literal["run_check"] = "run_check"
    workspace: str = Field(min_length=1, max_length=64)
    profile: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_.-]+$")
    arguments: tuple[str, ...] = Field(default_factory=tuple, max_length=32)


class ViewArtifactAction(StrictModel):
    kind: Literal["view_artifact"] = "view_artifact"
    artifact_id: EvidenceRef
    line_start: int = Field(ge=1, le=10_000_000)
    line_end: int = Field(ge=1, le=10_000_000)

    @model_validator(mode="after")
    def validate_window(self) -> ViewArtifactAction:
        if self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")
        if self.line_end - self.line_start + 1 > 200:
            raise ValueError("artifact windows cannot exceed 200 lines")
        return self


class SubmitCandidateAction(StrictModel):
    kind: Literal["submit_candidate"] = "submit_candidate"
    summary: ShortText


AgentAction = Annotated[
    RepoSnapshotAction
    | ViewFileAction
    | SearchCodeAction
    | EditLinesAction
    | CreateFileAction
    | MovePathAction
    | DeletePathAction
    | RunCheckAction
    | ViewArtifactAction
    | SubmitCandidateAction,
    Field(discriminator="kind"),
]


class ActionProposal(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    decision_summary: ShortText
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple, max_length=12)
    expected_outcome: ShortText
    uncertainty: Uncertainty
    alternatives_considered: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=4)
    requested_action: AgentAction


ModelArgument = str | int | bool | list[str]


class ModelActionProposal(StrictModel):
    """Lean Ollama grammar; controller validates arguments against the concrete tool."""

    schema_version: Literal["1.0"] = "1.0"
    decision_summary: ShortText
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple, max_length=12)
    expected_outcome: ShortText
    uncertainty: Uncertainty
    tool_call: ToolName
    arguments: dict[str, ModelArgument] = Field(max_length=16)
