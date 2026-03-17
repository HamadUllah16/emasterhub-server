import datetime
import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class ContentBlockType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    KEY_TAKEAWAYS = "key_takeaways"
    SUMMARY = "summary"


class ContentBlock(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    lesson_id: uuid.UUID = Field(foreign_key="lesson.id", index=True)

    sort_order: int = Field(default=0, index=True)
    block_type: ContentBlockType = Field(index=True)
    content: str = Field(default="")
    meta: dict = Field(default_factory=dict, sa_column=Column("metadata", JSON))

    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

