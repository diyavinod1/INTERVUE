from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class NextAction(StrEnum):
    FOLLOW_UP = "FOLLOW_UP"
    INCREASE_DIFFICULTY = "INCREASE_DIFFICULTY"
    DECREASE_DIFFICULTY = "DECREASE_DIFFICULTY"
    CHANGE_TOPIC = "CHANGE_TOPIC"
    ASK_RESUME_QUESTION = "ASK_RESUME_QUESTION"
    ASK_JOB_SPECIFIC_QUESTION = "ASK_JOB_SPECIFIC_QUESTION"
    CLARIFY = "CLARIFY"
    FINISH_INTERVIEW = "FINISH_INTERVIEW"


class AnswerEvaluation(BaseModel):
    """
    Structured rubric score for a single answer. This is what the evaluator
    LLM call is forced (via structured output / JSON schema prompting) to
    return. Pydantic validation means a malformed LLM response either gets
    coerced into range or raises - never silently corrupts interview state.
    """

    overall_score: float = Field(ge=0, le=10)
    correctness: float = Field(ge=0, le=10)
    completeness: float = Field(ge=0, le=10)
    technical_depth: float = Field(ge=0, le=10)
    relevance: float = Field(ge=0, le=10)
    clarity: float = Field(ge=0, le=10)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missing_concepts: list[str] = Field(default_factory=list)
    feedback: str = ""
    recommended_action: NextAction = NextAction.FOLLOW_UP

    @field_validator("overall_score", "correctness", "completeness", "technical_depth", "relevance", "clarity", mode="before")
    @classmethod
    def clamp_score(cls, v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return 5.0
        return max(0.0, min(10.0, v))
