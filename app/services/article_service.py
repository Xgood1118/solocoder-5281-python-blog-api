from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Article,
    ArticleStatus,
    AuditAction,
    Category,
    PendingComment,
    Tag,
)
from app.schemas import ArticleCreate, ArticleUpdate
from app.services.audit import log_audit
from app.utils.slug import generate_slug


async def get_article(
    db: AsyncSession, article_id: int
) -> Optional[Article]:
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.category))
        .where(Article.id == article_id)
    )
    return result.scalar_one_or_none()


async def get_article_by_slug(
    db: AsyncSession, slug: str
) -> Optional[Article]:
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.category))
        .where(Article.slug == slug)
    )
    return result.scalar_one_or_none()


async def list_articles(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    status: Optional[str] = None,
    category_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    search: Optional[str] = None,
) -> Tuple[List[Article], int]:
    query = select(Article).options(
        selectinload(Article.tags), selectinload(Article.category)
    )

    conditions = []
    if status:
        conditions.append(Article.status == status)
    if category_id:
        conditions.append(Article.category_id == category_id)
    if search:
        conditions.append(Article.title.ilike(f"%{search}%"))

    if conditions:
        query = query.where(and_(*conditions))

    if tag_id:
        query = query.join(Article.tags).where(Tag.id == tag_id)

    count_query = select(func.count()).select_from(Article)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    if tag_id:
        count_query = count_query.join(Article.tags).where(Tag.id == tag_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(
            desc(Article.published_at), desc(Article.created_at)
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def create_article(
    db: AsyncSession, article_data: ArticleCreate, user: str = "admin",
    request_ip: Optional[str] = None,
) -> Article:
    slug = article_data.slug or generate_slug(article_data.title)

    slug = await _ensure_unique_slug(db, slug, article_data.category_id)

    article = Article(
        title=article_data.title,
        slug=slug,
        summary=article_data.summary,
        content=article_data.content,
        cover_image=article_data.cover_image,
        status=article_data.status or ArticleStatus.DRAFT.value,
        author=article_data.author or user,
        category_id=article_data.category_id,
        seo_title=article_data.seo_title,
        seo_description=article_data.seo_description,
        og_image=article_data.og_image,
    )

    if article_data.tag_ids:
        tags = await _get_tags_by_ids(db, article_data.tag_ids)
        article.tags = tags

    if article.status == ArticleStatus.PUBLISHED.value and not article.published_at:
        article.published_at = datetime.utcnow()

    db.add(article)
    await db.commit()

    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.category))
        .where(Article.id == article.id)
    )
    article = result.scalar_one()

    await log_audit(
        db,
        action=AuditAction.CREATE.value,
        resource_type="article",
        resource_id=article.id,
        user=user,
        ip_address=request_ip,
        new_value={"id": article.id, "title": article.title, "slug": article.slug},
    )

    return article


async def update_article(
    db: AsyncSession,
    article_id: int,
    article_data: ArticleUpdate,
    user: str = "admin",
    request_ip: Optional[str] = None,
) -> Optional[Article]:
    article = await get_article(db, article_id)
    if not article:
        return None

    old_value = {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "status": article.status,
    }

    update_data = article_data.model_dump(exclude_unset=True)

    if "tag_ids" in update_data:
        tag_ids = update_data.pop("tag_ids")
        tags = await _get_tags_by_ids(db, tag_ids)
        article.tags = tags

    if "title" in update_data and "slug" not in update_data:
        update_data["slug"] = generate_slug(update_data["title"])

    if "slug" in update_data or "category_id" in update_data:
        new_slug = update_data.get("slug", article.slug)
        new_category_id = update_data.get("category_id", article.category_id)
        update_data["slug"] = await _ensure_unique_slug(
            db, new_slug, new_category_id, article.id
        )

    for key, value in update_data.items():
        setattr(article, key, value)

    if (
        article.status == ArticleStatus.PUBLISHED.value
        and not article.published_at
    ):
        article.published_at = datetime.utcnow()

    article.updated_at = datetime.utcnow()

    await db.commit()

    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.category))
        .where(Article.id == article.id)
    )
    article = result.scalar_one()

    await log_audit(
        db,
        action=AuditAction.UPDATE.value,
        resource_type="article",
        resource_id=article.id,
        user=user,
        ip_address=request_ip,
        old_value=old_value,
        new_value={"title": article.title, "slug": article.slug, "status": article.status},
    )

    return article


async def delete_article(
    db: AsyncSession,
    article_id: int,
    user: str = "admin",
    request_ip: Optional[str] = None,
) -> bool:
    article = await get_article(db, article_id)
    if not article:
        return False

    old_value = {"id": article.id, "title": article.title, "slug": article.slug}

    await db.delete(article)
    await db.commit()

    await log_audit(
        db,
        action=AuditAction.DELETE.value,
        resource_type="article",
        resource_id=article_id,
        user=user,
        ip_address=request_ip,
        old_value=old_value,
    )

    return True


async def increment_views(db: AsyncSession, article_id: int) -> None:
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if article:
        article.views += 1
        await db.commit()


async def increment_likes(db: AsyncSession, article_id: int) -> bool:
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        return False
    article.likes += 1
    await db.commit()
    return True


async def get_hot_articles(
    db: AsyncSession, limit: int = 10
) -> List[Article]:
    result = await db.execute(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED.value)
        .order_by(desc(Article.views), desc(Article.likes))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_archives_by_month(
    db: AsyncSession,
) -> List[dict]:
    result = await db.execute(
        select(
            func.strftime("%Y-%m", Article.published_at).label("month"),
            func.count(Article.id).label("count"),
        )
        .where(
            and_(
                Article.status == ArticleStatus.PUBLISHED.value,
                Article.published_at.isnot(None),
            )
        )
        .group_by("month")
        .order_by(desc("month"))
    )
    return [
        {"date": row.month, "count": row.count}
        for row in result.all()
    ]


async def _get_tags_by_ids(db: AsyncSession, tag_ids: List[int]) -> List[Tag]:
    if not tag_ids:
        return []
    result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
    return list(result.scalars().all())


async def _ensure_unique_slug(
    db: AsyncSession,
    slug: str,
    category_id: Optional[int],
    exclude_id: Optional[int] = None,
) -> str:
    base_slug = slug
    counter = 1

    while True:
        current_slug = base_slug if counter == 1 else f"{base_slug}-{counter}"
        query = select(Article).where(Article.slug == current_slug)

        if category_id is not None:
            query = query.where(Article.category_id == category_id)

        if exclude_id is not None:
            query = query.where(Article.id != exclude_id)

        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if not existing:
            return current_slug

        counter += 1
