"""Same-model, fresh-context independent review session."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Protocol

from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from KOV.contracts.promotion import ReviewVerdict

_INSTRUCTION = """You are an independent code observer in a clean session.
Review only the supplied bounded diff and check manifest. Do not assume the
implementer's rationale is correct. Return the strict schema. Request changes
for ambiguity, missing coverage, unsafe behavior, or policy weakening. Never
emit chain-of-thought or quote raw trace/conversation content.
Use approve when the change is correct, safe, focused, and sufficiently tested.
Use request_changes or reject only when at least one finding begins with
"BLOCKER:" and describes a concrete defect in the supplied diff. The decision
must be logically consistent with the findings; minor style preferences are not blockers.
"""


class ObserverLlm(Protocol):
    def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]: ...


class IndependentObserver:
    def __init__(self, llm: ObserverLlm | None = None) -> None:
        self.llm = llm or LiteLlm(
            model="ollama_chat/qwen3.5-kilo:9b",
            api_base="http://127.0.0.1:11434",
            num_ctx=32_768,
            num_predict=2_048,
            temperature=0,
            seed=19,
            think=False,
            keep_alive=-1,
        )

    async def review(self, *, diff: str, check_manifest: str) -> ReviewVerdict:
        if len(diff.encode()) > 250_000 or len(check_manifest) > 8_000:
            raise ValueError("Observer input exceeds clean-session bounds")
        request = LlmRequest(
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"DIFF\n{diff}\n\nCHECKS\n{check_manifest}")],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=_INSTRUCTION, temperature=0, max_output_tokens=2_048, seed=19
            ),
        )
        request.set_output_schema(ReviewVerdict)
        chunks: list[str] = []
        async for response in self.llm.generate_content_async(request, stream=False):
            if response.error_message:
                raise RuntimeError(response.error_message)
            if response.content and response.content.parts:
                chunks.extend(part.text for part in response.content.parts if part.text)
        raw = "".join(chunks).strip()
        if raw.startswith("```"):
            raw = raw[raw.find("\n") + 1 : raw.rfind("```")].strip()
        json.loads(raw)
        verdict = ReviewVerdict.model_validate_json(raw)
        findings = (
            *verdict.correctness_findings,
            *verdict.security_findings,
            *verdict.test_findings,
        )
        if verdict.decision.value != "approve" and not any(
            finding.startswith("BLOCKER:") for finding in findings
        ):
            raise ValueError("Observer rejection is inconsistent: no BLOCKER finding")
        return verdict
