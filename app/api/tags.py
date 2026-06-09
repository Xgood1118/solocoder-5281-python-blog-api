from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    TagCloudItem,
    TagCreate,
    TagResponse,
    TagUpdate,
)
from app.services import tag_service

router = APIRouter(prefix="/tags", tags=["tags"])


def _get_request_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.get("", response_model=list[TagResponse])
async def list_tags(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    items, total = await tag_service.list_tags(db, page=page, page_size=page_size)
    return items


@router.get("/cloud", response_model=list[TagCloudItem])
async def get_tag_cloud(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    cloud = await tag_service.get_tag_cloud(db, limit=limit)
    return cloud


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
):
    tag = await tag_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.get("/slug/{slug}", response_model=TagResponse)
async def get_tag_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    tag = await tag_service.get_tag_by_slug(db, slug)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tag = await tag_service.create_tag(
        db, tag_data, request_ip=_get_request_ip(request)
    )
    return tag


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    tag_data: TagUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tag = await tag_service.update_tag(
        db, tag_id, tag_data, request_ip=_get_request_ip(request)
    )
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    success = await tag_service.delete_tag(
        db, tag_id, request_ip=_get_request_ip(request)
    )
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found")
    return None
