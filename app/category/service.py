from sqlalchemy.orm import Session
from app.category import repository
from app.category.models import CreateCategoryRequest, UpdateCategoryRequest, CategoryResponse
from app.common.response import raise_bad_request, raise_not_found

def list_categories(db: Session):
    return repository.list_categories(db)

def get_category(db: Session, category_id: int):
    cat = repository.get_category(db, category_id)
    if not cat:
        raise_not_found("Category not found")
    return cat

def create_category(db: Session, request: CreateCategoryRequest):
    return repository.create_category(db, request.name, request.description)

def update_category(db: Session, category_id: int, request: UpdateCategoryRequest):
    cat = repository.update_category(db, category_id, request.name, request.description)
    if not cat:
        raise_not_found("Category not found")
    return cat

def delete_category(db: Session, category_id: int):
    if not repository.get_category(db, category_id):
        raise_not_found("Category not found")
        
    if not repository.can_delete_category(db, category_id):
        raise_bad_request("Category is referenced by one or more actions/skills and cannot be deleted")
        
    repository.delete_category(db, category_id)
