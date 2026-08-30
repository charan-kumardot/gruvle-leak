from pathlib import Path

from app.parsers import csv_parser

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_happy_path_orders_csv():
    content = (FIXTURES / "orders.csv").read_bytes()
    table = csv_parser.parse(content, "orders.csv")
    assert table.columns == ["order_id", "customer_name", "total"]
    assert len(table.rows) == 6
    assert table.rows[0]["customer_name"] == "Acme Corp"


def test_bom_and_inconsistent_quoting():
    content = (
        b"\xef\xbb\xbforder_id,note\n"
        b'1,"has, a comma"\n'
        b"2,no comma\n"
        b'3,"quoted ""with escaped quotes"""\n'
    )
    table = csv_parser.parse(content, "notes.csv")
    assert table.columns == ["order_id", "note"]
    assert len(table.rows) == 3
    assert table.rows[0]["note"] == "has, a comma"
    assert table.rows[2]["note"] == 'quoted "with escaped quotes"'
    assert any("byte-order mark" in w for w in table.warnings)


def test_semicolon_delimiter_sniffed():
    content = b"id;name;amount\n1;foo;10\n2;bar;20\n"
    table = csv_parser.parse(content, "eu.csv")
    assert table.columns == ["id", "name", "amount"]
    assert len(table.rows) == 2


def test_empty_file_returns_warning_not_crash():
    table = csv_parser.parse(b"", "empty.csv")
    assert table.rows == []
    assert table.columns == []
    assert table.warnings


def test_trailing_blank_rows_and_columns_dropped():
    content = (
        b"a,b,\n"
        b"1,2,\n"
        b"3,4,\n"
        b",,\n"
    )
    table = csv_parser.parse(content, "trailing.csv")
    assert "a" in table.columns and "b" in table.columns
    # blank trailing column and blank trailing row should be gone
    assert len(table.rows) == 2
    assert all(v not in ("", None) for row in table.rows for v in [row.get("a"), row.get("b")])


def test_mixed_type_column_does_not_crash():
    content = b"id,value\n1,10\n2,abc\n3,30\n"
    table = csv_parser.parse(content, "mixed.csv")
    assert len(table.rows) == 3
    # Should not raise; values preserved in some coerced/original form.
    assert table.rows[1]["value"] == "abc"


def test_large_file_uses_chunked_path(monkeypatch):
    monkeypatch.setattr(csv_parser, "_CHUNK_THRESHOLD_BYTES", 100)
    monkeypatch.setattr(csv_parser, "_CHUNK_ROWS", 5)
    lines = [b"id,value"] + [f"{i},{i*2}".encode() for i in range(50)]
    content = b"\n".join(lines) + b"\n"
    table = csv_parser.parse(content, "large.csv")
    assert len(table.rows) == 50
    assert any("chunks" in w for w in table.warnings)
