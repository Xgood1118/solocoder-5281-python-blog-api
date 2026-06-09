from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_audit(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    user: Optional[str] = None,
    ip_address: Optional[str] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
) -> None:
    log_entry = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user=user,
        ip_address=ip_address,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(log_entry)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
