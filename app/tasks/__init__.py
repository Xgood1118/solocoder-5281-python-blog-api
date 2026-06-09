from __future__ import annotations

import asyncio
from typing import List

from app.email.sender import send_new_article_notification
from app.models import Article
from app.search import update_article, delete_article, add_articles


async def sync_article_to_search(article: Article) -> None:
    try:
        update_article(article)
    except Exception:
        pass


async def remove_article_from_search(article_id: int) -> None:
    try:
        delete_article(article_id)
    except Exception:
        pass


async def batch_sync_articles(articles: List[Article]) -> None:
    try:
        add_articles(articles)
    except Exception:
        pass


async def notify_subscribers_of_new_article(
    article: Article, subscribers: List[str]
) -> None:
    from app.config import get_settings
    settings = get_settings()
    article_url = f"{settings.site_url}/articles/{article.slug}"

    tasks = []
    for email in subscribers:
        tasks.append(
            send_new_article_notification(
                email, article.title, article_url, settings.site_name
            )
        )

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
