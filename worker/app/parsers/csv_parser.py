"""
CSV parsing via pandas, hardened against the messy files real customers
upload: BOM markers, unusual delimiters, quoted fields, trailing blank
rows/columns, and mixed-type columns. Large files are streamed in chunks so
memory stays bounded and roughly predictable regardless of file size.
"""
from __future__ import annotations

import csv
import io

import pandas as pd

from app.parsers._common import dataframe_to_table
from app.parsers.base import ParsedTable

# Above this size we read in chunks rather than materializing the whole
# CSV as text/DataFrame in one shot.
_CHUNK_THRESHOLD_BYTES = 5 * 1024 * 1024
_CHUNK_ROWS = 50_000

# Candidate delimiters tried if csv.Sniffer can't confidently pick one.
_FALLBACK_DELIMITERS = [",", ";", "\t", "|"]


def _decode(content: bytes) -> tuple[str, list[str]]:
    """Decode bytes to text, stripping BOM. Returns (text, warnings)."""
    warnings: list[str] = []
    if content.startswith(b"\xef\xbb\xbf"):
        warnings.append("File began with a UTF-8 byte-order mark (BOM); it was stripped.")
        text = content[3:].decode("utf-8", errors="replace")
    else:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            warnings.append("File was not valid UTF-8; decoded as latin-1 with best effort.")
            text = content.decode("latin-1", errors="replace")
    return text, warnings


def _sniff_delimiter(sample: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter, warnings
    except csv.Error:
        pass

    # Fall back: pick whichever candidate delimiter appears most consistently
    # across the first few non-blank lines.
    lines = [ln for ln in sample.splitlines() if ln.strip()][:20]
    best_delim, best_score = ",", -1
    for delim in _FALLBACK_DELIMITERS:
        counts = [ln.count(delim) for ln in lines]
        if not counts or max(counts) == 0:
            continue
        # Consistency = how many lines share the modal count (and it's > 0).
        modal = max(set(counts), key=counts.count)
        if modal == 0:
            continue
        score = counts.count(modal)
        if score > best_score:
            best_delim, best_score = delim, score
    warnings.append(f"Could not confidently detect delimiter; falling back to '{best_delim}'.")
    return best_delim, warnings


def parse(content: bytes, filename: str) -> ParsedTable:
    warnings: list[str] = []

    if not content or not content.strip():
        return ParsedTable(columns=[], rows=[], warnings=["File is empty."])

    text, decode_warnings = _decode(content)
    warnings.extend(decode_warnings)

    if not text.strip():
        return ParsedTable(columns=[], rows=[], warnings=warnings + ["File contains no data after decoding."])

    sample = "\n".join(text.splitlines()[:50])
    delimiter, sniff_warnings = _sniff_delimiter(sample)
    warnings.extend(sniff_warnings)

    buf = io.StringIO(text)

    try:
        if len(content) > _CHUNK_THRESHOLD_BYTES:
            chunks = []
            reader = pd.read_csv(
                buf,
                sep=delimiter,
                engine="python",
                dtype=object,
                keep_default_na=True,
                chunksize=_CHUNK_ROWS,
                on_bad_lines="warn",
            )
            for chunk in reader:
                chunks.append(chunk)
            if not chunks:
                return ParsedTable(columns=[], rows=[], warnings=warnings + ["No rows could be parsed from file."])
            df = pd.concat(chunks, ignore_index=True)
            warnings.append(
                f"Large file ({len(content)} bytes) was read in chunks of {_CHUNK_ROWS} rows to bound memory usage."
            )
        else:
            df = pd.read_csv(
                buf,
                sep=delimiter,
                engine="python",
                dtype=object,
                keep_default_na=True,
                on_bad_lines="warn",
            )
    except pd.errors.EmptyDataError:
        return ParsedTable(columns=[], rows=[], warnings=warnings + ["File has no columns/data to parse."])
    except Exception as e:  # noqa: BLE001 - parser must never crash the caller
        return ParsedTable(columns=[], rows=[], warnings=warnings + [f"Failed to parse CSV: {e}"])

    return dataframe_to_table(df, warnings)
