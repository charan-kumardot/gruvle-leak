import pytest

from app.parsers.validation import ValidationError, validate_upload


def test_valid_csv_passes():
    content = b"a,b,c\n1,2,3\n"
    validate_upload(content, "orders.csv", "text/csv", max_size_bytes=1024)


def test_valid_json_passes():
    content = b'[{"a": 1}]'
    validate_upload(content, "data.json", "application/json", max_size_bytes=1024)


def test_valid_pdf_passes():
    content = b"%PDF-1.4\n%mock pdf content"
    validate_upload(content, "invoice.pdf", "application/pdf", max_size_bytes=1024)


def test_valid_xlsx_passes():
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("xl/workbook.xml", "<workbook/>")
    validate_upload(buf.getvalue(), "book.xlsx", "application/vnd.openxmlformats", max_size_bytes=1024)


def test_rejects_oversized_file():
    content = b"a,b\n1,2\n" * 1000
    with pytest.raises(ValidationError, match="exceeds maximum"):
        validate_upload(content, "big.csv", "text/csv", max_size_bytes=10)


def test_rejects_empty_file():
    with pytest.raises(ValidationError, match="empty"):
        validate_upload(b"", "empty.csv", "text/csv", max_size_bytes=1024)


def test_rejects_disallowed_extension():
    with pytest.raises(ValidationError, match="not supported"):
        validate_upload(b"hello", "readme.md", "text/markdown", max_size_bytes=1024)


def test_rejects_exe_renamed_to_csv():
    # MZ header = Windows PE executable magic bytes.
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
    with pytest.raises(ValidationError, match="does not match its extension"):
        validate_upload(exe_bytes, "totally_a_spreadsheet.csv", "text/csv", max_size_bytes=1024)


def test_rejects_pdf_renamed_to_json():
    pdf_bytes = b"%PDF-1.7\n%fake"
    with pytest.raises(ValidationError, match="does not match its extension"):
        validate_upload(pdf_bytes, "data.json", "application/json", max_size_bytes=1024)


def test_rejects_random_zip_claiming_to_be_xlsx():
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "just a plain zip, not an office file")
    with pytest.raises(ValidationError, match="does not match its extension"):
        validate_upload(buf.getvalue(), "fake.xlsx", "application/octet-stream", max_size_bytes=1024)


def test_never_trusts_declared_content_type_alone():
    # Declared content type claims PDF, but the extension/signature checks
    # are what actually govern the decision — a text file named .csv with a
    # bogus declared_content_type must still pass.
    content = b"a,b\n1,2\n"
    validate_upload(content, "orders.csv", "application/pdf", max_size_bytes=1024)
