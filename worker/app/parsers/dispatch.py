"""
Single entry point for turning an uploaded file's raw bytes into a
`ParsedTable` (or, for PDFs with no detectable table, a list of best-effort
key/value dicts — one per page). Always validates before parsing.
"""
from __future__ import annotations

import os

from app.parsers import csv_parser, json_parser, pdf_parser, xlsx_parser
from app.parsers.base import ParsedTable
from app.parsers.validation import validate_upload

# No size limit was specified by the product spec for this module in
# isolation; 50MB is a reasonable ceiling for spreadsheet/PDF uploads that
# keeps `validate_upload` meaningful. The API layer (app/api/) may apply a
# stricter limit of its own before bytes ever reach this function.
DEFAULT_MAX_SIZE_BYTES = 50 * 1024 * 1024


def parse_file(content: bytes, filename: str, declared_content_type: str) -> ParsedTable | list[dict]:
    """
    Validates `content` against its filename/declared type, then routes to
    the appropriate format parser.

    Returns a ParsedTable for csv/xlsx/xls/json/txt, and for PDFs, a
    ParsedTable when a detectable table exists (the largest one found),
    otherwise a list of per-page best-effort key/value dicts from
    `pdf_parser.extract_text_blocks`.

    Raises `app.parsers.validation.ValidationError` if the upload is unsafe
    or malformed (wrong size, disallowed extension, or a content signature
    that doesn't match the claimed extension).
    """
    validate_upload(content, filename, declared_content_type, DEFAULT_MAX_SIZE_BYTES)

    _, ext = os.path.splitext(filename.lower())

    if ext in (".csv", ".txt"):
        return csv_parser.parse(content, filename)
    if ext in (".xlsx", ".xls"):
        return xlsx_parser.parse(content, filename)
    if ext == ".json":
        return json_parser.parse(content, filename)
    if ext == ".pdf":
        tables = pdf_parser.extract_tables(content)
        real_tables = [t for t in tables if t.rows]
        if real_tables:
            return max(real_tables, key=lambda t: len(t.rows))
        return pdf_parser.extract_text_blocks(content)

    # validate_upload already rejects unknown extensions, so this is
    # unreachable in practice — kept as a defensive fallback.
    raise ValueError(f"No parser available for extension '{ext}'.")
