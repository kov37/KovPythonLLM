"""Typed general chat response through ADK without persisted raw conversation history."""

from __future__ import annotations

from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from pydantic import Field

from KOV.contracts.common import EvidenceRef, StrictModel


class ChatReply(StrictModel):
    answer: str = Field(min_length=1, max_length=8_000)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple, max_length=16)
    uncertainties: tuple[str, ...] = Field(default_factory=tuple, max_length=8)


class ADKChatGateway:
    def __init__(self) -> None:
        self.llm = LiteLlm(
            model="ollama_chat/qwen3.5-kilo:9b",
            api_base="http://127.0.0.1:11434",
            num_ctx=32_768,
            num_predict=2_048,
            temperature=0.2,
            think=False,
            keep_alive=-1,
        )

    async def answer(self, prompt: str, evidence: str = "") -> ChatReply:
        if not prompt.strip() or len(prompt) > 8_000 or len(evidence) > 16_000:
            raise ValueError("Chat request exceeds protected bounds")
        request = LlmRequest(
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=f"QUESTION\n{prompt}\n\nEVIDENCE\n{evidence}")
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Answer concisely from supplied evidence. Never invent citations, expose "
                    "private reasoning, or reproduce personal data. Return the strict schema."
                ),
                temperature=0.2,
                max_output_tokens=2_048,
            ),
        )
        request.set_output_schema(ChatReply)
        chunks: list[str] = []
        async for response in self.llm.generate_content_async(request, stream=False):
            if response.error_message:
                raise RuntimeError(response.error_message)
            if response.content and response.content.parts:
                chunks.extend(part.text for part in response.content.parts if part.text)
        return ChatReply.model_validate_json("".join(chunks))
