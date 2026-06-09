from __future__ import annotations

import jieba
from meilisearch import Client
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings

settings = get_settings()

_client: Optional[Client] = None


def get_search_client() -> Optional[Client]:
    global _client
    if not settings.meilisearch_enabled:
        return None
    if _client is None:
        try:
            _client = Client(settings.meilisearch_url, settings.meilisearch_api_key)
        except Exception:
            _client = None
    return _client


def tokenize(text: str) -> str:
    tokens = jieba.cut_for_search(text)
    return " ".join(tokens)


async def init_index() -> None:
    client = get_search_client()
    if not client:
        return

    try:
        index = client.index(settings.meilisearch_index)
        index.update_searchable_attributes([
            "title", "summary", "content", "tags", "author"
        ])
        index.update_filterable_attributes(["tags", "category_id", "status"])
        index.update_sortable_attributes(["published_at", "views", "likes"])
    except Exception:
        pass


def article_to_document(article: Any) -> Dict[str, Any]:
    tags = [tag.name for tag in article.tags] if hasattr(article, "tags") else []
    content_tokens = tokenize(article.content or "")

    return {
        "id": str(article.id),
        "title": article.title,
        "summary": article.summary or "",
        "content": content_tokens,
        "tags": tags,
        "author": article.author,
        "category_id": article.category_id,
        "slug": article.slug,
        "cover_image": article.cover_image or "",
        "views": article.views,
        "likes": article.likes,
        "status": article.status,
        "published_at": article.published_at.isoformat() if article.published_at else None,
    }


def add_articles(articles: List[Any]) -> None:
    client = get_search_client()
    if not client:
        return

    try:
        documents = [article_to_document(a) for a in articles]
        client.index(settings.meilisearch_index).add_documents(documents)
    except Exception:
        pass


def update_article(article: Any) -> None:
    client = get_search_client()
    if not client:
        return

    try:
        document = article_to_document(article)
        client.index(settings.meilisearch_index).update_documents([document])
    except Exception:
        pass


def delete_article(article_id: int) -> None:
    client = get_search_client()
    if not client:
        return

    try:
        client.index(settings.meilisearch_index).delete_document(str(article_id))
    except Exception:
        pass


def search_articles(
    query: str,
    page: int = 1,
    page_size: int = 20,
    filter_tags: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], int, float]:
    client = get_search_client()
    if not client:
        return [], 0, 0.0

    try:
        search_params: Dict[str, Any] = {
            "offset": (page - 1) * page_size,
            "limit": page_size,
        }

        if filter_tags:
            tag_filters = [f"tags = {tag!r}" for tag in filter_tags]
            search_params["filter"] = " OR ".join(tag_filters)

        result = client.index(settings.meilisearch_index).search(query, search_params)

        items = result.get("hits", [])
        total = result.get("estimatedTotalHits", result.get("nbHits", 0))
        processing_time = result.get("processingTimeMs", 0)

        return items, total, processing_time
    except Exception:
        return [], 0, 0.0
