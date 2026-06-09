from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)


class TagResponse(TagBase):
    id: int
    article_count: Optional[int] = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagCloudItem(BaseModel):
    id: int
    name: str
    slug: str
    article_count: int


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[int] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[int] = None


class CategoryResponse(CategoryBase):
    id: int
    level: int
    created_at: datetime
    updated_at: datetime
    children: List["CategoryResponse"] = []
    article_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class ArticleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: Optional[str] = None
    summary: Optional[str] = Field(None, max_length=500)
    content: str
    cover_image: Optional[str] = None
    status: str = "draft"
    author: Optional[str] = "admin"
    category_id: Optional[int] = None
    tag_ids: List[int] = []
    seo_title: Optional[str] = Field(None, max_length=200)
    seo_description: Optional[str] = Field(None, max_length=500)
    og_image: Optional[str] = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = None
    summary: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    cover_image: Optional[str] = None
    status: Optional[str] = None
    author: Optional[str] = None
    category_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None
    seo_title: Optional[str] = Field(None, max_length=200)
    seo_description: Optional[str] = Field(None, max_length=500)
    og_image: Optional[str] = None


class ArticleSummary(BaseModel):
    id: int
    title: str
    slug: str
    summary: Optional[str] = None
    cover_image: Optional[str] = None
    status: str
    author: str
    views: int
    likes: int
    comment_count: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleDetail(ArticleSummary):
    content: str
    category: Optional[CategoryResponse] = None
    tags: List[TagResponse] = []
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    og_image: Optional[str] = None


class ArticleListResponse(BaseModel):
    items: List[ArticleSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class CommentBase(BaseModel):
    author: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    content: str = Field(..., min_length=1)
    parent_id: Optional[int] = None


class CommentCreate(CommentBase):
    pass


class CommentUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[str] = None


class CommentResponse(BaseModel):
    id: int
    article_id: int
    parent_id: Optional[int] = None
    depth: int
    author: str
    email: Optional[str] = None
    website: Optional[str] = None
    content: str
    status: str
    likes: int
    report_count: int
    created_at: datetime
    updated_at: datetime
    children: List["CommentResponse"] = []

    model_config = ConfigDict(from_attributes=True)


class CommentListResponse(BaseModel):
    items: List[CommentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SubscriptionBase(BaseModel):
    email: EmailStr


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionResponse(BaseModel):
    id: int
    email: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SearchResultItem(BaseModel):
    id: int
    title: str
    summary: str
    slug: str
    tags: List[str] = []
    published_at: Optional[datetime] = None


class SearchResponse(BaseModel):
    items: List[SearchResultItem]
    total: int
    page: int
    page_size: int
    processing_time_ms: Optional[float] = None


class ArchiveItem(BaseModel):
    date: str
    count: int
    articles: List[ArticleSummary] = []


class ArchiveResponse(BaseModel):
    archives: List[ArchiveItem]


class PendingCommentReview(BaseModel):
    approved: bool
    reason: Optional[str] = None
