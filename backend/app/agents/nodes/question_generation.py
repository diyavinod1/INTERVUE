"""
GENERATE QUESTION node (PRD Sec. 19).
"""
from app.agents.prompts.context import render_candidate_profile, render_full_resume, render_job_profile, render_recent_conversation
from app.agents.state import InterviewState
from app.services.llm_service import LLMService

_llm = LLMService()


async def generate_question_node(state: InterviewState) -> InterviewState:
    profile = state["candidate_profile"]
    job = state["job_profile"]
    candidate_context = render_candidate_profile(profile)
    job_context = render_job_profile(job)

    is_opening = state.get("questions_asked", 0) == 0

    if is_opening:
        question = await _llm.generate_opening_question(
            candidate_name=state["candidate_name"],
            candidate_context=candidate_context,
            full_resume=render_full_resume(state.get("candidate_resume_text", "")),
            job_context=job_context,
            opening_focus=state["interview_plan"].opening_focus or state["current_topic"],
        )
    else:
        question = await _llm.generate_question(
            candidate_name=state["candidate_name"],
            candidate_context=candidate_context,
            full_resume=render_full_resume(state.get("candidate_resume_text", "")),
            job_context=job_context,
            current_topic=state["current_topic"],
            current_difficulty=state["current_difficulty"],
            action=state.get("next_action") or "FOLLOW_UP",
            topic_source=state.get("current_topic_source", "resume"),
            recent_conversation=render_recent_conversation(state.get("conversation_history", [])),
            question_history=state.get("question_history", []),
        )

    state["generated_question"] = question
    state["current_question"] = question
    state["current_answer"] = ""
    state["questions_asked"] = state.get("questions_asked", 0) + 1
    state["interview_status"] = "in_progress"
    return state
