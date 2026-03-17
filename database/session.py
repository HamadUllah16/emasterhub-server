from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from database.config import get_database_url


engine = create_engine(get_database_url(), pool_pre_ping=True)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

