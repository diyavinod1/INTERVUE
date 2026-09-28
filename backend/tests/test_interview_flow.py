import pytest

from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview import InterviewMode
from app.services import interview_service, llm_service, resume_service, jd_service

pytestmark = pytest.mark.asyncio

# Captured before any fixture monkeypatches LLMService.evaluate_answer, so the
# LLM-failure test below can restore the REAL implementation (which contains
# the try/except fallback we want to exercise) after the mock_llm fixture
# has replaced it with a canned response.
_REAL_EVALUATE_ANSWER = llm_service.LLMService.evaluate_answer

SAMPLE_RESUME = """
Jane Doe

PROJECTS
Inventory API: Built a REST API for inventory management using FastAPI and PostgreSQL.

SKILLS
Python, FastAPI, PostgreSQL, React
"""

SAMPLE_JD = """
Requirements
Python
FastAPI
PostgreSQL
"""


@pytest.fixture()
def mock_llm(monkeypatch):
    """Replaces every LLM-dependent call with deterministic, controllable
    behavior so tests never hit the network. `score_queue` lets a test
    script exactly which evaluation score comes back for each successive
    answer."""
    state = {"score_queue": []}

    async def fake_plan_rationales(self, *, candidate_context, job_context, topic_names):
        return {"rationales": {n: f"Explores {n}." for n in topic_names}, "opening_focus": topic_names[0]}

    async def fake_opening_question(self, *, candidate_name, candidate_context, job_context, opening_focus):
        return f"Hi {candidate_name}, let's start with {opening_focus}."

    async def fake_generate_question(self, **kwargs):
        return f"[{kwargs['action']}] Tell me more about {kwargs['current_topic']}."

    async def fake_evaluate(self, *, topic, difficulty, question, answer):
        score = state["score_queue"].pop(0) if state["score_queue"] else 6.0
        return AnswerEvaluation(
            overall_score=score, correctness=score, completeness=score,
            technical_depth=score, relevance=score, clarity=score,
        )

    async def fake_final_report(self, **kwargs):
        return {
            "summary": "Solid overall performance.",
            "strengths": ["Good FastAPI knowledge"],
            "weaknesses": ["Could go deeper on PostgreSQL"],
            "technical_gaps": ["Indexing strategies"],
            "recommended_learning_areas": ["Database indexing"],
        }

    monkeypatch.setattr(llm_service.LLMService, "generate_plan_rationales", fake_plan_rationales)
    monkeypatch.setattr(llm_service.LLMService, "generate_opening_question", fake_opening_question)
    monkeypatch.setattr(llm_service.LLMService, "generate_question", fake_generate_question)
    monkeypatch.setattr(llm_service.LLMService, "evaluate_answer", fake_evaluate)
    monkeypatch.setattr(llm_service.LLMService, "generate_final_report_narrative", fake_final_report)

    return state


async def _create_test_interview(db):
    resume_text = SAMPLE_RESUME
    profile = resume_service.build_candidate_profile(resume_text)
    job_profile = jd_service.build_job_profile(SAMPLE_JD, target_role="Backend Developer")

    from app.repositories import interview_repository as repo

    candidate = repo.create_candidate(
        db, full_name="Jane Doe", target_role="Backend Developer", experience_level="1-2 Years",
        resume_filename="resume.pdf", resume_raw_text=resume_text, resume_profile=profile,
        job_description_text=SAMPLE_JD, job_profile=job_profile,
    )
    interview = repo.create_interview(db, candidate_id=candidate.id, question_limit=4)
    return interview


async def test_full_interview_lifecycle(db_session, mock_llm):
    interview = await _create_test_interview(db_session)

    # 1. Starting the interview produces an opening question and moves status forward.
    interview = await interview_service.start_interview(db_session, interview_id=interview.id, mode=InterviewMode.TEXT)
    assert interview.status == "in_progress"
    assert interview.questions_asked == 1

    # 2. A strong answer should push difficulty up one level (from the plan's
    #    initial "easy" opening topic) - deterministic decision logic.
    mock_llm["score_queue"] = [9.0]
    interview = await interview_service.submit_answer(
        db_session, interview_id=interview.id, answer_text="A thorough, correct answer.",
        mode=InterviewMode.TEXT, audio_duration_seconds=None, response_latency_ms=None,
    )
    assert interview.current_difficulty == "medium"
    assert interview.questions_asked == 2

    # 3. Candidate switches to voice mode mid-interview - progress must not reset.
    interview = interview_service.set_mode(db_session, interview.id, InterviewMode.VOICE)
    assert interview.mode == "voice"
    assert interview.questions_asked == 2  # unchanged by a mode switch

    # 4. A weak voice answer.
    mock_llm["score_queue"] = [3.0]
    interview = await interview_service.submit_answer(
        db_session, interview_id=interview.id, answer_text="Not sure, maybe X?",
        mode=InterviewMode.VOICE, audio_duration_seconds=12.4, response_latency_ms=1500,
    )
    assert interview.questions_asked == 3

    # 5. One more answer reaches the question limit (4) and finishes the interview.
    mock_llm["score_queue"] = [7.0]
    interview = await interview_service.submit_answer(
        db_session, interview_id=interview.id, answer_text="A reasonable answer.",
        mode=InterviewMode.TEXT, audio_duration_seconds=None, response_latency_ms=None,
    )
    assert interview.status == "in_progress"  # question 4 has been asked, not yet answered

    mock_llm["score_queue"] = [7.0]
    interview = await interview_service.submit_answer(
        db_session, interview_id=interview.id, answer_text="A reasonable final answer.",
        mode=InterviewMode.TEXT, audio_duration_seconds=None, response_latency_ms=None,
    )
    assert interview.status == "completed"

    report = interview_service.build_final_report_response(db_session, interview)
    assert report["candidate_name"] == "Jane Doe"
    assert report["question_count"] == 4
    assert "Database indexing" in report["recommended_learning_areas"]

    # The full conversation (across both text and voice turns) must be intact.
    conversation = interview_service.build_conversation_messages(db_session, interview.id)
    assert len(conversation) == 8  # 4 questions + 4 answers
    assert conversation[0]["role"] == "interviewer"
    assert any(m["mode"] == "voice" for m in conversation)


async def test_llm_failure_falls_back_gracefully(db_session, monkeypatch, mock_llm):
    """If the underlying OpenRouter call fails entirely, LLMService.evaluate_answer's
    own try/except should catch it and return the neutral fallback evaluation
    instead of crashing the interview (PRD Sec. 39) - so we restore the REAL
    evaluate_answer implementation here (mock_llm's fixture replaces it with a
    canned response, which would hide the very fallback path we're testing)."""
    from app.providers.llm.openrouter import LLMProviderError, OpenRouterProvider

    monkeypatch.setattr(llm_service.LLMService, "evaluate_answer", _REAL_EVALUATE_ANSWER)

    async def always_fail(self, model, messages, temperature, max_tokens, json_mode):
        raise LLMProviderError("simulated total LLM outage")

    monkeypatch.setattr(OpenRouterProvider, "_call_once", always_fail)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    interview = await _create_test_interview(db_session)
    interview = await interview_service.start_interview(db_session, interview_id=interview.id, mode=InterviewMode.TEXT)

    # evaluate_answer_node calls the REAL llm_service.evaluate_answer, which
    # catches the LLMProviderError internally and returns _fallback_evaluation
    # - so this must NOT raise, and the interview must keep moving.
    interview = await interview_service.submit_answer(
        db_session, interview_id=interview.id, answer_text="Some answer despite the outage.",
        mode=InterviewMode.TEXT, audio_duration_seconds=None, response_latency_ms=None,
    )
    assert interview.status in ("in_progress", "completed")
