"""
HTTP Response Helpers — standard API envelope for all endpoints.

Success envelope: {"status": True, "message": "...", "data": ...}
Error envelope:   {"status": False, "message": "...", "data": None}
"""
from __future__ import annotations

from typing import Any, NoReturn

from fastapi import HTTPException


# =========================================================================
# Success Response Builder
# =========================================================================
def build_success_response(message: str = "Success", data: Any = None) -> dict:
    """Build a standard success envelope."""
    return {"status": True, "message": message, "data": data}


# =========================================================================
# Exception Raisers — all raise HTTPException with envelope body
# =========================================================================
def _raise_http(message: str, http_status: int) -> NoReturn:
    raise HTTPException(
        status_code=http_status,
        detail={"status": False, "message": message, "data": None},
    )


def raise_bad_request(message: str = "Invalid request") -> NoReturn:
    """Raise HTTP 400 with error envelope."""
    _raise_http(message, 400)


def raise_not_found(message: str = "Not found") -> NoReturn:
    """Raise HTTP 404 with error envelope."""
    _raise_http(message, 404)


def raise_conflict(message: str = "Conflict") -> NoReturn:
    """Raise HTTP 409 with error envelope."""
    _raise_http(message, 409)


def raise_internal_server_error(message: str = "Internal error") -> NoReturn:
    """Raise HTTP 500 with error envelope."""
    _raise_http(message, 500)
