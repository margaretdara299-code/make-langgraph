"""
Response helpers — standard API envelope for all endpoints.

Success: {"status": True, "message": "...", "data": ...}
Error:   {"status": False, "message": "...", "data": None}
"""
from typing import Any, Optional
from fastapi import HTTPException
from fastapi.responses import JSONResponse


# =========================================================================
# Success helpers
# =========================================================================
def ok(data: Any = None, message: str = "Success") -> dict:
    """Return a success envelope."""
    return {"status": True, "message": message, "data": data}


# =========================================================================
# Error helpers — all raise HTTPException with envelope body
# =========================================================================
def _raise(message: str, http_status: int) -> None:
    raise HTTPException(
        status_code=http_status,
        detail={"status": False, "message": message, "data": None},
    )


def bad_request(message: str = "Invalid request") -> None:
    _raise(message, 400)


def not_found(message: str = "Not found") -> None:
    _raise(message, 404)


def conflict(message: str = "Conflict") -> None:
    _raise(message, 409)


def internal_error(message: str = "Internal error") -> None:
    _raise(message, 500)
