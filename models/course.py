import datetime
import uuid
from sqlmodel import SQLModel, Field

class Course(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category_id: uuid.UUID = Field(foreign_key="category.id")
    title: str = Field(max_length=255)
    description: str = Field(max_length=1000)
    target_audience: str=Field(max_length=255)
    reading_level: str=Field(max_length=255)
    language: str=Field(max_length=255)
    theme_id: uuid.UUID = Field(foreign_key="theme.id")
    status: str=Field(max_length=255)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)