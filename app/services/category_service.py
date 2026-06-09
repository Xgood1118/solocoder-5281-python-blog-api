from __future__ import annotations

from typing import List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Article, ArticleStatus, AuditAction, Category
from app.schemas import CategoryCreate, CategoryUpdate
from app.services.audit import log_audit
from app.utils.slug import generate_slug

MAX_CATEGORY_DEPTH = 2


async def get_category(db: AsyncSession, category_id: int) -> Optional[Category]:
    result = await db.execute(
        select(Category).options(selectinload(Category.children)).where(Category.id == category_id)
    )
    return result.scalar_one_or_none()


async def get_category_by_slug(db: AsyncSession, slug: str) -> Optional[Category]:
    result = await db.execute(
        select(Category).options(selectinload(Category.children)).where(Category.slug == slug)
    )
    return result.scalar_one_or_none()


async def list_categories(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    include_children: bool = True,
) -> tuple[List[Category], int]:
    query = select(Category).where(Category.parent_id.is_(None))

    if include_children:
        query = query.options(selectinload(Category.children))

    count_query = select(func.count()).select_from(Category).where(Category.parent_id.is_(None))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Category.id).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def list_all_categories(db: AsyncSession) -> List[Category]:
    result = await db.execute(
        select(Category).options(selectinload(Category.children)).order_by(Category.id)
    )
    return list(result.scalars().all())


async def create_category(
    db: AsyncSession,
    category_data: CategoryCreate,
    user: str = "admin",
    request_ip: Optional[str] = None,
) -> Category:
    parent = None
    level = 0

    if category_data.parent_id:
        parent = await get_category(db, category_data.parent_id)
        if not parent:
            raise ValueError(f"Parent category {category_data.parent_id} not found")
        if parent.level >= MAX_CATEGORY_DEPTH - 1:
            raise ValueError(f"Maximum category depth ({MAX_CATEGORY_DEPTH}) exceeded")
        level = parent.level + 1

    slug = category_data.slug or generate_slug(category_data.name)
    slug = await _ensure_unique_slug(db, slug)

    category = Category(
        name=category_data.name,
        slug=slug,
        description=category_data.description,
        parent_id=category_data.parent_id,
        level=level,
    )

    db.add(category)
    await db.commit()

    result = await db.execute(
        select(Category)
        .options(selectinload(Category.children))
        .where(Category.id == category.id)
    )
    category = result.scalar_one()

    await log_audit(
        db,
        action=AuditAction.CREATE.value,
        resource_type="category",
        resource_id=category.id,
        user=user,
        ip_address=request_ip,
        new_value={"id": category.id, "name": category.name},
    )

    return category


async def update_category(
    db: AsyncSession,
    category_id: int,
    category_data: CategoryUpdate,
    user: str = "admin",
    request_ip: Optional[str] = None,
) -> Optional[Category]:
    category = await get_category(db, category_id)
    if not category:
        return None

    old_value = {"id": category.id, "name": category.name, "slug": category.slug}

    update_data = category_data.model_dump(exclude_unset=True)

    if "parent_id" in update_data:
        new_parent_id = update_data["parent_id"]
        if new_parent_id is None:
            update_data["level"] = 0
        else:
            if new_parent_id == category_id:
                raise ValueError("Cannot set parent to self")
            new_parent = await get_category(db, new_parent_id)
            if not new_parent:
                raise ValueError(f"Parent category {new_parent_id} not found")
            if new_parent.level >= MAX_CATEGORY_DEPTH - 1:
                raise ValueError(f"Maximum category depth ({MAX_CATEGORY_DEPTH}) exceeded")
            update_data["level"] = new_parent.level + 1

    if "name" in update_data and "slug" not in update_data:
        update_data["slug"] = generate_slug(update_data["name"])

    if "slug" in update_data:
        update_data["slug"] = await _ensure_unique_slug(
            db, update_data["slug"], category_id
        )

    for key, value in update_data.items():
        setattr(category, key, value)

    await db.commit()

    result = await db.execute(
        select(Category)
        .options(selectinload(Category.children))
        .where(Category.id == category.id)
    )
    category = result.scalar_one()

    await log_audit(
        db,
        action=AuditAction.UPDATE.value,
        resource_type="category",
        resource_id=category.id,
        user=user,
        ip_address=request_ip,
        old_value=old_value,
        new_value={"name": category.name, "slug": category.slug},
    )

    return category


async def delete_category(
    db: AsyncSession,
    category_id: int,
    user: str = "admin",
    request_ip: Optional[str] = None,
) -> bool:
    category = await get_category(db, category_id)
    if not category:
        return False

    child_count = await db.execute(
        select(func.count()).where(Category.parent_id == category_id)
    )
    if child_count.scalar_one() > 0:
        raise ValueError("Cannot delete category with children")

    old_value = {"id": category.id, "name": category.name}

    await db.delete(category)
    await db.commit()

    await log_audit(
        db,
        action=AuditAction.DELETE.value,
        resource_type="category",
        resource_id=category_id,
        user=user,
        ip_address=request_ip,
        old_value=old_value,
    )

    return True


async def get_category_article_count(
    db: AsyncSession, category_id: int
) -> int:
    result = await db.execute(
        select(func.count(Article.id)).where(
            and_(
                Article.category_id == category_id,
                Article.status == ArticleStatus.PUBLISHED.value,
            )
        )
    )
    return result.scalar_one()


async def _ensure_unique_slug(
    db: AsyncSession, slug: str, exclude_id: Optional[int] = None
) -> str:
    base_slug = slug
    counter = 1

    while True:
        current_slug = base_slug if counter == 1 else f"{base_slug}-{counter}"
        query = select(Category).where(Category.slug == current_slug)

        if exclude_id is not None:
            query = query.where(Category.id != exclude_id)

        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if not existing:
            return current_slug

        counter += 1
