import json
from pathlib import Path

from app.parsers import json_parser

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_top_level_array_of_objects():
    content = (FIXTURES / "orders.json").read_bytes()
    table = json_parser.parse(content, "orders.json")
    assert set(table.columns) == {"order_id", "customer_name", "total"}
    assert len(table.rows) == 6
    assert table.rows[0]["customer_name"] == "Acme Corp"


def test_object_with_single_array_valued_key_is_autodetected():
    content = json.dumps({
        "meta": {"exported_at": "2026-01-01"},
        "orders": [{"order_id": 1}, {"order_id": 2}],
    }).encode()
    # "meta" is object-valued (not array), "orders" is the sole array key.
    table = json_parser.parse(content, "wrapped.json")
    assert table.columns == ["order_id"]
    assert len(table.rows) == 2
    assert any("orders" in w for w in table.warnings)


def test_ndjson_parsed_line_by_line():
    content = b'{"order_id": 1}\n{"order_id": 2}\n{"order_id": 3}\n'
    table = json_parser.parse(content, "orders.ndjson.json")
    assert len(table.rows) == 3
    assert any("newline-delimited" in w for w in table.warnings)


def test_one_level_nested_object_is_flattened():
    content = json.dumps([{"order_id": 1, "customer": {"id": 5, "name": "Acme"}}]).encode()
    table = json_parser.parse(content, "nested.json")
    assert "customer.id" in table.columns
    assert "customer.name" in table.columns
    assert table.rows[0]["customer.id"] == 5
    assert table.rows[0]["customer.name"] == "Acme"


def test_array_of_objects_field_is_stringified_with_warning():
    content = json.dumps([{
        "order_id": 1,
        "line_items": [{"sku": "A"}, {"sku": "B"}],
    }]).encode()
    table = json_parser.parse(content, "line_items.json")
    assert isinstance(table.rows[0]["line_items"], str)
    assert "sku" in table.rows[0]["line_items"]
    assert any("line_items" in w and "JSON-stringified" in w for w in table.warnings)


def test_array_of_primitives_left_as_is():
    content = json.dumps([{"order_id": 1, "tags": ["a", "b", "c"]}]).encode()
    table = json_parser.parse(content, "tags.json")
    assert table.rows[0]["tags"] == ["a", "b", "c"]


def test_malformed_json_returns_warning_not_crash():
    table = json_parser.parse(b"{not valid json", "broken.json")
    assert table.rows == []
    assert table.warnings


def test_empty_file_returns_warning():
    table = json_parser.parse(b"", "empty.json")
    assert table.rows == []
    assert table.warnings
