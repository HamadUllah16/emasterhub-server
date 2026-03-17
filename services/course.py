import os
import json
from textwrap import dedent
from typing import Any, Tuple

from anthropic import Anthropic


CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")


def _extract_text(message: Any) -> str:
    parts: list[str] = []
    for block in getattr(message, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n\n".join(parts).strip()

def _parse_json_strict(text: str) -> Any:
    """
    Claude sometimes wraps JSON in markdown fences; strip them and parse.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        # Remove leading ```json or ``` and trailing ```
        stripped = stripped.split("\n", 1)[1]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
    return json.loads(stripped.strip())


def _get_client() -> Anthropic:
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("CLAUDE_API_KEY is not set in the environment.")
    return Anthropic(api_key=api_key)


def _build_outline_prompt(
    *,
    doc_chunks: list[str],
    title: str,
    description: str | None,
    audience: str | None,
    reading_level: str | None,
    country: str | None,
    tone: str | None,
    depth: str | None,
    module_count: int | None,
    lessons_per_module: int | None,
    language: str,
) -> str:
    return dedent(
        f"""
        You are an expert instructional designer.

        Create a course outline in {language}.

        Course metadata:
        - title: {title}
        - description: {description or ""}
        - audience: {audience or "general learners"}
        - reading_level: {reading_level or "standard"}
        - country: {country or ""}
        - tone: {tone or "clear and supportive"}
        - depth: {depth or "beginner-to-intermediate"}
        - target module count: {module_count or "choose an appropriate number"}
        - target lessons per module: {lessons_per_module or "choose an appropriate number"}

        Source materials (may be partial / noisy):
        {json.dumps(doc_chunks, ensure_ascii=False)}

        Output MUST be valid JSON only (no markdown, no extra text) with this schema:
        {{
          "course": {{
            "title": string,
            "description": string,
            "learning_outcomes": string[]
          }},
          "modules": [
            {{
              "sort_order": number,
              "title": string,
              "description": string,
              "learning_objectives": string[],
              "lessons": [
                {{
                  "sort_order": number,
                  "title": string
                }}
              ]
            }}
          ]
        }}
        """
    ).strip()

def _build_module_content_prompt(
    *,
    outline_json: dict,
    module_sort_order: int,
    module_title: str,
    module_description: str | None,
    module_learning_objectives: list[str],
    lesson_titles: list[str],
    language: str,
) -> str:
    return dedent(
        f"""
        You are an expert course author.

        Write the full lesson content for a single module in {language}.
        Use the full course outline for context but ONLY generate content for the requested module.

        Full course outline (JSON):
        {json.dumps(outline_json, ensure_ascii=False)}

        Target module:
        - sort_order: {module_sort_order}
        - title: {module_title}
        - description: {module_description or ""}
        - learning_objectives: {json.dumps(module_learning_objectives, ensure_ascii=False)}
        - lesson_titles: {json.dumps(lesson_titles, ensure_ascii=False)}

        Output MUST be valid JSON only (no markdown, no extra text) with this schema:
        {{
          "lessons": [
            {{
              "sort_order": number,
              "title": string,
              "blocks": [
                {{
                  "type": "heading" | "paragraph" | "key_takeaways" | "summary",
                  "content": string,
                  "items": string[]?
                }}
              ]
            }}
          ]
        }}
        Rules:
        - Each lesson must have multiple paragraphs and end with key_takeaways + summary blocks.
        - Use "heading" blocks to structure within a lesson.
        - For "key_takeaways", put bullet items in "items" (string[]), and set "content" to an empty string.
        """
    ).strip()


def _build_module_quiz_prompt(
    *,
    module_title: str,
    module_learning_objectives: list[str],
    lesson_material: list[dict],
    quiz_settings: dict,
    language: str,
) -> str:
    return dedent(
        f"""
        You are an assessment designer.

        Create a quiz in {language} for the module below, based ONLY on the provided lesson material.

        Module:
        - title: {module_title}
        - learning_objectives: {json.dumps(module_learning_objectives, ensure_ascii=False)}

        Lesson material (JSON):
        {json.dumps(lesson_material, ensure_ascii=False)}

        Quiz settings (JSON):
        {json.dumps(quiz_settings, ensure_ascii=False)}

        Output MUST be valid JSON only (no markdown, no extra text) with this schema:
        {{
          "questions": [
            {{
              "question": string,
              "choices": string[],
              "answer_index": number,
              "explanation": string
            }}
          ]
        }}
        Rules:
        - choices length must match settings.num_choices when provided, otherwise use 4
        - answer_index must be a valid index into choices
        - questions must test the module learning objectives and lesson content
        """
    ).strip()


def generate_course_with_claude(payload) -> Tuple[str, str]:
    """
    Generate a course outline using Anthropic Claude.

    Returns a tuple of (outline_markdown).
    """
    client = _get_client()
    prompt = dedent(
        f"""
        You are an expert instructional designer helping to design an online course.

        Design a complete course for the topic: "{payload.topic}".

        Target audience: {getattr(payload, "target_audience", None) or "a general audience of learners"}
        Difficulty level: {getattr(payload, "difficulty", None) or "beginner"}
        Language: {getattr(payload, "language", "en")}

        Respond with a clear, human-readable course outline as markdown.
        """
    ).strip()

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0.7,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    outline = _extract_text(message)

    return outline


def generate_course_outline_structured(payload) -> tuple[dict, str, str]:
    """
    Step 1: Generate structured outline JSON.

    Returns (outline_json, raw_text).
    """
    client = _get_client()

    prompt = _build_outline_prompt(
        doc_chunks=getattr(payload, "doc_chunks", []) or [],
        title=payload.title,
        description=getattr(payload, "description", None),
        audience=getattr(payload, "audience", None),
        reading_level=getattr(payload, "reading_level", None),
        country=getattr(payload, "country", None),
        tone=getattr(payload, "tone", None),
        depth=getattr(payload, "depth", None),
        module_count=getattr(payload, "module_count", None),
        lessons_per_module=getattr(payload, "lessons_per_module", None),
        language=getattr(payload, "language", "en"),
    )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0.4,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_text(message)
    outline_json = _parse_json_strict(raw)
    return outline_json, raw


def generate_module_content_structured(payload) -> tuple[dict, str, str]:
    """
    Step 2: Generate per-module lesson content JSON.

    Returns (module_content_json, raw_text).
    """
    client = _get_client()

    prompt = _build_module_content_prompt(
        outline_json=payload.outline_json,
        module_sort_order=payload.module_sort_order,
        module_title=payload.module_title,
        module_description=getattr(payload, "module_description", None),
        module_learning_objectives=getattr(payload, "module_learning_objectives", []) or [],
        lesson_titles=getattr(payload, "lesson_titles", []) or [],
        language=getattr(payload, "language", "en"),
    )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8192,
        temperature=0.6,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_text(message)
    module_content_json = _parse_json_strict(raw)
    return module_content_json, raw


def generate_module_quiz_structured(payload) -> tuple[dict, str, str]:
    """
    Step 3: Generate per-module quiz JSON.

    Returns (quiz_json, raw_text).
    """
    client = _get_client()

    prompt = _build_module_quiz_prompt(
        module_title=payload.module_title,
        module_learning_objectives=getattr(payload, "module_learning_objectives", []) or [],
        lesson_material=getattr(payload, "lesson_material", []) or [],
        quiz_settings=getattr(payload, "quiz_settings", {}) or {},
        language=getattr(payload, "language", "en"),
    )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0.4,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_text(message)
    quiz_json = _parse_json_strict(raw)
    return quiz_json, raw

