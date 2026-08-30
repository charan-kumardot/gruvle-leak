"""
AIProvider abstraction (spec sections 52-53, 60).

Hard rule: AI is used ONLY for schema interpretation, natural-language
explanation, and drafting communications. It is never used to perform a
financial calculation, and its output is always validated against a strict
schema before use — a malformed or off-schema response is discarded and the
caller falls back to a deterministic/heuristic path, it never crashes the
scan.
"""
from __future__ import annotations

import abc
from typing import Optional

from pydantic import BaseModel, ValidationError


class ColumnMappingSuggestion(BaseModel):
    raw_name: str
    canonical_field: Optional[str]
    confidence: float
    reason: str


class ColumnMappingResponse(BaseModel):
    suggestions: list[ColumnMappingSuggestion]


class FindingExplanationResponse(BaseModel):
    why_it_matters: str
    plain_language_summary: str


class ActionDraftResponse(BaseModel):
    subject: str
    body: str
    tone: str = "professional"


class AIProvider(abc.ABC):
    """Every provider (Gemini, Groq, OpenRouter, heuristic fallback) implements this."""

    name: str = "base"

    @abc.abstractmethod
    async def suggest_column_mapping(
        self, raw_columns: list[str], canonical_fields: list[str], sample_rows: list[dict]
    ) -> ColumnMappingResponse:
        ...

    @abc.abstractmethod
    async def explain_finding(self, finding_summary: str, calculation_text: str) -> FindingExplanationResponse:
        ...

    @abc.abstractmethod
    async def draft_action(self, action_type: str, context: dict) -> ActionDraftResponse:
        ...


class AIProviderError(Exception):
    """Raised on provider failure (network, auth, malformed output). Always caught by the router."""


def validate_or_raise(model_cls: type[BaseModel], raw: dict):
    try:
        return model_cls.model_validate(raw)
    except ValidationError as e:
        raise AIProviderError(f"AI output failed schema validation: {e}") from e
