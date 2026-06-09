from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SearchResponse, SearchResultItem
from app.search import search_articles

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tags: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    filter_tags = None
    if tags:
        filter_tags = [t.strip() for t in tags.split(",") if t.strip()]

    items, total, processing_time = search_articles(
        q, page=page, page_size=page_size, filter_tags=filter_tags
    )

    result_items = []
    for item in items:
        published_at = item.get("published_at")
        if published_at and isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at)
            except (ValueError, TypeError):
                published_at = None

        result_items.append(
            SearchResultItem(
                id=int(item.get("id", 0)),
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                slug=item.get("slug", ""),
                tags=item.get("tags", []),
                published_at=published_at,
            )
        )

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return SearchResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        processing_time_ms=processing_time,
    )
