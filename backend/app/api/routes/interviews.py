"""
Interview routes. Every route is deliberately thin: parse/validate the
request, call InterviewService, shape the response. All real logic lives in
services/ and agents/ (PRD Sec. 30, 44).
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.logging import get_logger
from app.repositories import interview_repository as repo
from app.schemas.interview import (
    ChatMessage,
    CreateInterviewResponse,
    CurrentQuestionResponse,
    InterviewLength,
    InterviewMode,
    InterviewStatus,
    InterviewSummaryResponse,
    SetModeRequest,
    StartInterviewRequest,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.schemas.report import FinalReportResponse
from app.services import interview_service

router = APIRouter(prefix="/api/interviews", tags=["interviews"])
logger = get_logger(__name__)


@router.post("", response_model=CreateInterviewResponse, status_code=201)
async def create_interview(
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    target_role: str = Form(...),
    experience_level: str = Form(...),
    job_description: str = Form(...),
    interview_length: InterviewLength = Form(InterviewLength.STANDARD),
    resume: UploadFile = File(...),
):
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required.")

    raw_bytes = await resume.read()
    interview_service.validate_upload(resume, raw_bytes)

    interview = await interview_service.create_interview(
        db,
        full_name=full_name,
        target_role=target_role,
        experience_level=experience_level,
        job_description=job_description,
        resume_filename=resume.filename,
        resume_bytes=raw_bytes,
        interview_length=interview_length,
    )
    candidate = repo.get_candidate(db, interview.candidate_id)
    logger.info("interview_created interview_id=%s candidate_id=%s", interview.id, candidate.id)

    return CreateInterviewResponse(
        interview_id=str(interview.id),
        candidate_id=str(candidate.id),
        full_name=candidate.full_name,
        target_role=candidate.target_role,
        experience_level=candidate.experience_level,
        resume_filename=candidate.resume_filename,
        resume_profile=candidate.resume_profile,
        job_profile=candidate.job_profile,
    )


@router.get("/{interview_id}", response_model=InterviewSummaryResponse)
def get_interview(interview_id: str, db: Session = Depends(get_db)):
    interview = interview_service.get_interview_or_404(db, interview_id)
    candidate = repo.get_candidate(db, interview.candidate_id)
    return InterviewSummaryResponse(
        id=str(interview.id),
        status=InterviewStatus(interview.status),
        mode=InterviewMode(interview.mode),
        candidate_name=candidate.full_name,
        target_role=candidate.target_role,
        questions_asked=interview.questions_asked,
        question_limit=interview.question_limit,
        question_strategy=(interview.interview_plan or {}).get("question_strategy", "standard"),
        current_topic=interview.current_topic,
        overall_score=interview.overall_score,
    )


@router.post("/{interview_id}/start", response_model=CurrentQuestionResponse)
async def start_interview(interview_id: str, body: StartInterviewRequest, db: Session = Depends(get_db)):
    interview = await interview_service.start_interview(db, interview_id=interview_id, mode=body.mode)
    return _current_question_response(db, interview)


@router.get("/{interview_id}/current", response_model=CurrentQuestionResponse)
def get_current(interview_id: str, db: Session = Depends(get_db)):
    interview = interview_service.get_interview_or_404(db, interview_id)
    return _current_question_response(db, interview)


@router.post("/{interview_id}/answer", response_model=SubmitAnswerResponse)
async def submit_answer(interview_id: str, body: SubmitAnswerRequest, db: Session = Depends(get_db)):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Answer text cannot be empty.")

    interview = await interview_service.submit_answer(
        db,
        interview_id=interview_id,
        answer_text=body.text,
        mode=body.mode,
        audio_duration_seconds=body.audio_duration_seconds,
        response_latency_ms=body.response_latency_ms,
    )

    next_question = repo.get_latest_unanswered_question(db, interview.id)
    conversation = interview_service.build_conversation_messages(db, interview.id)
    last_action = next_question.action_type if next_question else "FINISH_INTERVIEW"

    return SubmitAnswerResponse(
        interview_id=str(interview.id),
        status=InterviewStatus(interview.status),
        next_question_id=str(next_question.id) if next_question else None,
        next_question_text=next_question.text if next_question else None,
        topic=interview.current_topic,
        difficulty=interview.current_difficulty,
        action_taken=last_action,
        questions_asked=interview.questions_asked,
        question_limit=interview.question_limit,
        question_strategy=(interview.interview_plan or {}).get("question_strategy", "standard"),
        conversation=[ChatMessage(**m) for m in conversation],
    )


@router.post("/{interview_id}/mode", response_model=InterviewSummaryResponse)
def set_mode(interview_id: str, body: SetModeRequest, db: Session = Depends(get_db)):
    interview = interview_service.set_mode(db, interview_id, body.mode)
    candidate = repo.get_candidate(db, interview.candidate_id)
    return InterviewSummaryResponse(
        id=str(interview.id),
        status=InterviewStatus(interview.status),
        mode=InterviewMode(interview.mode),
        candidate_name=candidate.full_name,
        target_role=candidate.target_role,
        questions_asked=interview.questions_asked,
        question_limit=interview.question_limit,
        question_strategy=(interview.interview_plan or {}).get("question_strategy", "standard"),
        current_topic=interview.current_topic,
        overall_score=interview.overall_score,
    )


@router.post("/{interview_id}/finish", response_model=FinalReportResponse)
async def finish_interview(interview_id: str, db: Session = Depends(get_db)):
    interview = await interview_service.finish_interview_early(db, interview_id=interview_id)
    return interview_service.build_final_report_response(db, interview)


@router.get("/{interview_id}/report", response_model=FinalReportResponse)
def get_report(interview_id: str, db: Session = Depends(get_db)):
    interview = interview_service.get_interview_or_404(db, interview_id)
    return interview_service.build_final_report_response(db, interview)


def _current_question_response(db: Session, interview) -> CurrentQuestionResponse:
    question = repo.get_latest_unanswered_question(db, interview.id)
    conversation = interview_service.build_conversation_messages(db, interview.id)
    return CurrentQuestionResponse(
        interview_id=str(interview.id),
        status=InterviewStatus(interview.status),
        question_id=str(question.id) if question else None,
        question_text=question.text if question else None,
        topic=interview.current_topic,
        difficulty=interview.current_difficulty,
        questions_asked=interview.questions_asked,
        question_limit=interview.question_limit,
        question_strategy=(interview.interview_plan or {}).get("question_strategy", "standard"),
        mode=InterviewMode(interview.mode),
        conversation=[ChatMessage(**m) for m in conversation],
    )
