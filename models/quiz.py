import datetime
import uuid
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class Quiz(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    module_id: uuid.UUID = Field(foreign_key="module.id", index=True)

    # Generated questions as JSON.
    questions: list[dict] = Field(default_factory=list, sa_column=Column(JSON))

    raw: Optional[str] = Field(default=None)

    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
