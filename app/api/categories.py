from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


def _get_request_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    items, total = await category_service.list_categories(
        db, page=page, page_size=page_size
    )
    return items


@router.get("/all", response_model=list[CategoryResponse])
async def list_all_categories(
    db: AsyncSession = Depends(get_db),
):
    items = await category_service.list_all_categories(db)
    return items


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    category = await category_service.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("/slug/{slug}", response_model=CategoryResponse)
async def get_category_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    category = await category_service.get_category_by_slug(db, slug)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        category = await category_service.create_category(
            db, category_data, request_ip=_get_request_ip(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        category = await category_service.update_category(
            db, category_id, category_data, request_ip=_get_request_ip(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        success = await category_service.delete_category(
            db, category_id, request_ip=_get_request_ip(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    return None
