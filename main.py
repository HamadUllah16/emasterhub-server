from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

import models  # noqa: F401
from database.session import create_db_and_tables
from routers.course import router as course_router

app = FastAPI(title="eMasterHub AI Course Creator")

@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


@app.get("/")
def read_root():
    return {"message": "eMasterHub API is running"}


app.include_router(course_router, prefix="/courses", tags=["courses"])
