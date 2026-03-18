from pydantic import BaseModel

class CreateCategoryRequest(BaseModel):
    name: str
    description: str | None = None

class UpdateCategoryRequest(BaseModel):
    name: str | None = None
    description: str | None = None

class CategoryResponse(BaseModel):
    category_id: int
    name: str
    description: str | None = None
