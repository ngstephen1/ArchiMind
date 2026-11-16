"""Canonical JSON bytes and digests so identical content always hashes identically.

Rules: UTF-8, sorted keys, no insignificant whitespace, LF-only JSONL, floats rounded
to ``FLOAT_DECIMALS`` places with negative zero folded to zero, and no NaN/Infinity.
Rounding absorbs last-bit differences between platforms and NumPy builds.
"""

import hashlib
import json
import math
import os
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path

from pydantic import BaseModel

FLOAT_DECIMALS = 9
MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_JSONL_LINE_BYTES = 4 * 1024 * 1024


class CanonicalError(ValueError):
    """Content cannot be represented canonically or is not strict JSON."""


def _canonical(value):
    if isinstance(value, BaseModel):
        return _canonical(value.model_dump(mode="json"))
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalError("Non-finite float")
        rounded = round(value, FLOAT_DECIMALS)
        return 0.0 if rounded == 0 else rounded
    if isinstance(value, Mapping):
        if not all(isinstance(k, str) for k in value):
            raise CanonicalError("JSON object keys must be strings")
        return {k: _canonical(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_canonical(v) for v in value]
    raise CanonicalError(f"Unsupported type {type(value).__name__}")


def canonical_bytes(value) -> bytes:
    """Serialize ``value`` to canonical UTF-8 JSON bytes."""
    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(value) -> str:
    """SHA-256 of the canonical bytes of ``value``."""
    return sha256_hex(canonical_bytes(value))


def file_sha256(path: Path, *, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        while block := handle.read(chunk):
            h.update(block)
    return h.hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(name):
    raise CanonicalError(f"Non-standard JSON constant {name}")


def strict_loads(data: str | bytes, *, max_bytes: int = MAX_JSON_BYTES):
    """Parse JSON rejecting duplicate keys, NaN/Infinity and oversized input."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    if len(raw) > max_bytes:
        raise CanonicalError("JSON exceeds size limit")
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except CanonicalError:
        raise
    except (ValueError, UnicodeDecodeError) as error:
        raise CanonicalError("Invalid JSON") from error


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write via a sibling temporary file and rename, so readers never see partials."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.partial")
    with open(tmp, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    replace_with_retry(tmp, path)


def replace_with_retry(src: Path, dest: Path, *, attempts: int = 8, sleep=None) -> None:
    """``os.replace`` that tolerates brief Windows sharing violations.

    On Windows a scanner or indexer can hold a just-written file for a few
    milliseconds, and the rename then fails with ``PermissionError``. The retry is
    bounded (about 1.3 s in total). The last error is raised unchanged.
    """
    import time

    sleep = time.sleep if sleep is None else sleep
    for attempt in range(attempts):
        try:
            os.replace(src, dest)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            sleep(0.01 * 2**attempt)


def write_jsonl(path: Path, records: Iterable) -> tuple[str, int]:
    """Write one canonical record per LF-terminated line; return (sha256, count)."""
    lines = [canonical_bytes(record) + b"\n" for record in records]
    data = b"".join(lines)
    atomic_write_bytes(path, data)
    return sha256_hex(data), len(lines)


def iter_jsonl(
    path: Path,
    *,
    max_line_bytes: int = MAX_JSONL_LINE_BYTES,
    max_records: int = 1_000_000,
) -> Iterator:
    """Yield strictly parsed records with per-line and record-count bounds."""
    with open(path, "rb") as handle:
        count = 0
        while True:
            line = handle.readline(max_line_bytes + 1)
            if not line:
                return
            if len(line) > max_line_bytes:
                raise CanonicalError("JSONL line exceeds size limit")
            if line.endswith(b"\r\n"):
                raise CanonicalError("JSONL must use LF line endings")
            if not line.strip():
                continue
            count += 1
            if count > max_records:
                raise CanonicalError("JSONL exceeds record limit")
            yield strict_loads(line, max_bytes=max_line_bytes)
