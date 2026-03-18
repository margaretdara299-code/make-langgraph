from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response
from app.capability.models import CreateCapabilityRequest, UpdateCapabilityRequest
from app.capability import service

router = APIRouter(prefix="/api/v1", tags=["Capability"])

@router.get("/capabilities")
def list_capabilities(db: Session = Depends(get_db_session)):
    return build_success_response("Capabilities fetched", service.list_capabilities(db))

@router.post("/capabilities", status_code=201)
def create_capability(request: CreateCapabilityRequest, db: Session = Depends(get_db_session)):
    return build_success_response("Capability created", service.create_capability(db, request))

@router.get("/capabilities/{capability_id}")
def get_capability(capability_id: int, db: Session = Depends(get_db_session)):
    return build_success_response("Capability fetched", service.get_capability(db, capability_id))

@router.patch("/capabilities/{capability_id}")
def update_capability(capability_id: int, request: UpdateCapabilityRequest, db: Session = Depends(get_db_session)):
    return build_success_response("Capability updated", service.update_capability(db, capability_id, request))

@router.delete("/capabilities/{capability_id}")
def delete_capability(capability_id: int, db: Session = Depends(get_db_session)):
    service.delete_capability(db, capability_id)
    return build_success_response("Capability deleted")
