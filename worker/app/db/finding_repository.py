"""
Persists and reconstructs `LeakFinding`s against the three Appwrite
collections `schema.py` models for them (`leak_findings`, `leak_evidence`,
`leak_calculations`), all routed through `app/db/repositories.py` so every
write gets the same team-scoped isolation as everything else.

Evidence persistence is capped at `EVIDENCE_PERSIST_CAP` per finding — each
evidence record is its own Appwrite document, and a synchronous HTTP scan
request writing hundreds of them per finding would make large scans
unreasonably slow. `LeakFinding.evidence` from the detector itself is
already capped at 50; this trims further for what actually gets persisted
and displayed via the API. The `evidence_count` shown to the user should
always come from the detector's own count, not `len(persisted evidence)`,
so a cap here is never mistaken for "this is literally all the evidence
that exists" — see `finding.calculation.inputs` for the true aggregate
counts a detector computed over.
"""
from __future__ import annotations

import json
from decimal import Decimal

from appwrite.query import Query

from app.db.repositories import (
    create_business_scoped_document,
    list_business_scoped,
    update_business_scoped_document,
)
from app.schemas.domain import (
    Calculation,
    Confidence,
    DetectorRunResult,
    EvidenceRecordRef,
    FinancialImpact,
    FindingStatus,
    ImpactType,
    LeakCategory,
    LeakFinding,
)

EVIDENCE_PERSIST_CAP = 10


def _finding_to_document_data(finding: LeakFinding) -> dict:
    return {
        "scan_id": finding.scan_id,
        "category": finding.category.value,
        "title": finding.title,
        "summary": finding.summary,
        "why_it_matters": finding.why_it_matters,
        "what_we_dont_know": finding.what_we_dont_know,
        "recommended_action": finding.recommended_action,
        "impact_type": finding.financial_impact.impact_type.value,
        "impact_amount": float(finding.financial_impact.amount),
        "currency": finding.financial_impact.currency,
        "is_recurring": finding.financial_impact.is_recurring,
        "recurrence_period": finding.financial_impact.recurrence_period,
        "confidence": finding.confidence.value,
        "confidence_explanation": finding.confidence_explanation,
        "urgency": finding.urgency,
        "recoverability": finding.recoverability,
        "priority_score": finding.priority_score,
        "detection_method": finding.detection_method,
        "source_dataset_ids": finding.source_dataset_ids,
        "status": finding.status.value,
        "is_demo": False,
    }


def save_scan_findings(business_id: str, team_id: str, detector_results: list[DetectorRunResult]) -> None:
    for result in detector_results:
        for finding in result.findings:
            create_business_scoped_document(
                "leak_findings", business_id, team_id,
                data=_finding_to_document_data(finding),
                document_id=finding.id,
            )
            for evidence in finding.evidence[:EVIDENCE_PERSIST_CAP]:
                create_business_scoped_document(
                    "leak_evidence", business_id, team_id,
                    data={
                        "finding_id": finding.id,
                        "dataset_id": evidence.dataset_id,
                        "row_index": evidence.row_index,
                        "display_fields_json": json.dumps(evidence.display_fields, default=str),
                    },
                )
            create_business_scoped_document(
                "leak_calculations", business_id, team_id,
                data={
                    "finding_id": finding.id,
                    "method": finding.calculation.method,
                    "formula": finding.calculation.formula,
                    "inputs_json": json.dumps(finding.calculation.inputs, default=str),
                    "result": float(finding.calculation.result),
                },
            )


def _document_to_finding(doc: dict, evidence_docs: list[dict], calc_doc: dict | None) -> LeakFinding:
    evidence = [
        EvidenceRecordRef(
            dataset_id=e["dataset_id"],
            row_index=e["row_index"],
            display_fields=json.loads(e["display_fields_json"]) if e.get("display_fields_json") else {},
        )
        for e in evidence_docs
    ]
    calculation = (
        Calculation(
            method=calc_doc["method"],
            formula=calc_doc["formula"],
            inputs=json.loads(calc_doc["inputs_json"]) if calc_doc.get("inputs_json") else {},
            result=Decimal(str(calc_doc["result"])),
        )
        if calc_doc is not None
        else Calculation(method="unknown", formula="", result=Decimal(str(doc["impact_amount"])))
    )

    return LeakFinding(
        id=doc["$id"],
        scan_id=doc["scan_id"],
        business_id=doc["business_id"],
        category=LeakCategory(doc["category"]),
        title=doc["title"],
        summary=doc["summary"],
        why_it_matters=doc.get("why_it_matters") or "",
        what_we_dont_know=doc.get("what_we_dont_know") or [],
        recommended_action=doc.get("recommended_action") or "",
        financial_impact=FinancialImpact(
            impact_type=ImpactType(doc["impact_type"]),
            amount=Decimal(str(doc["impact_amount"])),
            currency=doc["currency"],
            is_recurring=doc.get("is_recurring", False),
            recurrence_period=doc.get("recurrence_period"),
        ),
        confidence=Confidence(doc["confidence"]),
        confidence_explanation=doc.get("confidence_explanation") or "",
        urgency=doc.get("urgency", 0.0),
        recoverability=doc.get("recoverability", 0.0),
        priority_score=doc.get("priority_score", 0.0),
        evidence=evidence,
        calculation=calculation,
        detection_method=doc.get("detection_method") or "",
        source_dataset_ids=doc.get("source_dataset_ids") or [],
        status=FindingStatus(doc.get("status", "NEW")),
        created_at=doc.get("$createdAt") or doc.get("created_at"),
    )


def load_scan_findings(team_id: str, scan_id: str) -> list[LeakFinding]:
    finding_docs = list_business_scoped("leak_findings", team_id, queries=[Query.equal("scan_id", scan_id)])
    findings = []
    for doc in finding_docs:
        evidence_docs = list_business_scoped(
            "leak_evidence", team_id, queries=[Query.equal("finding_id", doc["$id"])]
        )
        calc_docs = list_business_scoped(
            "leak_calculations", team_id, queries=[Query.equal("finding_id", doc["$id"])]
        )
        findings.append(_document_to_finding(doc, evidence_docs, calc_docs[0] if calc_docs else None))
    return findings


def load_finding(team_id: str, finding_id: str) -> LeakFinding | None:
    from app.db.repositories import get_business_scoped

    doc = get_business_scoped("leak_findings", finding_id, team_id)
    if doc is None:
        return None
    evidence_docs = list_business_scoped("leak_evidence", team_id, queries=[Query.equal("finding_id", finding_id)])
    calc_docs = list_business_scoped("leak_calculations", team_id, queries=[Query.equal("finding_id", finding_id)])
    return _document_to_finding(doc, evidence_docs, calc_docs[0] if calc_docs else None)


def update_finding_status(team_id: str, finding_id: str, status: FindingStatus, note: str | None = None) -> LeakFinding | None:
    data: dict = {"status": status.value}
    if note:
        if status == FindingStatus.DISMISSED:
            data["dismissal_reason"] = note
        elif status == FindingStatus.RESOLVED:
            data["resolution_notes"] = note
    doc = update_business_scoped_document("leak_findings", finding_id, team_id, data)
    if doc is None:
        return None
    evidence_docs = list_business_scoped("leak_evidence", team_id, queries=[Query.equal("finding_id", finding_id)])
    calc_docs = list_business_scoped("leak_calculations", team_id, queries=[Query.equal("finding_id", finding_id)])
    return _document_to_finding(doc, evidence_docs, calc_docs[0] if calc_docs else None)
