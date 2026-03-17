import os
from dotenv import load_dotenv

load_dotenv()

def get_database_url() -> str:
    """
    Resolve the SQLAlchemy database URL.

    if DATABASE_URL is set, return it, otherwise raise an error
    """
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    raise ValueError("DATABASE_URL is not set in the environment.")