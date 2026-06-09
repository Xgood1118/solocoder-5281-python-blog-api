from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    SearchResponse,
    SearchResultItem,
    SubscriptionCreate,
    SubscriptionResponse,
)
from app.services import subscription_service
from app.search import search_articles

router = APIRouter(tags=["subscriptions"])


def _get_request_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.post("/subscribe", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def subscribe(
    data: SubscriptionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        subscription = await subscription_service.subscribe(
            db, data.email, ip_address=_get_request_ip(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return subscription


@router.get("/subscriptions/confirm")
async def confirm_subscription(
    email: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    subscription = await subscription_service.confirm_subscription(
        db, email, token
    )
    if not subscription:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return {
        "success": True,
        "message": "Subscription confirmed successfully",
        "email": email,
    }


@router.post("/unsubscribe")
async def unsubscribe(
    data: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
):
    success = await subscription_service.unsubscribe(db, data.email)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"success": True, "message": "Unsubscribed successfully"}


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    items, total = await subscription_service.list_subscriptions(
        db, status=status, page=page, page_size=page_size
    )
    return items
