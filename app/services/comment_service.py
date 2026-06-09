from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models import (
    Article,
    Comment,
    CommentStatus,
    IPBlacklist,
    PendingComment,
)
from app.schemas import CommentCreate, CommentUpdate
from app.services.antispam import is_suspicious
from app.services.audit import log_audit

settings = get_settings()

MAX_COMMENT_DEPTH = 3


async def get_comment(db: AsyncSession, comment_id: int) -> Optional[Comment]:
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.children))
        .where(Comment.id == comment_id)
    )
    return result.scalar_one_or_none()


async def list_comments(
    db: AsyncSession,
    article_id: Optional[int] = None,
    status: str = CommentStatus.PUBLISHED.value,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Comment], int]:
    query = select(Comment).where(Comment.parent_id.is_(None))

    conditions = []
    if status:
        conditions.append(Comment.status == status)
    if article_id:
        conditions.append(Comment.article_id == article_id)

    if conditions:
        query = query.where(and_(*conditions))

    count_query = select(func.count()).select_from(Comment).where(Comment.parent_id.is_(None))
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.options(selectinload(Comment.children))
        .order_by(desc(Comment.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def create_comment(
    db: AsyncSession,
    article_id: int,
    comment_data: CommentCreate,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Comment:
    article_result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = article_result.scalar_one_or_none()
    if not article:
        raise ValueError(f"Article {article_id} not found")

    parent = None
    path = ""
    depth = 0

    if comment_data.parent_id:
        parent = await get_comment(db, comment_data.parent_id)
        if not parent:
            raise ValueError(f"Parent comment {comment_data.parent_id} not found")
        if parent.depth >= MAX_COMMENT_DEPTH - 1:
            raise ValueError(f"Maximum comment depth ({MAX_COMMENT_DEPTH}) exceeded")
        depth = parent.depth + 1
        path = f"{parent.path}/{parent.id}"

    suspicious, reason = is_suspicious(comment_data.content, ip_address or "")

    status = CommentStatus.PENDING.value if suspicious else CommentStatus.PUBLISHED.value

    comment = Comment(
        article_id=article_id,
        parent_id=comment_data.parent_id,
        path=path,
        depth=depth,
        author=comment_data.author,
        email=comment_data.email,
        website=comment_data.website,
        content=comment_data.content,
        status=status,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(comment)
    await db.flush()

    if suspicious:
        pending = PendingComment(
            comment_id=comment.id,
            article_id=article_id,
            author=comment.author,
            email=comment.email,
            content=comment.content,
            ip_address=ip_address,
            spam_reason=reason,
            spam_score=0,
        )
        db.add(pending)

    if status == CommentStatus.PUBLISHED.value:
        article.comment_count += 1

    await db.commit()

    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.children))
        .where(Comment.id == comment.id)
    )
    comment = result.scalar_one()

    return comment


async def update_comment(
    db: AsyncSession,
    comment_id: int,
    comment_data: CommentUpdate,
    user: str = "admin",
    request_ip: Optional[str] = None,
) -> Optional[Comment]:
    comment = await get_comment(db, comment_id)
    if not comment:
        return None

    old_value = {"id": comment.id, "status": comment.status, "content": comment.content}

    update_data = comment_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(comment, key, value)

    await db.commit()
    await db.refresh(comment)

    await log_audit(
        db,
        action="update",
        resource_type="comment",
        resource_id=comment.id,
        user=user,
        ip_address=request_ip,
        old_value=old_value,
        new_value={"status": comment.status, "content": comment.content},
    )

    return comment


async def delete_comment(
    db: AsyncSession,
    comment_id: int,
    user: str = "admin",
    request_ip: Optional[str] = None,
) -> bool:
    comment = await get_comment(db, comment_id)
    if not comment:
        return False

    old_value = {"id": comment.id, "author": comment.author}

    await db.delete(comment)
    await db.commit()

    await log_audit(
        db,
        action="delete",
        resource_type="comment",
        resource_id=comment_id,
        user=user,
        ip_address=request_ip,
        old_value=old_value,
    )

    return True


async def like_comment(db: AsyncSession, comment_id: int) -> bool:
    comment = await get_comment(db, comment_id)
    if not comment:
        return False
    comment.likes += 1
    await db.commit()
    return True


async def report_comment(db: AsyncSession, comment_id: int) -> bool:
    comment = await get_comment(db, comment_id)
    if not comment:
        return False
    comment.report_count += 1
    if comment.status == CommentStatus.PUBLISHED.value:
        comment.status = CommentStatus.REPORTED.value
    await db.commit()
    return True


async def list_pending_comments(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[PendingComment], int]:
    query = select(PendingComment).where(PendingComment.reviewed == False)
    count_query = select(func.count()).select_from(PendingComment).where(PendingComment.reviewed == False)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(desc(PendingComment.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def review_pending_comment(
    db: AsyncSession,
    pending_id: int,
    approved: bool,
    reason: Optional[str] = None,
    user: str = "admin",
) -> bool:
    result = await db.execute(
        select(PendingComment).where(PendingComment.id == pending_id)
    )
    pending = result.scalar_one_or_none()
    if not pending:
        return False

    pending.reviewed = True

    if pending.comment_id:
        comment_result = await db.execute(
            select(Comment).where(Comment.id == pending.comment_id)
        )
        comment = comment_result.scalar_one_or_none()
        if comment:
            if approved:
                comment.status = CommentStatus.PUBLISHED.value
                article_result = await db.execute(
                    select(Article).where(Article.id == comment.article_id)
                )
                article = article_result.scalar_one_or_none()
                if article:
                    article.comment_count += 1
            else:
                comment.status = CommentStatus.REJECTED.value

    await db.commit()
    return True


async def is_ip_banned(db: AsyncSession, ip_address: str) -> bool:
    if not ip_address:
        return False
    result = await db.execute(
        select(IPBlacklist).where(
            and_(
                IPBlacklist.ip_address == ip_address,
                or_(
                    IPBlacklist.expires_at.is_(None),
                    IPBlacklist.expires_at > datetime.utcnow(),
                ),
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def ban_ip(
    db: AsyncSession,
    ip_address: str,
    reason: str = "",
    duration_hours: int = 24,
) -> None:
    existing = await db.execute(
        select(IPBlacklist).where(IPBlacklist.ip_address == ip_address)
    )
    if existing.scalar_one_or_none():
        return

    expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
    ban = IPBlacklist(
        ip_address=ip_address,
        reason=reason,
        expires_at=expires_at,
    )
    db.add(ban)
    await db.commit()


async def get_comment_count_by_ip(
    db: AsyncSession, ip_address: str, hours: int = 24
) -> int:
    if not ip_address:
        return 0
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(func.count(Comment.id)).where(
            and_(
                Comment.ip_address == ip_address,
                Comment.created_at >= since,
            )
        )
    )
    return result.scalar_one()
