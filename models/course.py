import datetime
import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class CourseStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class Course(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # user_id: uuid.UUID = Field(foreign_key="user.id") # TODO: add user_id
    category_id: Optional[uuid.UUID] = Field(default=None, foreign_key="category.id")
    theme_id: Optional[uuid.UUID] = Field(default=None, foreign_key="theme.id")

    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)

    # Generation metadata (Step 1 input)
    target_audience: Optional[str] = Field(default=None, max_length=1000)
    reading_level: Optional[str] = Field(default=None, max_length=64)
    country: Optional[str] = Field(default=None, max_length=128)
    tone: Optional[str] = Field(default=None, max_length=255)
    depth: Optional[str] = Field(default=None, max_length=255)
    module_count: Optional[int] = Field(default=None)
    lessons_per_module: Optional[int] = Field(default=None)
    language: str = Field(default="en", max_length=32)
    source_doc_chunks: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Generation outputs (Step 1)
    outline_json: dict = Field(default_factory=dict, sa_column=Column(JSON))

    status: CourseStatus = Field(default=CourseStatus.DRAFT)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

