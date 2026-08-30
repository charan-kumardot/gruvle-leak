"""
Deterministic fallback AI provider — zero external calls, zero cost.

Active whenever no AI API key is configured, and used automatically if a
live provider (Gemini/Groq/OpenRouter) errors or returns malformed output,
so a scan never fails just because an AI call failed (spec section 67).
It is intentionally simple: string-similarity heuristics for column mapping,
and template-based text for explanations/drafts. Financial numbers it
touches are always ones already computed deterministically upstream — it
only ever wraps them in words.
"""
from __future__ import annotations

import difflib

from app.ai.base import (
    ActionDraftResponse,
    AIProvider,
    ColumnMappingResponse,
    ColumnMappingSuggestion,
    FindingExplanationResponse,
)

_SYNONYMS: dict[str, list[str]] = {
    "customer_id": ["customer id", "cust id", "client id", "customerid", "custid"],
    "customer_name": ["customer", "customer name", "client", "client name", "account name"],
    "order_id": ["order id", "order no", "order number", "orderid", "so number"],
    "invoice_id": ["invoice id", "invoice no", "invoice number", "invoiceid", "bill number"],
    "contract_id": ["contract id", "contract no", "agreement id"],
    "product_id": ["product id", "sku", "item id", "item code"],
    "product_name": ["product", "product name", "item", "item name", "description"],
    "quantity": ["qty", "quantity", "units", "unit count"],
    "unit_price": ["unit price", "price", "rate", "unit cost price", "selling price"],
    "list_price": ["list price", "msrp", "standard price", "catalog price"],
    "discount_amount": ["discount amount", "discount value", "disc amt"],
    "discount_percent": ["discount %", "discount percent", "disc %", "discount pct"],
    "total_amount": ["total", "amount", "total amount", "invoice total", "invoice value", "grand total", "net amount"],
    "cost_amount": ["cost", "cost amount", "cogs", "unit cost"],
    "tax_amount": ["tax", "tax amount", "gst", "vat"],
    "currency": ["currency", "curr", "ccy"],
    "order_date": ["order date", "date ordered", "created date"],
    "invoice_date": ["invoice date", "billed date", "billing date"],
    "due_date": ["due date", "payment due"],
    "paid_date": ["paid date", "payment date", "date paid"],
    "status": ["status", "order status", "invoice status", "state"],
    "renewal_date": ["renewal date", "next renewal", "renew on"],
    "contract_start_date": ["contract start", "start date", "effective date"],
    "contract_end_date": ["contract end", "end date", "expiry date", "expiration date"],
    "refund_amount": ["refund amount", "refund value", "amount refunded"],
    "refund_date": ["refund date", "date refunded"],
    "inventory_quantity": ["stock", "stock qty", "on hand", "inventory qty", "quantity on hand"],
    "last_movement_date": ["last movement", "last sold", "last transaction date"],
    "payment_amount": ["payment amount", "amount paid", "paid amount"],
    "payment_date": ["payment date", "date paid"],
}


def _normalize(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else " " for ch in s).strip()


def _score(raw: str, canonical: str) -> float:
    raw_n = _normalize(raw)
    best = difflib.SequenceMatcher(None, raw_n, canonical.replace("_", " ")).ratio()
    for syn in _SYNONYMS.get(canonical, []):
        best = max(best, difflib.SequenceMatcher(None, raw_n, syn).ratio())
        if raw_n == syn:
            best = 1.0
    return best


class HeuristicAIProvider(AIProvider):
    name = "heuristic"

    async def suggest_column_mapping(
        self, raw_columns: list[str], canonical_fields: list[str], sample_rows: list[dict]
    ) -> ColumnMappingResponse:
        suggestions = []
        for raw in raw_columns:
            best_field, best_score = None, 0.0
            for field in canonical_fields:
                s = _score(raw, field)
                if s > best_score:
                    best_field, best_score = field, s
            if best_score >= 0.6:
                suggestions.append(ColumnMappingSuggestion(
                    raw_name=raw,
                    canonical_field=best_field,
                    confidence=round(min(best_score, 0.97), 2),
                    reason=f"'{raw}' closely matches known field '{best_field}' by name similarity.",
                ))
            else:
                suggestions.append(ColumnMappingSuggestion(
                    raw_name=raw,
                    canonical_field=None,
                    confidence=0.0,
                    reason="No confident match found among known fields.",
                ))
        return ColumnMappingResponse(suggestions=suggestions)

    async def explain_finding(self, finding_summary: str, calculation_text: str) -> FindingExplanationResponse:
        return FindingExplanationResponse(
            why_it_matters=(
                f"{finding_summary} This was identified from patterns in your uploaded data and may "
                f"represent revenue that needs review."
            ),
            plain_language_summary=finding_summary,
        )

    async def draft_action(self, action_type: str, context: dict) -> ActionDraftResponse:
        subject_map = {
            "renewal_outreach": "Checking in ahead of your upcoming renewal",
            "invoice_reminder": "Reminder: outstanding invoice",
            "pricing_review": "Internal note: pricing review needed",
            "follow_up": "Following up",
        }
        subject = subject_map.get(action_type, "Follow-up")
        body = (
            f"Hi {{customer_name}},\n\n"
            f"This is a draft {action_type.replace('_', ' ')} generated from your Gruvle Leak scan. "
            f"Please review and personalize before sending — Gruvle does not send messages automatically.\n\n"
            f"Context: {context}\n\nThanks,\n{{your_name}}"
        )
        return ActionDraftResponse(subject=subject, body=body)
