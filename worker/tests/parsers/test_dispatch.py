from pathlib import Path

import pytest

from app.parsers.base import ParsedTable
from app.parsers.dispatch import parse_file
from app.parsers.validation import ValidationError

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_dispatch_routes_csv():
    content = (FIXTURES / "orders.csv").read_bytes()
    result = parse_file(content, "orders.csv", "text/csv")
    assert isinstance(result, ParsedTable)
    assert len(result.rows) == 6


def test_dispatch_routes_json():
    content = (FIXTURES / "orders.json").read_bytes()
    result = parse_file(content, "orders.json", "application/json")
    assert isinstance(result, ParsedTable)
    assert len(result.rows) == 6


def test_dispatch_routes_xlsx():
    content = (FIXTURES / "two_sheet.xlsx").read_bytes()
    result = parse_file(content, "two_sheet.xlsx", "application/vnd.openxmlformats")
    assert isinstance(result, ParsedTable)
    assert len(result.rows) == 8


def test_dispatch_rejects_spoofed_extension():
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 20
    with pytest.raises(ValidationError):
        parse_file(exe_bytes, "totally_fine.csv", "text/csv")


def test_dispatch_pdf_falls_back_to_key_value_when_no_table():
    import io

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 700, "Invoice Number: INV-42")
    c.drawString(72, 685, "Total Due: $99.00")
    c.showPage()
    c.save()

    result = parse_file(buf.getvalue(), "invoice.pdf", "application/pdf")
    assert isinstance(result, list)
    assert result[0]["fields"].get("invoice_number") == "INV-42"
