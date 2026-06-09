from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
    CommentUpdate,
    PendingCommentReview,
)
from app.services import comment_service
from app.services.cache_service import check_rate_limit

settings = get_settings()

router = APIRouter(prefix="/comments", tags=["comments"])


def _get_request_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _get_user_agent(request: Request) -> str:
    return request.headers.get("User-Agent", "")


@router.get("", response_model=CommentListResponse)
async def list_comments(
    article_id: Optional[int] = None,
    status: str = Query("published"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    items, total = await comment_service.list_comments(
        db,
        article_id=article_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size
    return CommentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/pending")
async def list_pending_comments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    items, total = await comment_service.list_pending_comments(
        db, page=page, page_size=page_size
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
):
    comment = await comment_service.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    article_id: int,
    comment_data: CommentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip_address = _get_request_ip(request)

    banned = await comment_service.is_ip_banned(db, ip_address)
    if banned:
        raise HTTPException(status_code=403, detail="Your IP has been banned")

    rate_ok = await check_rate_limit(
        f"rate_limit:comment:{ip_address}",
        settings.comment_rate_limit_seconds,
    )
    if not rate_ok:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please wait {settings.comment_rate_limit_seconds} seconds.",
        )

    daily_count = await comment_service.get_comment_count_by_ip(
        db, ip_address, hours=24
    )
    if daily_count >= settings.comment_ip_daily_limit:
        await comment_service.ban_ip(db, ip_address, reason="Too many comments in 24h")
        raise HTTPException(status_code=403, detail="Your IP has been temporarily banned")

    try:
        comment = await comment_service.create_comment(
            db,
            article_id=article_id,
            comment_data=comment_data,
            ip_address=ip_address,
            user_agent=_get_user_agent(request),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return comment


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    comment_data: CommentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    comment = await comment_service.update_comment(
        db, comment_id, comment_data, request_ip=_get_request_ip(request)
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    success = await comment_service.delete_comment(
        db, comment_id, request_ip=_get_request_ip(request)
    )
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")
    return None


@router.post("/{comment_id}/like")
async def like_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
):
    success = await comment_service.like_comment(db, comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"success": True}


@router.post("/{comment_id}/report")
async def report_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
):
    success = await comment_service.report_comment(db, comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"success": True}


@router.post("/pending/{pending_id}/review")
async def review_pending_comment(
    pending_id: int,
    review_data: PendingCommentReview,
    db: AsyncSession = Depends(get_db),
):
    success = await comment_service.review_pending_comment(
        db, pending_id, review_data.approved, review_data.reason
    )
    if not success:
        raise HTTPException(status_code=404, detail="Pending comment not found")
    return {"success": True}
