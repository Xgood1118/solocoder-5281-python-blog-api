from __future__ import annotations

from typing import List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Article, ArticleStatus, AuditAction, Tag, article_tags
from app.schemas import TagCreate, TagUpdate
from app.services.audit import log_audit
from app.utils.slug import generate_slug


async def get_tag(db: AsyncSession, tag_id: int) -> Optional[Tag]:
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    return result.scalar_one_or_none()


async def get_tag_by_slug(db: AsyncSession, slug: str) -> Optional[Tag]:
    result = await db.execute(select(Tag).where(Tag.slug == slug))
    return result.scalar_one_or_none()


async def list_tags(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    include_count: bool = False,
) -> tuple[List[Tag], int]:
    query = select(Tag)
    count_query = select(func.count()).select_from(Tag)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(desc(Tag.created_at)).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def get_tag_cloud(db: AsyncSession, limit: int = 50) -> List[dict]:
    result = await db.execute(
        select(
            Tag.id,
            Tag.name,
            Tag.slug,
            func.count(article_tags.c.article_id).label("article_count"),
        )
        .outerjoin(article_tags, article_tags.c.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(desc("article_count"))
        .limit(limit)
    )
    return [
        {
            "id": row.id,
            "name": row.name,
            "slug": row.slug,
            "article_count": row.article_count,
        }
        for row in result.all()
    ]


async def create_tag(
    db: AsyncSession,
    tag_data: TagCreate,
    user: str = "admin",
    request_ip: Optional[str] = None,
) -> Tag:
    slug = tag_data.slug or generate_slug(tag_data.name)
    slug = await _ensure_unique_slug(db, slug)

    tag = Tag(
        name=tag_data.name,
        slug=slug,
        description=tag_data.description,
    )

    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    await log_audit(
        db,
        action=AuditAction.CREATE.value,
        resource_type="tag",
        resource_id=tag.id,
        user=user,
        ip_address=request_ip,
        new_value={"id": tag.id, "name": tag.name},
    )

    return tag


async def update_tag(
    db: AsyncSession,
    tag_id: int,
    tag_data: TagUpdate,
    user: str = "admin",
    request_ip: Optional[str] = None,
) -> Optional[Tag]:
    tag = await get_tag(db, tag_id)
    if not tag:
        return None

    old_value = {"id": tag.id, "name": tag.name, "slug": tag.slug}

    update_data = tag_data.model_dump(exclude_unset=True)

    if "name" in update_data and "slug" not in update_data:
        update_data["slug"] = generate_slug(update_data["name"])

    if "slug" in update_data:
        update_data["slug"] = await _ensure_unique_slug(
            db, update_data["slug"], tag_id
        )

    for key, value in update_data.items():
        setattr(tag, key, value)

    await db.commit()
    await db.refresh(tag)

    await log_audit(
        db,
        action=AuditAction.UPDATE.value,
        resource_type="tag",
        resource_id=tag.id,
        user=user,
        ip_address=request_ip,
        old_value=old_value,
        new_value={"name": tag.name, "slug": tag.slug},
    )

    return tag


async def delete_tag(
    db: AsyncSession,
    tag_id: int,
    user: str = "admin",
    request_ip: Optional[str] = None,
) -> bool:
    tag = await get_tag(db, tag_id)
    if not tag:
        return False

    old_value = {"id": tag.id, "name": tag.name}

    await db.delete(tag)
    await db.commit()

    await log_audit(
        db,
        action=AuditAction.DELETE.value,
        resource_type="tag",
        resource_id=tag_id,
        user=user,
        ip_address=request_ip,
        old_value=old_value,
    )

    return True


async def _ensure_unique_slug(
    db: AsyncSession, slug: str, exclude_id: Optional[int] = None
) -> str:
    base_slug = slug
    counter = 1

    while True:
        current_slug = base_slug if counter == 1 else f"{base_slug}-{counter}"
        query = select(Tag).where(Tag.slug == current_slug)

        if exclude_id is not None:
            query = query.where(Tag.id != exclude_id)

        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if not existing:
            return current_slug

        counter += 1
