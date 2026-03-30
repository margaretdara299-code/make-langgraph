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


def serialize_to_json(value) -> str:
    """Serialize a value to a compact JSON string. Handles list/dict/None correctly."""
    if value is None:
        return '{}'
    if isinstance(value, list) and not value:
        return '[]'
    if isinstance(value, dict) and not value:
        return '{}'
    return json.dumps(value, separators=(',', ':'))


def deserialize_json(value, default=None):
    """Deserialize a JSON string. Returns default on failure."""
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def compute_sha256_hash(text: str) -> str:
    """SHA-256 hash of a given string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
