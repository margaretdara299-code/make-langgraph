"""
Claims Module — Dummy API for simulating external claim operations.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.common.response import build_success_response, raise_not_found

router = APIRouter(prefix="/claims", tags=["Dummy Claims API"])

# 🔥 In-memory dummy data
claims_db = [
    {
        "claim_id": "C001",
        "mrn": "MRN001",
        "patient_name": "John Doe",
        "dos": "2026-03-01",
        "facility": "City Hospital",
        "primary_payer": "Aetna",
        "rendering_provider": "Dr. Smith",
        "referring_provider": "Dr. Adams",
        "total_billed": 1000.0,
        "total_allowed": 800.0,
        "total_paid_ins": 600.0,
        "total_paid_pat": 100.0,
        "total_balance": 300.0,
        "status": "Pending"
    },
    {
        "claim_id": "C002",
        "mrn": "MRN002",
        "patient_name": "Jane Doe",
        "dos": "2026-03-02",
        "facility": "Metro Clinic",
        "primary_payer": "BlueCross",
        "rendering_provider": "Dr. Lee",
        "referring_provider": "Dr. Brown",
        "total_billed": 2000.0,
        "total_allowed": 1500.0,
        "total_paid_ins": 1200.0,
        "total_paid_pat": 200.0,
        "total_balance": 600.0,
        "status": "Paid"
    }
]


@router.get("")
def get_claims(status: str | None = None):
    """Return all dummy claims, optionally filtered by status."""
    items = claims_db
    if status:
        items = [c for c in claims_db if c.get("status", "").lower() == status.lower()]
    
    return build_success_response("Claims fetched", {"items": items, "total": len(items)})


@router.get("/status/{status}")
def get_claims_by_status(status: str):
    """Fetch all claims that match a specific status (path-based)."""
    items = [c for c in claims_db if c.get("status", "").lower() == status.lower()]
    return build_success_response(f"Claims with status '{status}' fetched", {"items": items, "total": len(items)})


@router.get("/{claim_id}")
def get_claim(claim_id: str):
    """Fetch a single claim by its ID."""
    for claim in claims_db:
        if claim["claim_id"] == claim_id:
            return build_success_response("Claim found", claim)
    raise_not_found(f"Claim '{claim_id}' not found")


@router.post("")
def create_claim(claim: Dict[str, Any]):
    """Simulate creating a new claim."""
    claims_db.append(claim)
    return build_success_response("Claim added", claim)


@router.put("/{claim_id}")
def update_claim(claim_id: str, updated_claim: Dict[str, Any]):
    """Simulate updating an existing claim."""
    for i, claim in enumerate(claims_db):
        if claim["claim_id"] == claim_id:
            claims_db[i].update(updated_claim)
            return build_success_response("Claim updated", claims_db[i])
    raise_not_found(f"Claim '{claim_id}' not found")


@router.delete("/{claim_id}")
def delete_claim(claim_id: str):
    """Simulate deleting a claim."""
    for i, claim in enumerate(claims_db):
        if claim["claim_id"] == claim_id:
            deleted = claims_db.pop(i)
            return build_success_response("Claim deleted", deleted)
    raise_not_found(f"Claim '{claim_id}' not found")
