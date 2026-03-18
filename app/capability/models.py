from pydantic import BaseModel

class CreateCapabilityRequest(BaseModel):
    name: str
    description: str | None = None

class UpdateCapabilityRequest(BaseModel):
    name: str | None = None
    description: str | None = None

class CapabilityResponse(BaseModel):
    capability_id: int
    name: str
    description: str | None = None
