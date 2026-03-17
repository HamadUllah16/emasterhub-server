import datetime
import uuid
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class Module(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    course_id: uuid.UUID = Field(foreign_key="course.id", index=True)

    sort_order: int = Field(default=0, index=True)
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    learning_objectives: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Generation outputs (Step 2)
    content_raw: Optional[str] = Field(default=None)

    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
