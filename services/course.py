import os
from textwrap import dedent
from typing import Tuple

from anthropic import Anthropic


CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")


def _build_prompt(
    topic: str,
    target_audience: str | None,
    difficulty: str | None,
    language: str,
) -> str:
    audience = target_audience or "a general audience of learners"
    difficulty = difficulty or "beginner"

    return dedent(
        f"""
        You are an expert instructional designer helping to design an online course.

        Design a complete course for the topic: "{topic}".

        Target audience: {audience}
        Difficulty level: {difficulty}
        Language: {language}

        Respond with a clear, human-readable course outline that roughly maps to:
        - course-level description and learning outcomes
        - modules (2-8), each with a title, summary, and sort order
        - lessons inside each module, each with title, summary, and sort order
        - example quizzes or assessments per module with a few sample questions

        The response should be formatted as markdown with headings for modules and lessons.
        Do not include any explanations about what you are doing, just return the outline.
        """
    ).strip()


def generate_course_with_claude(payload) -> Tuple[str, str]:
    """
    Generate a course outline using Anthropic Claude.

    Returns a tuple of (outline_markdown, model_used).
    """
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("CLAUDE_API_KEY is not set in the environment.")

    client = Anthropic(api_key=api_key)

    prompt = _build_prompt(
        topic=payload.topic,
        target_audience=getattr(payload, "target_audience", None),
        difficulty=getattr(payload, "difficulty", None),
        language=getattr(payload, "language", "en"),
    )

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

    # Claude responses are a list of content blocks; join text blocks together.
    parts = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)

    outline = "\n\n".join(parts).strip()

    return outline, CLAUDE_MODEL

