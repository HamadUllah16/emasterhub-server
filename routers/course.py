import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from services.course import generate_course_with_claude


router = APIRouter()
logger = logging.getLogger(__name__)


class CourseCreateRequest(BaseModel):
    topic: str = Field(..., description="High-level topic for the course, e.g. 'Intro to Python for Data Science'")
    target_audience: Optional[str] = Field(
        default=None,
        description="Who this course is for, e.g. 'beginners with no coding experience'",
    )
    difficulty: Optional[str] = Field(
        default=None,
        description="Difficulty level, e.g. 'beginner', 'intermediate', 'advanced'",
    )
    language: str = Field(default="en", description="Language for the generated content, e.g. 'en'")


class GeneratedCourseResponse(BaseModel):
    outline: str = Field(..., description="Structured outline of the generated course")
    model: str = Field(..., description="Claude model used to generate the course")


@router.post("/generate", response_model=GeneratedCourseResponse)
def create_course(payload: CourseCreateRequest):
    try:
        outline, model = generate_course_with_claude(payload)
        return GeneratedCourseResponse(outline=outline, model=model)
    except ValueError as e:
        logger.exception("Course generation failed due to configuration/validation error.")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error while generating course with Claude.")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate course with Claude. Check server logs for details.",
        )

