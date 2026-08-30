"""
AIProviderRouter — tries providers in priority order (Gemini -> Groq ->
OpenRouter -> Heuristic), falling back on any AIProviderError so a scan
never fails because an external AI call failed. This is the only thing the
rest of the app imports from app.ai; individual providers are an
implementation detail.
"""
from __future__ import annotations

import logging

from app.ai.base import ActionDraftResponse, AIProvider, AIProviderError, ColumnMappingResponse, FindingExplanationResponse
from app.ai.heuristic_provider import HeuristicAIProvider
from app.core.config import Settings

logger = logging.getLogger("gruvle.ai")


class AIProviderRouter(AIProvider):
    name = "router"

    def __init__(self, providers: list[AIProvider]):
        if not providers or providers[-1].name != "heuristic":
            providers = [*providers, HeuristicAIProvider()]
        self._providers = providers

    async def _try_all(self, method_name: str, *args):
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                method = getattr(provider, method_name)
                return await method(*args), provider.name
            except AIProviderError as e:
                logger.warning("AI provider %s failed on %s: %s", provider.name, method_name, e)
                last_error = e
                continue
        # HeuristicAIProvider never raises, so this should be unreachable.
        raise last_error or AIProviderError("All AI providers failed")

    async def suggest_column_mapping(self, raw_columns, canonical_fields, sample_rows) -> ColumnMappingResponse:
        result, _ = await self._try_all("suggest_column_mapping", raw_columns, canonical_fields, sample_rows)
        return result

    async def explain_finding(self, finding_summary, calculation_text) -> FindingExplanationResponse:
        result, _ = await self._try_all("explain_finding", finding_summary, calculation_text)
        return result

    async def draft_action(self, action_type, context) -> ActionDraftResponse:
        result, _ = await self._try_all("draft_action", action_type, context)
        return result


def build_ai_router(settings: Settings) -> AIProviderRouter:
    providers: list[AIProvider] = []
    if settings.gemini_api_key:
        from app.ai.gemini_provider import GeminiProvider
        providers.append(GeminiProvider(settings.gemini_api_key))
    if settings.groq_api_key:
        from app.ai.openai_compatible_provider import GroqProvider
        providers.append(GroqProvider(settings.groq_api_key))
    if settings.openrouter_api_key:
        from app.ai.openai_compatible_provider import OpenRouterProvider
        providers.append(OpenRouterProvider(settings.openrouter_api_key))
    providers.append(HeuristicAIProvider())
    return AIProviderRouter(providers)
