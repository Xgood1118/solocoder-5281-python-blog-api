from __future__ import annotations

from typing import List

from feedgen.feed import FeedGenerator

from app.config import get_settings
from app.models import Article

settings = get_settings()


def generate_rss_feed(articles: List[Article], feed_type: str = "rss") -> str:
    fg = FeedGenerator()
    fg.title(settings.site_name)
    fg.link(href=settings.site_url, rel="alternate")
    fg.description(settings.site_description)
    fg.language("zh-CN")

    for article in articles:
        fe = fg.add_entry()
        fe.title(article.title)
        fe.link(href=f"{settings.site_url}/articles/{article.slug}", rel="alternate")
        fe.guid(f"{settings.site_url}/articles/{article.slug}", permalink=True)

        if article.summary:
            fe.summary(article.summary)

        fe.content(article.content, type="html")

        if article.published_at:
            fe.published(article.published_at)

        fe.author(name=article.author)

        if article.tags:
            for tag in article.tags:
                fe.category(term=tag.name)

    if feed_type == "atom":
        return fg.atom_str(pretty=True).decode("utf-8")
    else:
        return fg.rss_str(pretty=True).decode("utf-8")


def generate_atom_feed(articles: List[Article]) -> str:
    return generate_rss_feed(articles, feed_type="atom")
