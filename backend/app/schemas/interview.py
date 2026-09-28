from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from app.schemas.candidate import SetupInterviewRequest  # re-exported for convenience


class InterviewLength(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"
    ADAPTIVE = "adaptive"


class InterviewMode(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class InterviewStatus(StrEnum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class CreateInterviewRequest(SetupInterviewRequest):
    """Body of POST /api/interviews is the setup form + JD; resume comes via multipart file."""


class CreateInterviewResponse(BaseModel):
    interview_id: str
    candidate_id: str
    full_name: str
    target_role: str
    experience_level: str
    resume_filename: str
    resume_profile: dict
    job_profile: dict


class StartInterviewRequest(BaseModel):
    mode: InterviewMode = InterviewMode.TEXT


class SetModeRequest(BaseModel):
    mode: InterviewMode


class SubmitAnswerRequest(BaseModel):
    text: str
    mode: InterviewMode
    audio_duration_seconds: float | None = None
    response_latency_ms: int | None = None


class ChatMessage(BaseModel):
    role: str  # "interviewer" | "candidate"
    text: str
    topic: str | None = None
    difficulty: str | None = None
    mode: str | None = None
    created_at: datetime


class CurrentQuestionResponse(BaseModel):
    interview_id: str
    status: InterviewStatus
    question_id: str | None
    question_text: str | None
    topic: str | None
    difficulty: str | None
    questions_asked: int
    question_limit: int
    question_strategy: str = "standard"
    mode: InterviewMode
    conversation: list[ChatMessage]


class SubmitAnswerResponse(BaseModel):
    interview_id: str
    status: InterviewStatus
    next_question_id: str | None
    next_question_text: str | None
    topic: str | None
    difficulty: str | None
    action_taken: str
    questions_asked: int
    question_limit: int
    question_strategy: str = "standard"
    conversation: list[ChatMessage]


class InterviewSummaryResponse(BaseModel):
    id: str
    status: InterviewStatus
    mode: InterviewMode
    candidate_name: str
    target_role: str
    questions_asked: int
    question_limit: int
    question_strategy: str = "standard"
    current_topic: str
    overall_score: float
