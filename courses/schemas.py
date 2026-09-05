"""
The single source of truth for what a generated course/chapter/quiz looks
like. Both the mock fallback generator and real Gemini output must validate
against this schema — see courses/services.py::_validate_response.

Gemini must never write directly to the database. The flow is always:
    raw AI/mock output -> this schema -> application-level checks -> preview -> DB
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class GeneratedKeyTerm(BaseModel):
    term: str = Field(min_length=1, max_length=100)
    definition: str = Field(min_length=10, max_length=500)
    source_reference: Optional[str] = None


class GeneratedFact(BaseModel):
    text: str = Field(min_length=10, max_length=500)
    source_reference: Optional[str] = None


class GeneratedAnalogy(BaseModel):
    label: str
    explanation: str
    source_reference: Optional[str] = None


class GeneratedTimelineItem(BaseModel):
    period: str
    title: str
    description: str


class GeneratedComparisonRow(BaseModel):
    criterion: str
    values: list[str]


class GeneratedComparison(BaseModel):
    title: str
    columns: list[str]
    rows: list[GeneratedComparisonRow]


class GeneratedConfusion(BaseModel):
    concept_a: str
    concept_b: str
    difference: str


class GeneratedChoice(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    is_correct: bool


class GeneratedQuestion(BaseModel):
    order: int
    text: str = Field(min_length=1, max_length=500)
    difficulty: Literal["easy", "medium", "hard"]
    choices: list[GeneratedChoice] = Field(min_length=2, max_length=4)
    explanation: str = Field(min_length=10, max_length=800)

    @model_validator(mode="after")
    def validate_correct_choice(self):
        correct_count = sum(choice.is_correct for choice in self.choices)
        if correct_count != 1:
            raise ValueError(
                f"Question '{self.text[:40]}...' must have exactly one "
                f"correct choice, found {correct_count}."
            )
        texts_lower = [c.text.strip().lower() for c in self.choices]
        if len(texts_lower) != len(set(texts_lower)):
            raise ValueError(
                f"Question '{self.text[:40]}...' has duplicate choice text."
            )
        return self


class GeneratedQuiz(BaseModel):
    title: str
    questions: list[GeneratedQuestion] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_no_duplicate_questions(self):
        texts_lower = [q.text.strip().lower() for q in self.questions]
        if len(texts_lower) != len(set(texts_lower)):
            raise ValueError(f"Quiz '{self.title}' has duplicate question text.")
        return self


class GeneratedChapter(BaseModel):
    order: int
    title: str = Field(min_length=1, max_length=200)
    overview: str = Field(min_length=10, max_length=600)

    key_terms: list[GeneratedKeyTerm] = []
    analogy: Optional[GeneratedAnalogy] = None
    quick_facts: list[GeneratedFact] = []
    timeline: list[GeneratedTimelineItem] = []
    comparisons: list[GeneratedComparison] = []
    real_world_examples: list[GeneratedFact] = []
    common_confusions: list[GeneratedConfusion] = []

    estimated_minutes: int = Field(ge=2, le=30)
    quiz: GeneratedQuiz


class GeneratedCourse(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=300)
    source_type: Literal[
        "syllabus", "module", "lecture_notes", "assignment", "reviewer", "other",
    ]
    difficulty: Literal["beginner", "intermediate", "advanced"]


class GeneratedJourney(BaseModel):
    schema_version: Literal["1.0"]
    course: GeneratedCourse
    chapters: list[GeneratedChapter] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sequential_chapter_order(self):
        orders = [c.order for c in self.chapters]
        expected = list(range(1, len(self.chapters) + 1))
        if orders != expected:
            raise ValueError(
                f"Chapter order values must be sequential starting at 1, "
                f"got {orders}."
            )
        return self
