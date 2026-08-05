"""Fresh-context structured action generation through Google ADK."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Protocol

from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import TypeAdapter, ValidationError

from KOV.contracts.actions import (
    ActionProposal,
    AgentAction,
    ModelActionProposal,
    ModelArgument,
)

SYSTEM_INSTRUCTION = """You are KOV's repository decision engine.
Return exactly one JSON object matching the supplied schema. The deterministic
controller, not you, owns permissions, state transitions, Git, and execution.
Choose one atomic action. Inspect before editing. File views are at most 100
lines. Edits require the digest from the latest view. Never invent evidence.
One edit may replace and emit at most 100 lines.
Use decision_summary for a concise, externally auditable rationale; never emit
private chain-of-thought. Prefer the smallest meaningful change and run syntax
then focused tests before submit_candidate. You cannot execute arbitrary shell.
Use the exact workspace named in CURRENT STATE. Argument signatures:
repo_snapshot(workspace,cursor); view_file(workspace,path,line_start,line_end);
search_code(workspace,pattern,path,cursor,literal);
edit_lines(workspace,path,line_start,line_end,replacement_text,expected_digest);
create_file(workspace,path,content,must_not_exist);
move_path(workspace,source,destination,expected_digest);
delete_path(workspace,path,expected_digest); run_check(workspace,profile,arguments);
view_artifact(artifact_id,line_start,line_end); submit_candidate(summary).
Valid check profiles: git.status, git.diff, python.syntax, python.tests,
frontend.typecheck, frontend.build. Omit optional arguments rather than using null.
create_file never overwrites. To repair a changed file, view that exact path to
obtain its digest, then use edit_lines. An empty edit_lines replacement_text
deletes exactly the selected line range. Changed files are listed in CURRENT STATE.
"""


class ADKLlm(Protocol):
    def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]: ...


@dataclass(frozen=True, slots=True)
class ModelTurn:
    proposal: ActionProposal
    duration_ms: int
    input_tokens: int | None
    output_tokens: int | None
    model_version: str | None


class StructuredOutputError(RuntimeError):
    """Raised when ADK cannot provide a contract-valid action."""


class ADKActionGateway:
    """Thin ADK boundary; every call receives compact controller-owned state."""

    def __init__(
        self,
        llm: ADKLlm | None = None,
        *,
        model: str = "ollama_chat/qwen3.5-kilo:9b",
        api_base: str = "http://127.0.0.1:11434",
        num_ctx: int = 32_768,
        max_output_tokens: int = 2_048,
        workspace_name: str = "candidate",
    ) -> None:
        self.llm: ADKLlm = llm or LiteLlm(
            model=model,
            api_base=api_base,
            num_ctx=num_ctx,
            num_predict=max_output_tokens,
            temperature=0.1,
            seed=7,
            think=False,
            keep_alive=-1,
        )
        self.max_output_tokens = max_output_tokens
        self.workspace_name = workspace_name

    async def propose(self, *, task: str, state_packet: str) -> ModelTurn:
        if len(task) > 8_000 or len(state_packet) > 24_000:
            raise ValueError("Model request exceeds protected fresh-context bounds")
        request = LlmRequest(
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=f"TASK\n{task}\n\nCURRENT STATE AND EVIDENCE\n{state_packet}"
                        )
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.1,
                max_output_tokens=self.max_output_tokens,
                seed=7,
            ),
        )
        request.set_output_schema(ModelActionProposal)
        started = time.monotonic()
        chunks: list[str] = []
        input_tokens: int | None = None
        output_tokens: int | None = None
        model_version: str | None = None
        error: str | None = None
        async for response in self.llm.generate_content_async(request, stream=False):
            model_version = response.model_version or model_version
            if response.error_message:
                error = response.error_message
            if response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
            if response.content and response.content.parts:
                chunks.extend(part.text for part in response.content.parts if part.text)
        if error:
            raise StructuredOutputError(error)
        raw = "".join(chunks).strip()
        try:
            model_proposal = ModelActionProposal.model_validate_json(self._extract_json(raw))
            arguments = dict(model_proposal.arguments)
            if model_proposal.tool_call.value in {
                "repo_snapshot",
                "view_file",
                "search_code",
                "edit_lines",
                "create_file",
                "move_path",
                "delete_path",
                "run_check",
            }:
                arguments["workspace"] = self.workspace_name
            defaults: dict[str, dict[str, ModelArgument]] = {
                "repo_snapshot": {"cursor": 0},
                "view_file": {"line_start": 1, "line_end": 100},
                "search_code": {"path": ".", "cursor": 0, "literal": False},
                "create_file": {"must_not_exist": True},
                "run_check": {"arguments": []},
            }
            for key, value in defaults.get(model_proposal.tool_call.value, {}).items():
                arguments.setdefault(key, value)
            known_digests = self._known_digests(state_packet)
            known_lengths = self._known_lengths(state_packet)
            if model_proposal.tool_call.value == "repo_snapshot":
                arguments["cursor"] = self._bounded_int(arguments.get("cursor"), 0, 0, 100_000)
            elif model_proposal.tool_call.value == "view_file":
                line_start = self._bounded_int(arguments.get("line_start"), 1, 1, 10_000_000)
                arguments["line_start"] = line_start
                arguments["line_end"] = line_start + 99
            elif model_proposal.tool_call.value == "search_code":
                arguments["cursor"] = self._bounded_int(arguments.get("cursor"), 0, 0, 100_000)
                pattern = arguments.get("pattern")
                arguments["pattern"] = (
                    pattern if isinstance(pattern, str) and pattern.strip() else "def test_"
                )
                path = arguments.get("path")
                arguments["path"] = path if isinstance(path, str) and path.strip() else "."
                literal = arguments.get("literal")
                arguments["literal"] = literal if isinstance(literal, bool) else False
            elif model_proposal.tool_call.value == "create_file":
                arguments["must_not_exist"] = True
            elif model_proposal.tool_call.value in {"edit_lines", "delete_path"}:
                path = arguments.get("path")
                if isinstance(path, str) and path in known_digests:
                    arguments["expected_digest"] = known_digests[path]
                if model_proposal.tool_call.value == "edit_lines" and isinstance(path, str):
                    total = known_lengths.get(path)
                    start = self._bounded_int(arguments.get("line_start"), 1, 1, 10_000_000)
                    end = self._bounded_int(
                        arguments.get("line_end"), start, max(0, start - 1), 10_000_000
                    )
                    if total is not None and start > total:
                        start, end = total + 1, total
                    elif total is not None:
                        end = min(end, total)
                    arguments["line_start"] = start
                    arguments["line_end"] = end
            elif model_proposal.tool_call.value == "move_path":
                source = arguments.get("source")
                if isinstance(source, str) and source in known_digests:
                    arguments["expected_digest"] = known_digests[source]
            elif model_proposal.tool_call.value == "run_check":
                allowed_profiles = {
                    "git.status",
                    "git.diff",
                    "python.syntax",
                    "python.tests",
                    "frontend.typecheck",
                    "frontend.build",
                }
                if arguments.get("profile") not in allowed_profiles:
                    arguments["profile"] = "git.status"
                # Profiles own their argv. Model-supplied flags are never forwarded.
                arguments.pop("arguments", None)
                arguments.pop("args", None)
            elif model_proposal.tool_call.value == "submit_candidate":
                summary = arguments.get("summary")
                if not isinstance(summary, str) or not summary.strip():
                    arguments["summary"] = model_proposal.decision_summary
            action_payload = {"kind": model_proposal.tool_call.value, **arguments}
            action = TypeAdapter(AgentAction).validate_python(action_payload)
            proposal = ActionProposal(
                decision_summary=model_proposal.decision_summary,
                evidence_refs=model_proposal.evidence_refs,
                expected_outcome=model_proposal.expected_outcome,
                uncertainty=model_proposal.uncertainty,
                requested_action=action,
            )
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            raise StructuredOutputError(f"Invalid structured action: {exc}") from exc
        return ModelTurn(
            proposal=proposal,
            duration_ms=int((time.monotonic() - started) * 1000),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_version=model_version,
        )

    @staticmethod
    def _extract_json(raw: str) -> str:
        if not raw:
            raise ValueError("Model returned no content")
        if raw.startswith("```"):
            first_newline = raw.find("\n")
            last_fence = raw.rfind("```")
            if first_newline < 0 or last_fence <= first_newline:
                raise ValueError("Malformed JSON fence")
            raw = raw[first_newline + 1 : last_fence].strip()
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Structured output must be a JSON object")
        return json.dumps(parsed, separators=(",", ":"))

    @staticmethod
    def _bounded_int(value: object, default: int, minimum: int, maximum: int) -> int:
        if isinstance(value, bool):
            return default
        try:
            parsed = int(value) if isinstance(value, (int, str)) else default
        except ValueError:
            parsed = default
        return max(minimum, min(parsed, maximum))

    @staticmethod
    def _known_digests(state_packet: str) -> dict[str, str]:
        try:
            packet = json.loads(state_packet)
            raw = packet.get("file_digests", {}) if isinstance(packet, dict) else {}
            if not isinstance(raw, dict):
                return {}
            return {
                str(path): str(digest)
                for path, digest in raw.items()
                if isinstance(path, str) and isinstance(digest, str) and len(digest) == 64
            }
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _known_lengths(state_packet: str) -> dict[str, int]:
        try:
            packet = json.loads(state_packet)
            raw = packet.get("file_lengths", {}) if isinstance(packet, dict) else {}
            if not isinstance(raw, dict):
                return {}
            return {
                str(path): length
                for path, length in raw.items()
                if isinstance(path, str) and isinstance(length, int) and length >= 0
            }
        except json.JSONDecodeError:
            return {}
