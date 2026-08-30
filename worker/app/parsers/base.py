"""
Shared shapes for the parser layer.

`ParsedTable` is the common output of every format-specific parser
(csv/xlsx/json). PDF parsing has its own richer return shapes (see
pdf_parser.py) because PDFs aren't naturally tabular, but when PyMuPDF does
find a table it is also normalized into a `ParsedTable`.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParsedTable(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)
