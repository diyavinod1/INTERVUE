"""
The LangGraph interview state.

This is intentionally a TypedDict (LangGraph's native state container) of
clearly named, typed fields - not one giant unstructured blob (PRD Sec. 17).
Nested structures (candidate_profile, job_profile, interview_plan,
evaluations) are themselves Pydantic models serialized to/from dict at the
service boundary, so every field has a real shape.

Lifecycle: InterviewService builds an InterviewState from the persisted
Interview + Candidate rows before every graph invocation, and writes the
relevant fields back to the database after the graph returns. The graph
itself never talks to the database directly - that keeps orchestration
logic (agents/) cleanly separated from persistence (repositories/,
services/), per PRD Sec. 44.
"""
from typing import Literal, TypedDict

from app.schemas.candidate import CandidateProfile, JobProfile
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_plan import InterviewPlan

Phase = Literal["start", "answer_submitted"]
NextActionLiteral = Literal[
    "FOLLOW_UP",
    "INCREASE_DIFFICULTY",
    "DECREASE_DIFFICULTY",
    "CHANGE_TOPIC",
    "ASK_RESUME_QUESTION",
    "ASK_JOB_SPECIFIC_QUESTION",
    "ASK_BEHAVIORAL_QUESTION",
    "ASK_SITUATIONAL_QUESTION",
    "CLARIFY",
    "FINISH_INTERVIEW",
]


class QAPair(TypedDict):
    question: str
    answer: str
    topic: str
    difficulty: str
    evaluation: dict  # serialized AnswerEvaluation


class InterviewState(TypedDict, total=False):
    # ---- identity ----
    interview_id: str
    candidate_id: str

    # ---- static context (loaded once) ----
    candidate_name: str
    candidate_profile: CandidateProfile
    # Original extracted resume text; unlike candidate_profile this contains
    # the complete source material from the uploaded resume.
    candidate_resume_text: str
    job_profile: JobProfile
    interview_plan: InterviewPlan

    # ---- turn control ----
    phase: Phase
    interview_mode: Literal["text", "voice"]

    # ---- current turn working data ----
    current_topic: str
    current_difficulty: Literal["easy", "medium", "hard"]
    current_topic_source: str
    current_question: str
    current_answer: str
    current_evaluation: AnswerEvaluation | None
    next_action: NextActionLiteral | None

    # ---- rolling memory (bounded - see interview_service for trimming) ----
    question_history: list[str]
    answer_history: list[str]
    evaluation_history: list[dict]
    conversation_history: list[QAPair]
    covered_topics: list[str]

    # ---- scoring ----
    topic_scores: dict[str, float]
    overall_score: float
    consecutive_strong: int
    consecutive_weak: int

    # ---- progress / termination ----
    questions_asked: int
    question_limit: int
    question_strategy: Literal["quick", "standard", "deep", "adaptive"]
    interview_status: Literal["created", "in_progress", "completed"]

    # ---- output of this invocation ----
    generated_question: str | None
    final_report: dict | None
