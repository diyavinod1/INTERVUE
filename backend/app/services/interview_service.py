"""
InterviewService: the seam between the FastAPI layer, the LangGraph
orchestration engine, and the database (PRD Sec. 44 - API -> Service ->
Agent -> Provider -> Database).

Every public method here does the same three things in order:
  1. Rehydrate an InterviewState from the database (candidate profile, job
     profile, plan, full conversation history so far).
  2. Invoke the compiled LangGraph with that state for exactly one
     transition (either "generate the opening question" or "process this
     answer and produce whatever comes next").
  3. Persist whatever the graph changed back to Postgres/SQLite.

The graph itself never imports SQLAlchemy - it only ever sees the
InterviewState TypedDict, which is what makes the orchestration logic
independently testable (see tests/) without a database at all.
"""
from fastapi import HTTPException

from app.agents.graph import interview_graph
from app.agents.nodes.final_report import generate_final_report_node
from app.core.config import get_settings
from app.core.security import validate_resume_upload
from app.models.interview import Interview
from app.repositories import interview_repository as repo
from app.schemas.candidate import CandidateProfile, JobProfile
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview import InterviewLength, InterviewMode
from app.schemas.interview_plan import InterviewPlan
from app.services import jd_service, resume_service
from app.services.voice_service import count_filler_words


async def create_interview(
    db,
    *,
    full_name: str,
    target_role: str,
    experience_level: str,
    job_description: str,
    resume_filename: str,
    resume_bytes: bytes,
    interview_length: InterviewLength = InterviewLength.STANDARD,
) -> Interview:
    resume_text = resume_service.extract_text(resume_filename, resume_bytes)
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from the resume file.")

    candidate_profile = resume_service.build_candidate_profile(resume_text)
    job_profile = jd_service.build_job_profile(job_description, target_role)

    candidate = repo.create_candidate(
        db,
        full_name=full_name,
        target_role=target_role,
        experience_level=experience_level,
        resume_filename=resume_filename,
        resume_raw_text=resume_text,
        resume_profile=candidate_profile,
        job_description_text=job_description,
        job_profile=job_profile,
    )

    settings = get_settings()
    question_limits = {
        InterviewLength.QUICK: 5,
        InterviewLength.STANDARD: 8,
        InterviewLength.DEEP: 12,
        # Adaptive has a ceiling of 12; the decision node can finish earlier
        # once it has enough evidence from the candidate.
        InterviewLength.ADAPTIVE: settings.max_questions,
    }
    question_limit = question_limits[interview_length]
    interview = repo.create_interview(
        db,
        candidate_id=candidate.id,
        question_limit=question_limit,
        question_strategy=interview_length.value,
    )
    return interview


async def start_interview(db, *, interview_id: str, mode: InterviewMode) -> Interview:
    interview = _get_interview_or_404(db, interview_id)
    if interview.status != "created":
        raise HTTPException(status_code=400, detail="This interview has already been started.")

    candidate = repo.get_candidate(db, interview.candidate_id)
    state = {
        "interview_id": interview.id,
        "candidate_id": candidate.id,
        "candidate_name": candidate.full_name,
        "candidate_profile": CandidateProfile.model_validate(candidate.resume_profile),
        "candidate_resume_text": candidate.resume_raw_text or "",
        "job_profile": JobProfile.model_validate(candidate.job_profile),
        "interview_plan": InterviewPlan(question_strategy=(interview.interview_plan or {}).get("question_strategy", "standard")),
        "question_strategy": (interview.interview_plan or {}).get("question_strategy", "standard"),
        "phase": "start",
        "interview_mode": mode.value,
        "current_topic": "",
        "current_topic_source": "resume",
        "current_difficulty": "easy",
        "question_history": [],
        "answer_history": [],
        "evaluation_history": [],
        "conversation_history": [],
        "covered_topics": [],
        "topic_scores": {},
        "overall_score": 0.0,
        "consecutive_strong": 0,
        "consecutive_weak": 0,
        "questions_asked": 0,
        "question_limit": interview.question_limit,
        "question_strategy": (interview.interview_plan or {}).get("question_strategy", "standard"),
        "interview_status": "created",
    }

    result_state = await interview_graph.ainvoke(state)

    repo.create_question(
        db,
        interview_id=interview.id,
        sequence_index=1,
        topic=result_state["current_topic"],
        difficulty=result_state["current_difficulty"],
        text=result_state["generated_question"],
        action_type="OPENING_QUESTION",
        reason={"type": "opening", "opening_focus": result_state["interview_plan"].opening_focus},
    )
    interview = repo.save_interview_state(db, interview, result_state)
    return interview


async def submit_answer(
    db,
    *,
    interview_id: str,
    answer_text: str,
    mode: InterviewMode,
    audio_duration_seconds: float | None,
    response_latency_ms: int | None,
) -> Interview:
    interview = _get_interview_or_404(db, interview_id)
    if interview.status == "completed":
        raise HTTPException(status_code=400, detail="This interview has already finished.")
    if interview.status != "in_progress":
        raise HTTPException(status_code=400, detail="Interview has not been started yet.")

    question = repo.get_latest_unanswered_question(db, interview.id)
    if question is None:
        raise HTTPException(status_code=400, detail="There is no pending question to answer.")

    state = await _rehydrate_state(db, interview, phase="answer_submitted")
    state["current_question"] = question.text
    state["current_topic"] = question.topic
    state["current_difficulty"] = question.difficulty
    state["current_answer"] = answer_text
    state["interview_mode"] = mode.value

    result_state = await interview_graph.ainvoke(state)

    # Read the evaluation from evaluation_history rather than
    # current_evaluation: within a single graph invocation, generate_question
    # (which runs after decide_next_action when the interview continues) may
    # execute after evaluate_answer set current_evaluation, so history is the
    # reliable place to find "the evaluation that was just produced."
    evaluation_dict = result_state["evaluation_history"][-1]
    evaluation = AnswerEvaluation.model_validate(evaluation_dict)
    word_count = len(answer_text.split())
    answer_row = repo.create_answer(
        db,
        question_id=question.id,
        interview_id=interview.id,
        text=answer_text,
        mode=mode.value,
        audio_duration_seconds=audio_duration_seconds,
        word_count=word_count,
        filler_word_count=count_filler_words(answer_text),
        response_latency_ms=response_latency_ms,
    )
    repo.create_evaluation(db, answer_id=answer_row.id, interview_id=interview.id, evaluation=evaluation)

    if result_state.get("next_action") == "FINISH_INTERVIEW":
        repo.save_final_report(db, interview_id=interview.id, report=result_state["final_report"])
    else:
        repo.create_question(
            db,
            interview_id=interview.id,
            sequence_index=result_state["questions_asked"],
            topic=result_state["current_topic"],
            difficulty=result_state["current_difficulty"],
            text=result_state["generated_question"],
            action_type=result_state.get("next_action", "FOLLOW_UP"),
        )

    interview = repo.save_interview_state(db, interview, result_state)
    return interview


async def finish_interview_early(db, *, interview_id: str) -> Interview:
    """Used by POST /finish - the candidate (or the frontend, on question
    limit reached) ends the interview without answering another question.
    Skips evaluate/decide (there's no new answer) and goes straight to
    report generation from whatever has been recorded so far."""
    interview = _get_interview_or_404(db, interview_id)
    if interview.status == "completed":
        return interview

    state = await _rehydrate_state(db, interview, phase="answer_submitted")
    if not state["conversation_history"]:
        raise HTTPException(status_code=400, detail="Cannot finish an interview with no answered questions yet.")

    result_state = await generate_final_report_node(state)
    repo.save_final_report(db, interview_id=interview.id, report=result_state["final_report"])
    interview = repo.save_interview_state(db, interview, result_state)
    return interview


def get_interview_or_404(db, interview_id: str) -> Interview:
    return _get_interview_or_404(db, interview_id)


def set_mode(db, interview_id: str, mode: InterviewMode) -> Interview:
    """Mode is a presentation-layer preference only (PRD Sec. 24) - it never
    touches interview_plan/topic/difficulty/history, so switching mode mid-
    interview can never reset progress."""
    interview = _get_interview_or_404(db, interview_id)
    return repo.set_interview_mode(db, interview, mode.value)


def validate_upload(file, raw_bytes: bytes) -> None:
    validate_resume_upload(file, raw_bytes)


# ---- internal helpers ----
def _get_interview_or_404(db, interview_id: str) -> Interview:
    interview = repo.get_interview(db, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return interview


def build_conversation_messages(db, interview_id: str) -> list[dict]:
    """Flattens the question/answer rows into an ordered chat transcript for
    the frontend - this is what makes voice answers ALSO show up as text
    (PRD Sec. 11, 26): every answer, regardless of mode, is stored as text
    and rendered the same way."""
    questions = repo.get_all_questions(db, interview_id)
    messages: list[dict] = []
    for q in questions:
        messages.append(
            {
                "role": "interviewer",
                "text": q.text,
                "topic": q.topic,
                "difficulty": q.difficulty,
                "mode": None,
                "created_at": q.created_at,
            }
        )
        if q.answer is not None:
            messages.append(
                {
                    "role": "candidate",
                    "text": q.answer.text,
                    "topic": q.topic,
                    "difficulty": q.difficulty,
                    "mode": q.answer.mode,
                    "created_at": q.answer.created_at,
                }
            )
    return messages


def build_final_report_response(db, interview: Interview) -> dict:
    report_row = repo.get_final_report(db, interview.id)
    if report_row is None:
        raise HTTPException(status_code=404, detail="Final report is not available yet - finish the interview first.")

    candidate = repo.get_candidate(db, interview.candidate_id)
    questions = repo.get_all_questions(db, interview.id)
    qa_history = []
    for q in questions:
        if q.answer is not None and q.answer.evaluation is not None:
            qa_history.append(
                {
                    "topic": q.topic,
                    "difficulty": q.difficulty,
                    "question": q.text,
                    "answer": q.answer.text,
                    "score": q.answer.evaluation.overall_score,
                    "feedback": q.answer.evaluation.feedback,
                }
            )

    return {
        "interview_id": str(interview.id),
        "candidate_name": candidate.full_name,
        "target_role": candidate.target_role,
        "overall_score": report_row.overall_score,
        "topic_scores": report_row.topic_scores,
        "strengths": report_row.strengths,
        "weaknesses": report_row.weaknesses,
        "technical_gaps": report_row.technical_gaps,
        "recommended_learning_areas": report_row.recommended_learning_areas,
        "question_count": report_row.question_count,
        "summary": report_row.summary,
        "qa_history": qa_history,
    }


async def _rehydrate_state(db, interview: Interview, *, phase: str) -> dict:
    candidate = repo.get_candidate(db, interview.candidate_id)
    questions = repo.get_all_questions(db, interview.id)

    conversation_history = []
    question_history = []
    answer_history = []
    evaluation_history = []
    for q in questions:
        question_history.append(q.text)
        if q.answer is not None:
            answer_history.append(q.answer.text)
            if q.answer.evaluation is not None:
                ev = q.answer.evaluation
                ev_dict = {
                    "overall_score": ev.overall_score,
                    "correctness": ev.correctness,
                    "completeness": ev.completeness,
                    "technical_depth": ev.technical_depth,
                    "relevance": ev.relevance,
                    "clarity": ev.clarity,
                    "strengths": ev.strengths,
                    "weaknesses": ev.weaknesses,
                    "missing_concepts": ev.missing_concepts,
                    "feedback": ev.feedback,
                    "recommended_action": ev.recommended_action,
                }
                evaluation_history.append(ev_dict)
                conversation_history.append(
                    {
                        "question": q.text,
                        "answer": q.answer.text,
                        "topic": q.topic,
                        "difficulty": q.difficulty,
                        "evaluation": ev_dict,
                    }
                )

    return {
        "interview_id": interview.id,
        "candidate_id": candidate.id,
        "candidate_name": candidate.full_name,
        "candidate_profile": CandidateProfile.model_validate(candidate.resume_profile),
        "candidate_resume_text": candidate.resume_raw_text or "",
        "job_profile": JobProfile.model_validate(candidate.job_profile),
        "interview_plan": InterviewPlan.model_validate(interview.interview_plan) if interview.interview_plan else InterviewPlan(),
        "question_strategy": (interview.interview_plan or {}).get("question_strategy", "standard"),
        "phase": phase,
        "interview_mode": interview.mode,
        "current_topic": interview.current_topic,
        "current_topic_source": next(
            (t.source for t in (InterviewPlan.model_validate(interview.interview_plan).topics if interview.interview_plan else [])
             if t.name == interview.current_topic),
            "resume",
        ),
        "current_difficulty": interview.current_difficulty,
        "question_history": question_history,
        "answer_history": answer_history,
        "evaluation_history": evaluation_history,
        "conversation_history": conversation_history,
        "covered_topics": list(interview.covered_topics or []),
        "topic_scores": dict(interview.topic_scores or {}),
        "overall_score": interview.overall_score,
        "consecutive_strong": interview.consecutive_strong,
        "consecutive_weak": interview.consecutive_weak,
        "questions_asked": interview.questions_asked,
        "question_limit": interview.question_limit,
        "question_strategy": (interview.interview_plan or {}).get("question_strategy", "standard"),
        "interview_status": interview.status,
    }
