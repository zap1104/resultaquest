"""
courses/schemas.py

The single source of truth for StudyQuest curriculum generation.
Both mock fallback generators and Gemini output validate against this schema.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, model_validator

# --------------------------------------------------
# 1. INPUT VALIDATION CONTRACT
# --------------------------------------------------
StudyGoal = Literal["quick_cram", "balanced_review", "deep_learning"]
AssessmentFormat = Literal[
    "multiple_choice", "identification", "enumeration", "essay", "not_sure"
]

class GenerationPreferences(BaseModel):
    study_goal: StudyGoal = "quick_cram"
    assessment_formats: List[AssessmentFormat] = Field(
        default_factory=lambda: ["multiple_choice"]
    )

class GenerationProfile(BaseModel):
    study_goal: StudyGoal
    assessment_formats: List[AssessmentFormat]

# --------------------------------------------------
# 2. QUIZ CONTRACT
# --------------------------------------------------
QuestionType = Literal["multiple_choice", "true_false"]

class GeneratedChoice(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    is_correct: bool

class GeneratedQuestion(BaseModel):
    order: int
    type: QuestionType = "multiple_choice"
    difficulty: Optional[str] = "medium"
    text: str = Field(min_length=5, max_length=500)
    explanation: str = Field(min_length=10, max_length=800)
    choices: List[GeneratedChoice]

    @model_validator(mode="after")
    def validate_question_integrity(self):
        # 1. Choice Count Check
        if self.type == "multiple_choice":
            if not (2 <= len(self.choices) <= 4):
                raise ValueError(
                    f"Question {self.order} (multiple_choice) requires between 2 and 4 choices; got {len(self.choices)}."
                )
        elif self.type == "true_false":
            if len(self.choices) != 2:
                raise ValueError(
                    f"Question {self.order} (true_false) requires exactly 2 choices; got {len(self.choices)}."
                )
            choice_texts = {c.text.strip().lower() for c in self.choices}
            if choice_texts != {"true", "false"}:
                raise ValueError(
                    f"Question {self.order} is true_false but choices are not ['True', 'False']."
                )

        # 2. Single Correct Choice Check
        correct_count = sum(1 for c in self.choices if c.is_correct)
        if correct_count != 1:
            raise ValueError(
                f"Question {self.order} must have exactly 1 correct choice; got {correct_count}."
            )

        # 3. Duplicate Choice Text Check (Fails test_tampered_duplicate_choice_text_is_rejected)
        texts_lower = [c.text.strip().lower() for c in self.choices]
        if len(texts_lower) != len(set(texts_lower)):
            raise ValueError(
                f"Question {self.order} has duplicate choice text."
            )

        return self

class GeneratedQuiz(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    questions: List[GeneratedQuestion] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_no_duplicate_questions(self):
        texts_lower = [q.text.strip().lower() for q in self.questions]
        if len(texts_lower) != len(set(texts_lower)):
            raise ValueError(f"Quiz '{self.title}' has duplicate question text.")
        return self

# --------------------------------------------------
# 3. LESSON CONTENT CONTRACT
# --------------------------------------------------
class GeneratedAnalogy(BaseModel):
    label: Optional[str] = None
    explanation: str
    source_reference: Optional[str] = None

class GeneratedConcept(BaseModel):
    term: str = Field(min_length=1, max_length=150)
    formal_definition: str = Field(min_length=5)
    simple_explanation: str = Field(min_length=5)
    analogy: Optional[str] = None
    examples: Optional[List[str]] = Field(default_factory=list)

class GeneratedSection(BaseModel):
    order: int
    title: str = Field(min_length=1, max_length=200)
    introduction: str = Field(default="")
    concepts: List[GeneratedConcept] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)

class GeneratedKeyTerm(BaseModel):
    term: str = Field(min_length=1, max_length=150)
    definition: str = Field(min_length=5)
    source_reference: Optional[str] = None

class ComparisonRow(BaseModel):
    criterion: str
    values: List[str]

class GeneratedComparison(BaseModel):
    title: str
    columns: List[str]
    rows: List[ComparisonRow]

class GeneratedEnumeration(BaseModel):
    title: str
    prompt: str
    items: List[str]
    order_matters: bool = False
    memory_cue: Optional[str] = None

class GeneratedCommonConfusion(BaseModel):
    concept_a: str
    concept_b: str
    difference: str

class GeneratedChapter(BaseModel):
    order: int
    title: str = Field(min_length=1, max_length=200)
    week_label: Optional[str] = None
    focus: Optional[str] = Field(default="")
    overview: str = Field(min_length=5)
    analogy: Optional[GeneratedAnalogy] = None  # Expected by test_hand_transcribed_chapter_validates
    estimated_minutes: int = Field(default=15, ge=2, le=60)
    learning_objectives: List[str] = Field(default_factory=list)
    sections: List[GeneratedSection] = Field(default_factory=list)
    key_terms: Optional[List[GeneratedKeyTerm]] = Field(default_factory=list)
    comparisons: Optional[List[GeneratedComparison]] = Field(default_factory=list)
    enumerations: Optional[List[GeneratedEnumeration]] = Field(default_factory=list)
    common_confusions: Optional[List[GeneratedCommonConfusion]] = Field(default_factory=list)
    key_takeaways: Optional[List[str]] = Field(default_factory=list)
    quiz: GeneratedQuiz

# --------------------------------------------------
# 4. ROOT JOURNEY CONTRACT
# --------------------------------------------------
class GeneratedCourseMeta(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=500)
    source_type: Optional[str] = "reviewer"
    difficulty: Optional[str] = "intermediate"

class GeneratedJourney(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    generation_profile: Optional[GenerationProfile] = None
    course: GeneratedCourseMeta
    chapters: List[GeneratedChapter] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sequential_chapter_order(self):
        orders = [c.order for c in self.chapters]
        expected = list(range(1, len(self.chapters) + 1))
        if orders != expected:
            raise ValueError(
                f"Chapter order values must be sequential starting at 1; got {orders}."
            )
        return self