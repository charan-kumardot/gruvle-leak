import pytest

from app.ai.heuristic_provider import HeuristicAIProvider


@pytest.mark.asyncio
async def test_maps_obvious_column_names():
    provider = HeuristicAIProvider()
    result = await provider.suggest_column_mapping(
        raw_columns=["Invoice Total", "Customer ID", "Random Nonsense Column"],
        canonical_fields=["total_amount", "customer_id", "order_id"],
        sample_rows=[],
    )
    by_raw = {s.raw_name: s for s in result.suggestions}
    assert by_raw["Invoice Total"].canonical_field == "total_amount"
    assert by_raw["Customer ID"].canonical_field == "customer_id"
    assert by_raw["Random Nonsense Column"].canonical_field is None
    assert by_raw["Random Nonsense Column"].confidence == 0.0


@pytest.mark.asyncio
async def test_explain_finding_never_invents_numbers():
    provider = HeuristicAIProvider()
    result = await provider.explain_finding("Potential unbilled revenue: INR 1000.", "sum(...) = 1000")
    # the explanation must be built only from the inputs given, never a new number
    assert result.plain_language_summary == "Potential unbilled revenue: INR 1000."


@pytest.mark.asyncio
async def test_draft_action_never_auto_sends_uses_placeholders():
    provider = HeuristicAIProvider()
    result = await provider.draft_action("renewal_outreach", {"customer_count": 5})
    assert "{customer_name}" in result.body
    assert "{your_name}" in result.body
    assert "Gruvle does not send messages automatically" in result.body
