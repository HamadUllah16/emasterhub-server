import datetime
import uuid
from typing import Optional

from sqlmodel import SQLModel, Field


class Lesson(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    module_id: uuid.UUID = Field(foreign_key="module.id", index=True)

    sort_order: int = Field(default=0, index=True)
    title: str = Field(max_length=255)
    summary: Optional[str] = Field(default=None, max_length=2000)

    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
