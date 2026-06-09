from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    app_name: str = "Blog API"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/api/v1"

    site_url: str = "http://localhost:8000"
    site_name: str = "My Blog"
    site_description: str = "A modern blog built with FastAPI"

    database_url: str = "sqlite+aiosqlite:///./blog.db"

    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True

    meilisearch_url: str = "http://localhost:7700"
    meilisearch_api_key: str = ""
    meilisearch_index: str = "articles"
    meilisearch_enabled: bool = True

    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    mail_from: str = "noreply@example.com"
    mail_from_name: str = "Blog Admin"

    comment_rate_limit_seconds: int = 60
    comment_max_links: int = 3
    comment_ip_daily_limit: int = 10

    spam_keywords: List[str] = [
        "spam",
        "垃圾",
        "广告",
        "推广",
        "兼职",
        "赚钱",
        "赌博",
        "色情",
        "viagra",
        "casino",
    ]

    hot_articles_cache_ttl: int = 600

    secret_key: str = "change-me-in-production-please"

    @property
    def spam_keywords_set(self) -> set:
        return {kw.lower() for kw in self.spam_keywords}


@lru_cache
def get_settings() -> Settings:
    return Settings()
