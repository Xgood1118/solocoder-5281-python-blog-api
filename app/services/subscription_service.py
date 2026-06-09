from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.email.sender import send_confirmation_email
from app.models import Subscription, SubscriptionStatus
from app.services.audit import log_audit

settings = get_settings()


def _generate_confirm_token(email: str) -> str:
    salt = secrets.token_hex(16)
    token = hashlib.sha256(f"{email}{salt}{settings.secret_key}".encode()).hexdigest()
    return f"{salt}.{token}"


def _verify_token(email: str, token: str) -> bool:
    try:
        salt, hash_part = token.split(".", 1)
        expected = hashlib.sha256(
            f"{email}{salt}{settings.secret_key}".encode()
        ).hexdigest()
        return secrets.compare_digest(expected, hash_part)
    except (ValueError, AttributeError):
        return False


async def get_subscription(
    db: AsyncSession, email: str
) -> Optional[Subscription]:
    result = await db.execute(
        select(Subscription).where(Subscription.email == email)
    )
    return result.scalar_one_or_none()


async def list_subscriptions(
    db: AsyncSession,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Subscription], int]:
    query = select(Subscription)
    count_query = select(func.count()).select_from(Subscription)

    if status:
        query = query.where(Subscription.status == status)
        count_query = count_query.where(Subscription.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(desc(Subscription.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def subscribe(
    db: AsyncSession,
    email: str,
    ip_address: Optional[str] = None,
) -> Subscription:
    existing = await get_subscription(db, email)

    if existing:
        if existing.status == SubscriptionStatus.ACTIVE.value:
            return existing
        if existing.status == SubscriptionStatus.PENDING.value:
            token = _generate_confirm_token(email)
            existing.confirm_token = token
            await db.commit()
            await _send_confirmation(email, token)
            return existing

    token = _generate_confirm_token(email)

    subscription = Subscription(
        email=email,
        status=SubscriptionStatus.PENDING.value,
        confirm_token=token,
        ip_address=ip_address,
    )

    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    await _send_confirmation(email, token)

    await log_audit(
        db,
        action="create",
        resource_type="subscription",
        resource_id=subscription.id,
        ip_address=ip_address,
        new_value={"email": email, "status": "pending"},
    )

    return subscription


async def confirm_subscription(
    db: AsyncSession, email: str, token: str
) -> Optional[Subscription]:
    subscription = await get_subscription(db, email)
    if not subscription:
        return None

    if not _verify_token(email, token):
        return None

    if subscription.status != SubscriptionStatus.PENDING.value:
        return subscription

    subscription.status = SubscriptionStatus.ACTIVE.value
    subscription.confirmed_at = datetime.utcnow()
    subscription.confirm_token = None

    await db.commit()
    await db.refresh(subscription)

    await log_audit(
        db,
        action="update",
        resource_type="subscription",
        resource_id=subscription.id,
        old_value={"status": "pending"},
        new_value={"status": "active"},
    )

    return subscription


async def unsubscribe(
    db: AsyncSession,
    email: str,
) -> bool:
    subscription = await get_subscription(db, email)
    if not subscription:
        return False

    subscription.status = SubscriptionStatus.INACTIVE.value
    await db.commit()

    await log_audit(
        db,
        action="delete",
        resource_type="subscription",
        resource_id=subscription.id,
        old_value={"email": email, "status": subscription.status},
    )

    return True


async def get_active_subscribers(db: AsyncSession) -> List[str]:
    result = await db.execute(
        select(Subscription.email).where(
            Subscription.status == SubscriptionStatus.ACTIVE.value
        )
    )
    return [row.email for row in result.all()]


async def _send_confirmation(email: str, token: str) -> None:
    from app.config import get_settings as _get_settings
    _settings = _get_settings()
    confirm_url = f"{_settings.site_url}{_settings.api_prefix}/subscriptions/confirm?email={email}&token={token}"
    await send_confirmation_email(email, confirm_url)
