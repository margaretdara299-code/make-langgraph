"""
General-purpose utility functions shared across the application.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any


def generate_utc_timestamp() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_unique_id(prefix: str = "") -> str:
    """Generate a standard UUID4 string. (Prefix is ignored for UUID compliance)."""
    return str(uuid.uuid4())


def serialise_json(data: Any) -> str:
    """Compact JSON serialisation (no extra whitespace)."""
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def deserialise_json(text: str | None, fallback: Any) -> Any:
    """Safe JSON deserialisation with a fallback value on failure."""
    if not text:
        return fallback
    try:
        return json.loads(text)
    except Exception:
        return fallback


def compute_sha256_hash(text: str) -> str:
    """SHA-256 hash of a given string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
