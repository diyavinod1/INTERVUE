"""
FINAL REPORT node (PRD Sec. 36).

Topic scores, overall score, and question count are deterministic
aggregates already sitting in state (built up turn-by-turn in
decision.py's _record_turn). The only LLM involvement here is writing the
narrative summary and suggested learning areas from that aggregate data -
never re-deriving the numbers themselves, and never speculating about the
candidate's personality or psychological state (enforced in the prompt).
"""
from app.agents.state import InterviewState
from app.services.llm_service import LLMService

_llm = LLMService()


def _summarize_evaluations_for_prompt(state: InterviewState) -> str:
    lines = []
    for turn in state.get("conversation_history", []):
        ev = turn["evaluation"]
        lines.append(
            f"[{turn['topic']} / {turn['difficulty']}] score={ev['overall_score']} "
            f"weaknesses={ev.get('weaknesses', [])} missing={ev.get('missing_concepts', [])}"
        )
    return "\n".join(lines) or "(no answers were recorded)"


async def generate_final_report_node(state: InterviewState) -> InterviewState:
    narrative = await _llm.generate_final_report_narrative(
        candidate_name=state["candidate_name"],
        target_role=state["job_profile"].target_role,
        overall_score=state.get("overall_score", 0.0),
        topic_scores=state.get("topic_scores", {}),
        evaluation_summaries=_summarize_evaluations_for_prompt(state),
    )

    state["final_report"] = {
        "overall_score": state.get("overall_score", 0.0),
        "topic_scores": state.get("topic_scores", {}),
        "question_count": len(state.get("conversation_history", [])),
        "summary": narrative.get("summary", ""),
        "strengths": narrative.get("strengths", []),
        "weaknesses": narrative.get("weaknesses", []),
        "technical_gaps": narrative.get("technical_gaps", []),
        "recommended_learning_areas": narrative.get("recommended_learning_areas", []),
    }
    state["interview_status"] = "completed"
    return state
