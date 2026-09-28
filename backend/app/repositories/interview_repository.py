"""
Repository layer: the only place raw SQLAlchemy queries happen. Services
call these functions instead of touching `Session` query methods directly -
this is what keeps InterviewService readable and keeps a future swap of the
persistence layer (e.g. moving a table to Supabase's REST API) contained to
one file per aggregate.
"""
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.answer import Answer
from app.models.candidate import Candidate
from app.models.evaluation import Evaluation
from app.models.interview import Interview
from app.models.question import Question
from app.models.report import FinalReport
from app.schemas.candidate import CandidateProfile, JobProfile
from app.schemas.evaluation import AnswerEvaluation


def new_id() -> str:
    return str(uuid.uuid4())


# ---- Candidate ----
def create_candidate(
    db: Session,
    *,
    full_name: str,
    target_role: str,
    experience_level: str,
    resume_filename: str,
    resume_raw_text: str,
    resume_profile: CandidateProfile,
    job_description_text: str,
    job_profile: JobProfile,
) -> Candidate:
    candidate = Candidate(
        id=new_id(),
        full_name=full_name,
        target_role=target_role,
        experience_level=experience_level,
        resume_filename=resume_filename,
        resume_raw_text=resume_raw_text,
        resume_profile=resume_profile.model_dump(),
        job_description_text=job_description_text,
        job_profile=job_profile.model_dump(),
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def get_candidate(db: Session, candidate_id: str) -> Candidate | None:
    return db.get(Candidate, candidate_id)


# ---- Interview ----
def create_interview(db: Session, *, candidate_id: str, question_limit: int, question_strategy: str = "standard") -> Interview:
    interview = Interview(
        id=new_id(),
        candidate_id=candidate_id,
        question_limit=question_limit,
        interview_plan={"question_strategy": question_strategy},
        status="created",
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


def get_interview(db: Session, interview_id: str) -> Interview | None:
    return db.get(Interview, interview_id)


def save_interview_state(db: Session, interview: Interview, state: dict) -> Interview:
    interview.status = state.get("interview_status", interview.status)
    interview.mode = state.get("interview_mode", interview.mode)
    interview.interview_plan = _plan_to_dict(state.get("interview_plan"))
    interview.current_topic = state.get("current_topic", interview.current_topic)
    interview.current_difficulty = state.get("current_difficulty", interview.current_difficulty)
    interview.questions_asked = state.get("questions_asked", interview.questions_asked)
    interview.overall_score = state.get("overall_score", interview.overall_score)
    interview.topic_scores = state.get("topic_scores", interview.topic_scores)
    interview.consecutive_strong = state.get("consecutive_strong", interview.consecutive_strong)
    interview.consecutive_weak = state.get("consecutive_weak", interview.consecutive_weak)
    interview.covered_topics = state.get("covered_topics", interview.covered_topics)

    if interview.status == "in_progress" and interview.started_at is None:
        interview.started_at = datetime.utcnow()
    if interview.status == "completed" and interview.completed_at is None:
        interview.completed_at = datetime.utcnow()

    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


def _plan_to_dict(plan) -> dict:
    if plan is None:
        return {}
    return plan.model_dump() if hasattr(plan, "model_dump") else plan


def set_interview_mode(db: Session, interview: Interview, mode: str) -> Interview:
    interview.mode = mode
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


# ---- Questions / Answers / Evaluations ----
def create_question(
    db: Session, *, interview_id: str, sequence_index: int, topic: str, difficulty: str, text: str,
    action_type: str, reason: dict | None = None,
) -> Question:
    question = Question(
        id=new_id(),
        interview_id=interview_id,
        sequence_index=sequence_index,
        topic=topic,
        difficulty=difficulty,
        text=text,
        action_type=action_type,
        reason=reason or {},
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def get_latest_unanswered_question(db: Session, interview_id: str) -> Question | None:
    questions = (
        db.query(Question)
        .filter(Question.interview_id == interview_id)
        .order_by(Question.sequence_index.desc())
        .all()
    )
    for q in questions:
        if q.answer is None:
            return q
    return None


def get_all_questions(db: Session, interview_id: str) -> list[Question]:
    return (
        db.query(Question)
        .filter(Question.interview_id == interview_id)
        .order_by(Question.sequence_index)
        .all()
    )


def create_answer(
    db: Session, *, question_id: str, interview_id: str, text: str, mode: str,
    audio_duration_seconds: float | None, word_count: int, filler_word_count: int,
    response_latency_ms: int | None,
) -> Answer:
    answer = Answer(
        id=new_id(),
        question_id=question_id,
        interview_id=interview_id,
        text=text,
        mode=mode,
        audio_duration_seconds=audio_duration_seconds,
        word_count=word_count,
        filler_word_count=filler_word_count,
        response_latency_ms=response_latency_ms,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer


def create_evaluation(db: Session, *, answer_id: str, interview_id: str, evaluation: AnswerEvaluation) -> Evaluation:
    row = Evaluation(
        id=new_id(),
        answer_id=answer_id,
        interview_id=interview_id,
        overall_score=evaluation.overall_score,
        correctness=evaluation.correctness,
        completeness=evaluation.completeness,
        technical_depth=evaluation.technical_depth,
        relevance=evaluation.relevance,
        clarity=evaluation.clarity,
        strengths=evaluation.strengths,
        weaknesses=evaluation.weaknesses,
        missing_concepts=evaluation.missing_concepts,
        feedback=evaluation.feedback,
        recommended_action=str(evaluation.recommended_action),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---- Final report ----
def save_final_report(db: Session, *, interview_id: str, report: dict) -> FinalReport:
    existing = db.query(FinalReport).filter(FinalReport.interview_id == interview_id).one_or_none()
    if existing:
        row = existing
    else:
        row = FinalReport(id=new_id(), interview_id=interview_id)

    row.overall_score = report.get("overall_score", 0.0)
    row.topic_scores = report.get("topic_scores", {})
    row.strengths = report.get("strengths", [])
    row.weaknesses = report.get("weaknesses", [])
    row.technical_gaps = report.get("technical_gaps", [])
    row.recommended_learning_areas = report.get("recommended_learning_areas", [])
    row.question_count = report.get("question_count", 0)
    row.summary = report.get("summary", "")

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_final_report(db: Session, interview_id: str) -> FinalReport | None:
    return db.query(FinalReport).filter(FinalReport.interview_id == interview_id).one_or_none()
