from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from feedgen.feed import FeedGenerator

from app.config import get_settings
from app.models import Article

settings = get_settings()


def _ensure_tz(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _build_feed(articles: List[Article]) -> FeedGenerator:
    fg = FeedGenerator()
    fg.title(settings.site_name)
    fg.link(href=settings.site_url, rel="alternate")
    fg.description(settings.site_description)
    fg.language("zh-CN")

    fg.id(settings.site_url)

    if articles and articles[0].updated_at:
        fg.updated(_ensure_tz(articles[0].updated_at))
    elif articles and articles[0].created_at:
        fg.updated(_ensure_tz(articles[0].created_at))
    else:
        fg.updated(datetime.now(timezone.utc))

    for article in articles:
        fe = fg.add_entry()
        fe.title(article.title)
        fe.link(href=f"{settings.site_url}/articles/{article.slug}", rel="alternate")
        fe.guid(f"{settings.site_url}/articles/{article.slug}", permalink=True)
        fe.id(f"{settings.site_url}/articles/{article.slug}")

        if article.summary:
            fe.summary(article.summary)

        fe.content(article.content, type="html")

        if article.published_at:
            fe.published(_ensure_tz(article.published_at))

        fe.updated(_ensure_tz(article.updated_at or article.created_at))

        fe.author(name=article.author)

        if article.tags:
            for tag in article.tags:
                fe.category(term=tag.name)

    return fg


def generate_rss_feed(articles: List[Article]) -> str:
    fg = _build_feed(articles)
    return fg.rss_str(pretty=True).decode("utf-8")


def generate_atom_feed(articles: List[Article]) -> str:
    fg = _build_feed(articles)
    return fg.atom_str(pretty=True).decode("utf-8")
