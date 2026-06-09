from __future__ import annotations

import json
import time
from typing import Any, Callable, List, Optional

from app.cache import get_redis_client
from app.config import get_settings

settings = get_settings()


async def get_cached(key: str) -> Optional[Any]:
    if not settings.redis_enabled:
        return None
    try:
        client = get_redis_client()
        data = await client.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


async def set_cached(key: str, value: Any, ttl: int = 300) -> None:
    if not settings.redis_enabled:
        return
    try:
        client = get_redis_client()
        await client.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


async def delete_cached(key: str) -> None:
    if not settings.redis_enabled:
        return
    try:
        client = get_redis_client()
        await client.delete(key)
    except Exception:
        pass


class SingleFlight:
    _in_flight: dict = {}
    _lock: Optional[Any] = None

    @classmethod
    async def execute(cls, key: str, func: Callable, *args, **kwargs) -> Any:
        if key in cls._in_flight:
            await cls._in_flight[key]["event"].wait()
            return cls._in_flight[key]["result"]

        import asyncio
        cls._in_flight[key] = {
            "event": asyncio.Event(),
            "result": None,
        }

        try:
            result = await func(*args, **kwargs)
            cls._in_flight[key]["result"] = result
            return result
        finally:
            cls._in_flight[key]["event"].set()
            del cls._in_flight[key]


async def increment_views(article_id: int) -> None:
    if not settings.redis_enabled:
        return None
    try:
        client = get_redis_client()
        await client.incr(f"article:{article_id}:views")
    except Exception:
        pass


async def get_views(article_id: int) -> int:
    if not settings.redis_enabled:
        return 0
    try:
        client = get_redis_client()
        views = await client.get(f"article:{article_id}:views")
        return int(views) if views else 0
    except Exception:
        return 0


async def check_rate_limit(key: str, limit_seconds: int) -> bool:
    if not settings.redis_enabled:
        return True
    try:
        client = get_redis_client()
        result = await client.set(key, 1, ex=limit_seconds, nx=True)
        return result is not None
    except Exception:
        return True


async def get_hot_articles_cached() -> Optional[List[dict]]:
    return await get_cached("hot_articles")


async def set_hot_articles_cache(articles: List[dict]) -> None:
    await set_cached("hot_articles", articles, settings.hot_articles_cache_ttl)
