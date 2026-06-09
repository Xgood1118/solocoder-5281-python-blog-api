from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import article_service, comment_service
from app.schemas import ArticleCreate, CommentCreate


@pytest.fixture
async def test_article(db_session: AsyncSession):
    article_data = ArticleCreate(
        title="Comment Test Article",
        content="Content for comment testing",
        status="published",
    )
    return await article_service.create_article(db_session, article_data)


@pytest.mark.asyncio
async def test_create_comment(client: AsyncClient, test_article):
    article = test_article
    comment_data = {
        "author": "Test User",
        "email": "test@example.com",
        "content": "This is a test comment.",
    }
    response = await client.post(
        f"/api/v1/comments?article_id={article.id}", json=comment_data
    )
    assert response.status_code == 201
    data = response.json()
    assert data["author"] == "Test User"
    assert data["content"] == "This is a test comment."
    assert data["depth"] == 0


@pytest.mark.asyncio
async def test_nested_comment(client: AsyncClient, db_session: AsyncSession, test_article):
    article = test_article

    parent = await comment_service.create_comment(
        db_session,
        article_id=article.id,
        comment_data=CommentCreate(author="Parent", content="Parent comment"),
        ip_address="127.0.0.1",
    )

    child_data = {
        "author": "Child",
        "content": "Child comment",
        "parent_id": parent.id,
    }
    response = await client.post(
        f"/api/v1/comments?article_id={article.id}", json=child_data
    )
    assert response.status_code == 201
    data = response.json()
    assert data["depth"] == 1
    assert data["parent_id"] == parent.id


@pytest.mark.asyncio
async def test_list_comments(client: AsyncClient, db_session: AsyncSession, test_article):
    article = test_article
    for i in range(3):
        await comment_service.create_comment(
            db_session,
            article_id=article.id,
            comment_data=CommentCreate(
                author=f"User {i}", content=f"Comment {i}"
            ),
            ip_address=f"127.0.0.{i}",
        )

    response = await client.get(
        f"/api/v1/comments?article_id={article.id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_like_comment(client: AsyncClient, db_session: AsyncSession, test_article):
    article = test_article
    comment = await comment_service.create_comment(
        db_session,
        article_id=article.id,
        comment_data=CommentCreate(author="User", content="Like me"),
        ip_address="127.0.0.1",
    )

    response = await client.post(f"/api/v1/comments/{comment.id}/like")
    assert response.status_code == 200

    response = await client.get(f"/api/v1/comments/{comment.id}")
    data = response.json()
    assert data["likes"] == 1


@pytest.mark.asyncio
async def test_report_comment(client: AsyncClient, db_session: AsyncSession, test_article):
    article = test_article
    comment = await comment_service.create_comment(
        db_session,
        article_id=article.id,
        comment_data=CommentCreate(author="User", content="Report me"),
        ip_address="127.0.0.1",
    )

    response = await client.post(f"/api/v1/comments/{comment.id}/report")
    assert response.status_code == 200

    response = await client.get(f"/api/v1/comments/{comment.id}")
    data = response.json()
    assert data["report_count"] == 1
