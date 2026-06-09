from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import category_service
from app.schemas import CategoryCreate


@pytest.mark.asyncio
async def test_create_category(client: AsyncClient):
    cat_data = {
        "name": "Technology",
        "description": "Tech articles",
    }
    response = await client.post("/api/v1/categories", json=cat_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Technology"
    assert data["slug"] == "technology"
    assert data["level"] == 0


@pytest.mark.asyncio
async def test_create_nested_category(client: AsyncClient, db_session: AsyncSession):
    parent = await category_service.create_category(
        db_session, CategoryCreate(name="Parent")
    )

    child_data = {
        "name": "Child",
        "parent_id": parent.id,
    }
    response = await client.post("/api/v1/categories", json=child_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Child"
    assert data["level"] == 1


@pytest.mark.asyncio
async def test_max_category_depth(client: AsyncClient, db_session: AsyncSession):
    level0 = await category_service.create_category(
        db_session, CategoryCreate(name="Level0")
    )
    level1 = await category_service.create_category(
        db_session, CategoryCreate(name="Level1", parent_id=level0.id)
    )

    child_data = {
        "name": "Level2",
        "parent_id": level1.id,
    }
    response = await client.post("/api/v1/categories", json=child_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient, db_session: AsyncSession):
    for i in range(3):
        await category_service.create_category(
            db_session, CategoryCreate(name=f"Cat {i}")
        )

    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_update_category(client: AsyncClient, db_session: AsyncSession):
    cat = await category_service.create_category(
        db_session, CategoryCreate(name="Old Name")
    )

    update_data = {"name": "New Name"}
    response = await client.put(f"/api/v1/categories/{cat.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_category(client: AsyncClient, db_session: AsyncSession):
    cat = await category_service.create_category(
        db_session, CategoryCreate(name="To Delete")
    )

    response = await client.delete(f"/api/v1/categories/{cat.id}")
    assert response.status_code == 204
