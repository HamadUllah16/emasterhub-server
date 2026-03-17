import logging

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from database.session import get_session
from models.content_block import ContentBlock, ContentBlockType
from models.course import Course
from models.lesson import Lesson
from models.module import Module
from models.quiz import Quiz
from services.course import (
    generate_course_outline_structured,
    generate_module_content_structured,
    generate_module_quiz_structured,
)


router = APIRouter()
logger = logging.getLogger(__name__)


class GeneratedCourseResponse(BaseModel):
    outline: str = Field(..., description="Structured outline of the generated course")
    model: str = Field(..., description="Claude model used to generate the course")


class OutlineGenerateRequest(BaseModel):
    doc_chunks: list[str] = Field(default_factory=list, description="Chunked source documents / notes")
    title: str = Field(..., description="Course title")
    description: Optional[str] = Field(default=None, description="Course description / brief (optional)")
    audience: Optional[str] = Field(default=None, description="Target audience")
    reading_level: Optional[str] = Field(
        default=None,
        description="Reading level, e.g. 'very easy', 'easy', 'standard', 'difficult', 'very difficult'",
    )
    country: Optional[str] = Field(default=None, description="Target country/localization, e.g. 'Saudi Arabia'")
    tone: Optional[str] = Field(default=None, description="Writing tone, e.g. 'friendly', 'formal'")
    depth: Optional[str] = Field(default=None, description="Depth, e.g. 'beginner', 'advanced'")
    module_count: Optional[int] = Field(default=None, ge=1, le=50)
    lessons_per_module: Optional[int] = Field(default=None, ge=1, le=50)
    language: str = Field(default="en", description="Language for generation")


class OutlineGenerateResponse(BaseModel):
    course_id: uuid.UUID
    outline: dict
    model: str


@router.post("/outline", response_model=OutlineGenerateResponse)
def generate_outline(payload: OutlineGenerateRequest, session: Session = Depends(get_session)):
    """
    Step 1: Generate outline + create Course/Module/Lesson skeleton rows.
    """
    try:
        outline_json, _raw = generate_course_outline_structured(payload)

        course_info = (outline_json or {}).get("course") or {}
        modules_info = (outline_json or {}).get("modules") or []

        course = Course(
            title=course_info.get("title") or payload.title,
            description=course_info.get("description") or payload.description,
            target_audience=payload.audience,
            reading_level=payload.reading_level,
            country=payload.country,
            tone=payload.tone,
            depth=payload.depth,
            module_count=payload.module_count,
            lessons_per_module=payload.lessons_per_module,
            language=payload.language,
            source_doc_chunks=payload.doc_chunks,
            outline_json=outline_json,
        )
        session.add(course)
        session.commit()
        session.refresh(course)

        for module_obj in modules_info:
            module = Module(
                course_id=course.id,
                sort_order=int(module_obj.get("sort_order") or 0),
                title=str(module_obj.get("title") or "").strip() or "Untitled module",
                description=module_obj.get("description"),
                learning_objectives=module_obj.get("learning_objectives") or [],
            )
            session.add(module)
            session.commit()
            session.refresh(module)

            for lesson_obj in module_obj.get("lessons") or []:
                lesson = Lesson(
                    module_id=module.id,
                    sort_order=int(lesson_obj.get("sort_order") or 0),
                    title=str(lesson_obj.get("title") or "").strip() or "Untitled lesson",
                )
                session.add(lesson)

            session.commit()

        return OutlineGenerateResponse(course_id=course.id, outline=outline_json)
    except ValueError as e:
        logger.exception("Outline generation failed due to configuration/validation error.")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        logger.exception("Unexpected error while generating outline.")
        raise HTTPException(status_code=500, detail="Failed to generate course outline.")


class ModuleContentGenerateRequest(BaseModel):
    language: str = Field(default="en")


class ModuleContentGenerateResponse(BaseModel):
    module_id: uuid.UUID
    lessons_written: int
    model: str


@router.post("/{course_id}/modules/{module_id}/content", response_model=ModuleContentGenerateResponse)
def generate_module_content(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    payload: ModuleContentGenerateRequest,
    session: Session = Depends(get_session),
):
    """
    Step 2: Generate lesson content blocks for a specific module (1 call per module).
    """
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    module = session.get(Module, module_id)
    if not module or module.course_id != course_id:
        raise HTTPException(status_code=404, detail="Module not found for this course.")

    lessons = session.exec(select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.sort_order)).all()
    if not lessons:
        raise HTTPException(status_code=400, detail="Module has no lessons to generate content for.")

    class _Payload(BaseModel):
        outline_json: dict
        module_sort_order: int
        module_title: str
        module_description: Optional[str] = None
        module_learning_objectives: list[str] = Field(default_factory=list)
        lesson_titles: list[str] = Field(default_factory=list)
        language: str = "en"

    req = _Payload(
        outline_json=course.outline_json or {},
        module_sort_order=module.sort_order,
        module_title=module.title,
        module_description=module.description,
        module_learning_objectives=module.learning_objectives or [],
        lesson_titles=[l.title for l in lessons],
        language=payload.language or course.language,
    )

    try:
        module_content_json, raw = generate_module_content_structured(req)
    except Exception:
        logger.exception("Failed generating module content.")
        raise HTTPException(status_code=500, detail="Failed to generate module content.")

    # Persist raw/model on module.
    module.content_raw = raw
    session.add(module)

    # Write blocks.
    lessons_written = 0
    lessons_by_title = {l.title.strip().lower(): l for l in lessons}
    lessons_by_order = {l.sort_order: l for l in lessons}

    for lesson_obj in (module_content_json or {}).get("lessons") or []:
        title = str(lesson_obj.get("title") or "").strip()
        sort_order = int(lesson_obj.get("sort_order") or 0)
        lesson = lessons_by_title.get(title.lower()) or lessons_by_order.get(sort_order)
        if not lesson:
            continue

        # Clear existing blocks for idempotency (simple approach).
        existing = session.exec(select(ContentBlock).where(ContentBlock.lesson_id == lesson.id)).all()
        for b in existing:
            session.delete(b)

        blocks = lesson_obj.get("blocks") or []
        for idx, blk in enumerate(blocks):
            btype = blk.get("type")
            if btype not in {t.value for t in ContentBlockType}:
                continue

            metadata: dict[str, Any] = {}
            if btype == ContentBlockType.KEY_TAKEAWAYS.value:
                metadata["items"] = blk.get("items") or []
                content = ""
            else:
                content = str(blk.get("content") or "")

            cb = ContentBlock(
                lesson_id=lesson.id,
                sort_order=idx,
                block_type=ContentBlockType(btype),
                content=content,
                meta=metadata,
            )
            session.add(cb)

        # Best-effort lesson summary from "summary" block.
        summary_block = next((b for b in blocks if b.get("type") == ContentBlockType.SUMMARY.value), None)
        if summary_block:
            lesson.summary = str(summary_block.get("content") or "")[:2000]
            session.add(lesson)

        lessons_written += 1

    session.commit()
    return ModuleContentGenerateResponse(module_id=module.id, lessons_written=lessons_written)


class ModuleQuizGenerateRequest(BaseModel):
    enabled: bool = Field(default=True, description="Toggle quiz generation")
    quiz_settings: dict = Field(default_factory=dict, description="format, num_questions, num_choices, etc.")
    language: str = Field(default="en")


class ModuleQuizGenerateResponse(BaseModel):
    module_id: uuid.UUID
    generated: bool
    quiz_id: Optional[uuid.UUID] = None
    model: Optional[str] = None


@router.post("/{course_id}/modules/{module_id}/quiz", response_model=ModuleQuizGenerateResponse)
def generate_module_quiz(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    payload: ModuleQuizGenerateRequest,
    session: Session = Depends(get_session),
):
    """
    Step 3: Optionally generate a quiz for a module using module content stored in DB.
    """
    if not payload.enabled:
        return ModuleQuizGenerateResponse(module_id=module_id, generated=False)

    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    module = session.get(Module, module_id)
    if not module or module.course_id != course_id:
        raise HTTPException(status_code=404, detail="Module not found for this course.")

    lessons = session.exec(select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.sort_order)).all()
    lesson_material: list[dict] = []
    for lesson in lessons:
        blocks = session.exec(
            select(ContentBlock).where(ContentBlock.lesson_id == lesson.id).order_by(ContentBlock.sort_order)
        ).all()
        lesson_material.append(
            {
                "title": lesson.title,
                "summary": lesson.summary,
                "blocks": [
                    {
                        "type": b.block_type.value,
                        "content": b.content,
                        "metadata": b.meta,
                    }
                    for b in blocks
                ],
            }
        )

    class _Payload(BaseModel):
        module_title: str
        module_learning_objectives: list[str] = Field(default_factory=list)
        lesson_material: list[dict] = Field(default_factory=list)
        quiz_settings: dict = Field(default_factory=dict)
        language: str = "en"

    req = _Payload(
        module_title=module.title,
        module_learning_objectives=module.learning_objectives or [],
        lesson_material=lesson_material,
        quiz_settings=payload.quiz_settings or {},
        language=payload.language or course.language,
    )

    try:
        quiz_json, raw = generate_module_quiz_structured(req)
    except Exception:
        logger.exception("Failed generating module quiz.")
        raise HTTPException(status_code=500, detail="Failed to generate module quiz.")

    quiz = Quiz(
        module_id=module.id,
        questions=(quiz_json or {}).get("questions") or [],
        raw=raw,
    )
    session.add(quiz)
    session.commit()
    session.refresh(quiz)

    return ModuleQuizGenerateResponse(
        module_id=module.id,
        generated=True,
        quiz_id=quiz.id,
    )

