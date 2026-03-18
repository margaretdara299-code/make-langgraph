from sqlalchemy.orm import Session
from app.capability import repository
from app.capability.models import CreateCapabilityRequest, UpdateCapabilityRequest, CapabilityResponse
from app.common.response import raise_bad_request, raise_not_found

def list_capabilities(db: Session):
    return repository.list_capabilities(db)

def get_capability(db: Session, capability_id: int):
    cap = repository.get_capability(db, capability_id)
    if not cap:
        raise_not_found("Capability not found")
    return cap

def create_capability(db: Session, request: CreateCapabilityRequest):
    return repository.create_capability(db, request.name, request.description)

def update_capability(db: Session, capability_id: int, request: UpdateCapabilityRequest):
    cap = repository.update_capability(db, capability_id, request.name, request.description)
    if not cap:
        raise_not_found("Capability not found")
    return cap

def delete_capability(db: Session, capability_id: int):
    if not repository.get_capability(db, capability_id):
        raise_not_found("Capability not found")
        
    if not repository.can_delete_capability(db, capability_id):
        raise_bad_request("Capability is referenced by one or more actions and cannot be deleted")
        
    repository.delete_capability(db, capability_id)
