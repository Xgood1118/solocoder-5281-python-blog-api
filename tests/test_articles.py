from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import article_service
from app.schemas import ArticleCreate


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_create_article(client: AsyncClient):
    article_data = {
        "title": "Test Article",
        "content": "This is a test article content.",
        "summary": "Test summary",
        "status": "published",
        "tag_ids": [],
    }
    response = await client.post("/api/v1/articles", json=article_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Article"
    assert data["slug"] == "test-article"
    assert data["status"] == "published"


@pytest.mark.asyncio
async def test_get_article(client: AsyncClient, db_session: AsyncSession):
    article_data = ArticleCreate(
        title="Test Article",
        content="Content here",
        status="published",
    )
    article = await article_service.create_article(db_session, article_data)

    response = await client.get(f"/api/v1/articles/{article.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == article.id
    assert data["title"] == "Test Article"


@pytest.mark.asyncio
async def test_list_articles(client: AsyncClient, db_session: AsyncSession):
    for i in range(5):
        article_data = ArticleCreate(
            title=f"Article {i}",
            content=f"Content {i}",
            status="published",
        )
        await article_service.create_article(db_session, article_data)

    response = await client.get("/api/v1/articles?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5


@pytest.mark.asyncio
async def test_update_article(client: AsyncClient, db_session: AsyncSession):
    article_data = ArticleCreate(
        title="Original Title",
        content="Original content",
    )
    article = await article_service.create_article(db_session, article_data)

    update_data = {"title": "Updated Title"}
    response = await client.put(f"/api/v1/articles/{article.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_delete_article(client: AsyncClient, db_session: AsyncSession):
    article_data = ArticleCreate(
        title="To Delete",
        content="Delete me",
    )
    article = await article_service.create_article(db_session, article_data)

    response = await client.delete(f"/api/v1/articles/{article.id}")
    assert response.status_code == 204

    response = await client.get(f"/api/v1/articles/{article.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_like_article(client: AsyncClient, db_session: AsyncSession):
    article_data = ArticleCreate(
        title="Like Test",
        content="Like me",
        status="published",
    )
    article = await article_service.create_article(db_session, article_data)

    response = await client.post(f"/api/v1/articles/{article.id}/like")
    assert response.status_code == 200

    response = await client.get(f"/api/v1/articles/{article.id}")
    data = response.json()
    assert data["likes"] == 1


@pytest.mark.asyncio
async def test_get_article_by_slug(client: AsyncClient, db_session: AsyncSession):
    article_data = ArticleCreate(
        title="Slug Test Article",
        content="Content",
        status="published",
    )
    article = await article_service.create_article(db_session, article_data)

    response = await client.get(f"/api/v1/articles/slug/{article.slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == article.slug
