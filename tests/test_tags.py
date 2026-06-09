from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import tag_service
from app.schemas import TagCreate


@pytest.mark.asyncio
async def test_create_tag(client: AsyncClient):
    tag_data = {
        "name": "Python",
        "description": "Python programming language",
    }
    response = await client.post("/api/v1/tags", json=tag_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Python"
    assert data["slug"] == "python"


@pytest.mark.asyncio
async def test_list_tags(client: AsyncClient, db_session: AsyncSession):
    for i in range(5):
        await tag_service.create_tag(db_session, TagCreate(name=f"Tag {i}"))

    response = await client.get("/api/v1/tags")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


@pytest.mark.asyncio
async def test_get_tag(client: AsyncClient, db_session: AsyncSession):
    tag = await tag_service.create_tag(db_session, TagCreate(name="Test Tag"))

    response = await client.get(f"/api/v1/tags/{tag.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Tag"


@pytest.mark.asyncio
async def test_update_tag(client: AsyncClient, db_session: AsyncSession):
    tag = await tag_service.create_tag(db_session, TagCreate(name="Old Name"))

    update_data = {"name": "New Name"}
    response = await client.put(f"/api/v1/tags/{tag.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_tag(client: AsyncClient, db_session: AsyncSession):
    tag = await tag_service.create_tag(db_session, TagCreate(name="To Delete"))

    response = await client.delete(f"/api/v1/tags/{tag.id}")
    assert response.status_code == 204

    response = await client.get(f"/api/v1/tags/{tag.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tag_cloud(client: AsyncClient, db_session: AsyncSession):
    for i in range(3):
        await tag_service.create_tag(db_session, TagCreate(name=f"CloudTag {i}"))

    response = await client.get("/api/v1/tags/cloud?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
