from fastapi import FastAPI
from dotenv import load_dotenv

from routers.course import router as course_router

load_dotenv()

app = FastAPI(title="eMasterHub AI Course Creator")


@app.get("/")
def read_root():
    return {"message": "eMasterHub API is running"}


app.include_router(course_router, prefix="/courses", tags=["courses"])
