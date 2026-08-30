"""
Upload validation — size, extension, and magic-byte checks.

Spec requirement: never trust a file extension alone. A user (or attacker)
renaming a `.exe` to `.csv` must be rejected before any parser touches the
bytes. We only ever *read* the content bytes here — never execute, never
shell out, never eval.
"""
from __future__ import annotations

import os
import zipfile
from io import BytesIO

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".txt", ".pdf"}

# Legacy .xls (OLE2 compound file) signature.
_OLE2_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

# UTF-8/16/32 BOMs we tolerate at the start of text-ish files.
_BOMS = (
    b"\xef\xbb\xbf",          # UTF-8
    b"\xff\xfe\x00\x00",      # UTF-32 LE
    b"\x00\x00\xfe\xff",      # UTF-32 BE
    b"\xff\xfe",              # UTF-16 LE
    b"\xfe\xff",              # UTF-16 BE
)


class ValidationError(Exception):
    """Raised when an uploaded file fails size, extension, or content-signature checks."""


def _strip_bom(content: bytes) -> bytes:
    for bom in _BOMS:
        if content.startswith(bom):
            return content[len(bom):]
    return content


def _looks_like_zip_office(content: bytes) -> bool:
    """.xlsx (and other OOXML formats) are zip archives (PK\\x03\\x04 signature)."""
    if not content.startswith(b"PK\x03\x04") and not content.startswith(b"PK\x05\x06"):
        return False
    try:
        with zipfile.ZipFile(BytesIO(content)) as zf:
            names = zf.namelist()
            return any(n.startswith("xl/") for n in names) or "[Content_Types].xml" in names
    except zipfile.BadZipFile:
        return False


def _looks_like_pdf(content: bytes) -> bool:
    # PDFs must start with %PDF- per spec, but tolerate a little leading
    # whitespace some tools emit.
    return content.lstrip(b"\x00\r\n\t ").startswith(b"%PDF-")


def _looks_like_json(content: bytes) -> bool:
    stripped = _strip_bom(content).lstrip(b" \t\r\n")
    return stripped[:1] in (b"{", b"[")


def _looks_like_legacy_xls(content: bytes) -> bool:
    return content.startswith(_OLE2_SIGNATURE)


def _looks_like_binary_garbage(content: bytes) -> bool:
    """
    Heuristic for "this is not text at all" — catches renamed executables,
    images, archives, etc. that don't match any of our known signatures and
    would otherwise fall through to the permissive text/csv default.
    """
    sample = content[:4096]
    if not sample:
        return False
    if b"\x00" in sample:
        return True
    printable = sum(1 for b in sample if b in (9, 10, 13) or 32 <= b < 127 or b >= 128)
    return (printable / len(sample)) < 0.85


def _detect_signature(content: bytes) -> str:
    """Returns one of: 'pdf', 'xlsx', 'xls', 'json', 'binary', 'text' (best-effort default)."""
    if _looks_like_pdf(content):
        return "pdf"
    if _looks_like_zip_office(content):
        return "xlsx"
    if _looks_like_legacy_xls(content):
        return "xls"
    if _looks_like_json(content):
        return "json"
    if _looks_like_binary_garbage(content):
        return "binary"
    return "text"


# Which detected signatures are acceptable for a given extension. CSV/TXT
# are both "text" signatures since a sniffed CSV has no distinct magic
# bytes of its own.
_EXTENSION_COMPATIBLE_SIGNATURES: dict[str, set[str]] = {
    ".csv": {"text", "json"},   # a CSV that happens to be JSON-shaped is still text-safe to sniff
    ".txt": {"text", "json"},
    ".json": {"json"},
    ".xlsx": {"xlsx"},
    ".xls": {"xls", "xlsx"},   # tolerate a modern xlsx mistakenly saved as .xls
    ".pdf": {"pdf"},
}


def validate_upload(content: bytes, filename: str, declared_content_type: str, max_size_bytes: int) -> None:
    """
    Raises ValidationError if the upload is unsafe or malformed:
      - exceeds max_size_bytes
      - extension not in the allow-list
      - actual file signature (magic bytes) doesn't match the claimed extension

    `declared_content_type` is accepted for logging/telemetry purposes only —
    it is never trusted as the basis for a decision, since it is fully
    attacker-controlled (spec requirement: never trust extension/MIME alone).
    """
    if content is None:
        raise ValidationError("Uploaded file has no content.")

    size = len(content)
    if size > max_size_bytes:
        raise ValidationError(
            f"File exceeds maximum allowed size ({size} bytes > {max_size_bytes} bytes)."
        )
    if size == 0:
        raise ValidationError("Uploaded file is empty.")

    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File extension '{ext or '(none)'}' is not supported. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    signature = _detect_signature(content)
    compatible = _EXTENSION_COMPATIBLE_SIGNATURES.get(ext, set())
    if signature not in compatible:
        raise ValidationError(
            f"File content does not match its extension ('{filename}' claims '{ext}' but its "
            f"content signature looks like '{signature}'). This file has been rejected — "
            f"renaming a file does not change what it actually is."
        )
