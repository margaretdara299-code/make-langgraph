from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response
from app.category.models import CreateCategoryRequest, UpdateCategoryRequest
from app.category import service

router = APIRouter(prefix="/categories", tags=["Category"])

@router.get("")
def list_categories(db: Session = Depends(get_db_session)):
    return build_success_response("Categories fetched", service.list_categories(db))

@router.post("", status_code=201)
def create_category(request: CreateCategoryRequest, db: Session = Depends(get_db_session)):
    return build_success_response("Category created", service.create_category(db, request))

@router.get("/{category_id}")
def get_category(category_id: int, db: Session = Depends(get_db_session)):
    return build_success_response("Category fetched", service.get_category(db, category_id))

@router.patch("/{category_id}")
def update_category(category_id: int, request: UpdateCategoryRequest, db: Session = Depends(get_db_session)):
    return build_success_response("Category updated", service.update_category(db, category_id, request))

@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db_session)):
    service.delete_category(db, category_id)
    return build_success_response("Category deleted")
