import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from app.parsers import pdf_parser


def _make_invoice_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 750, "INVOICE")
    c.setFont("Helvetica", 11)
    c.drawString(72, 700, "Invoice Number: INV-1001")
    c.drawString(72, 685, "Invoice Date: 01/15/2026")
    c.drawString(72, 670, "Due Date: 02/15/2026")
    c.drawString(72, 655, "Bill To: Acme Corporation")
    c.drawString(72, 640, "Total Due: $1,250.00")
    c.showPage()
    c.save()
    return buf.getvalue()


def _make_table_pdf() -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    data = [
        ["order_id", "customer", "total"],
        ["1", "Acme Corp", "100.00"],
        ["2", "Beta LLC", "250.50"],
        ["3", "Gamma Inc", "75.25"],
    ]
    table = Table(data, colWidths=[1.2 * inch, 2 * inch, 1.2 * inch])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    doc.build([table])
    return buf.getvalue()


def test_extract_text_blocks_finds_labeled_fields():
    content = _make_invoice_pdf()
    results = pdf_parser.extract_text_blocks(content)
    assert len(results) == 1
    fields = results[0]["fields"]
    assert fields.get("invoice_number") == "INV-1001"
    assert fields.get("total") == "1,250.00"
    assert results[0]["header"] == "INVOICE"


def test_extract_text_blocks_handles_malformed_pdf_without_crashing():
    results = pdf_parser.extract_text_blocks(b"not a real pdf at all")
    assert isinstance(results, list)
    assert results[0]["warnings"]


def test_extract_tables_finds_gridded_table():
    content = _make_table_pdf()
    tables = pdf_parser.extract_tables(content)
    real_tables = [t for t in tables if t.rows]
    assert real_tables, f"expected at least one detected table, got warnings: {[t.warnings for t in tables]}"
    best = max(real_tables, key=lambda t: len(t.rows))
    assert "order_id" in best.columns
    assert len(best.rows) == 3


def test_extract_tables_handles_malformed_pdf_without_crashing():
    tables = pdf_parser.extract_tables(b"not a real pdf at all")
    assert isinstance(tables, list)
    assert tables[0].warnings


def test_extract_tables_no_table_present_returns_placeholder_warning():
    content = _make_invoice_pdf()  # plain text, no gridded table
    tables = pdf_parser.extract_tables(content)
    assert all(not t.rows for t in tables)
    assert any("No tables detected" in w for t in tables for w in t.warnings)
