"""
PDF parsing via PyMuPDF (fitz).

Two extraction modes, both best-effort:
  - extract_text_blocks: layout-heuristic key/value extraction for the
    labeled fields commonly found in invoices/contracts (invoice number,
    date, total, customer name), plus the largest-font line per page as a
    naive "header" signal.
  - extract_tables: any tabular data PyMuPDF's table detector finds,
    normalized into ParsedTable.

Security note: PDFs are untrusted input. Everything extracted here is
treated purely as data — never eval'd/exec'd, never used to build a
filesystem path, and never shelled out to an external tool. All parsing
goes through PyMuPDF's Python API in-process.
"""
from __future__ import annotations

import re
from typing import Any

import fitz  # PyMuPDF

from app.parsers._common import dedupe_columns
from app.parsers.base import ParsedTable

_LABEL_PATTERNS: dict[str, re.Pattern] = {
    "invoice_number": re.compile(r"invoice\s*(?:no\.?|number|#)\s*[:#]?\s*([A-Za-z0-9\-\/]+)", re.IGNORECASE),
    "invoice_date": re.compile(
        r"invoice\s*date\s*[:#]?\s*([0-9]{1,4}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{1,4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        re.IGNORECASE,
    ),
    "due_date": re.compile(
        r"due\s*date\s*[:#]?\s*([0-9]{1,4}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{1,4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        re.IGNORECASE,
    ),
    "total": re.compile(r"(?:grand\s*total|total\s*due|total\s*amount|total)\s*[:#]?\s*\$?\s*([\d,]+\.\d{2})", re.IGNORECASE),
    "customer_name": re.compile(r"(?:bill\s*to|customer|client)\s*[:#]?\s*\n?\s*([A-Za-z0-9 ,.&'\-]{2,60})", re.IGNORECASE),
}


def _open_pdf(content: bytes):
    """Open PDF bytes in-memory; PyMuPDF never touches the filesystem here."""
    return fitz.open(stream=content, filetype="pdf")


def extract_text_blocks(content: bytes) -> list[dict[str, Any]]:
    """
    Best-effort key/value extraction, one result dict per page:
    {"page_number": int, "header": str|None, "fields": {...}, "warnings": [...]}
    Never raises — a page that can't be read is reported with an "error" key.
    """
    try:
        doc = _open_pdf(content)
    except Exception as e:  # noqa: BLE001
        return [{"page_number": None, "header": None, "fields": {}, "warnings": [f"Failed to open PDF: {e}"]}]

    results: list[dict[str, Any]] = []
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            try:
                page_dict = page.get_text("dict")
            except Exception as e:  # noqa: BLE001
                results.append({
                    "page_number": page_index + 1, "header": None, "fields": {},
                    "warnings": [f"Failed to extract text from page {page_index + 1}: {e}"],
                })
                continue

            lines_text: list[str] = []
            max_font_size = 0.0
            header_text: str | None = None
            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue
                    line_text = "".join(s.get("text", "") for s in spans).strip()
                    if not line_text:
                        continue
                    lines_text.append(line_text)
                    for s in spans:
                        size = s.get("size", 0.0)
                        if size > max_font_size:
                            max_font_size = size
                            header_text = line_text

            full_text = "\n".join(lines_text)
            fields: dict[str, str] = {}
            for key, pattern in _LABEL_PATTERNS.items():
                m = pattern.search(full_text)
                if m:
                    fields[key] = m.group(1).strip()

            page_warnings = []
            if not fields:
                page_warnings.append("No recognizable invoice/contract fields found on this page (best-effort extraction).")

            results.append({
                "page_number": page_index + 1,
                "header": header_text,
                "fields": fields,
                "warnings": page_warnings,
            })
    finally:
        doc.close()

    return results


def extract_tables(content: bytes) -> list[ParsedTable]:
    """
    Extracts any tabular data PyMuPDF's table detector finds, one ParsedTable
    per detected table, tagged with the source page in a warning. Never
    raises — a page/table that fails to extract is skipped with a note
    folded into the surrounding table's warnings where possible, or simply
    omitted if nothing is extractable.
    """
    try:
        doc = _open_pdf(content)
    except Exception as e:  # noqa: BLE001
        return [ParsedTable(columns=[], rows=[], warnings=[f"Failed to open PDF: {e}"])]

    tables_out: list[ParsedTable] = []
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            try:
                finder = page.find_tables()
                found_tables = list(finder.tables)
            except Exception as e:  # noqa: BLE001
                tables_out.append(ParsedTable(
                    columns=[], rows=[],
                    warnings=[f"Table detection failed on page {page_index + 1}: {e}"],
                ))
                continue

            for t_index, table in enumerate(found_tables):
                try:
                    data = table.extract()
                except Exception as e:  # noqa: BLE001
                    tables_out.append(ParsedTable(
                        columns=[], rows=[],
                        warnings=[f"Failed to extract table {t_index + 1} on page {page_index + 1}: {e}"],
                    ))
                    continue

                if not data or len(data) < 2:
                    continue

                header_row = data[0]
                raw_names = [("" if c is None else str(c).strip()) for c in header_row]
                columns = dedupe_columns(raw_names)

                rows = []
                for raw_row in data[1:]:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        row_dict[col] = raw_row[i] if i < len(raw_row) else None
                    rows.append(row_dict)

                tables_out.append(ParsedTable(
                    columns=columns,
                    rows=rows,
                    warnings=[f"Extracted from page {page_index + 1}, table {t_index + 1}."],
                ))
    finally:
        doc.close()

    if not tables_out:
        return [ParsedTable(columns=[], rows=[], warnings=["No tables detected in PDF."])]
    return tables_out
