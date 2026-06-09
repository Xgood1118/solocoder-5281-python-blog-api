from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import subscription_service


@pytest.mark.asyncio
async def test_subscribe(client: AsyncClient):
    response = await client.post(
        "/api/v1/subscribe", json={"email": "test@example.com"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_subscribe_duplicate(client: AsyncClient, db_session: AsyncSession):
    await subscription_service.subscribe(db_session, "dup@example.com")

    response = await client.post(
        "/api/v1/subscribe", json={"email": "dup@example.com"}
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_unsubscribe(client: AsyncClient, db_session: AsyncSession):
    await subscription_service.subscribe(db_session, "unsub@example.com")

    response = await client.post(
        "/api/v1/unsubscribe", json={"email": "unsub@example.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_unsubscribe_not_found(client: AsyncClient):
    response = await client.post(
        "/api/v1/unsubscribe", json={"email": "nope@example.com"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_subscriptions(client: AsyncClient, db_session: AsyncSession):
    for i in range(3):
        await subscription_service.subscribe(db_session, f"user{i}@example.com")

    response = await client.get("/api/v1/subscriptions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
