"""
EVALUATE ANSWER node (PRD Sec. 37).
"""
from app.agents.state import InterviewState
from app.services.llm_service import LLMService

_llm = LLMService()


async def evaluate_answer_node(state: InterviewState) -> InterviewState:
    evaluation = await _llm.evaluate_answer(
        topic=state["current_topic"],
        question_type=state.get("current_topic_source", "technical"),
        difficulty=state["current_difficulty"],
        question=state["current_question"],
        answer=state["current_answer"],
    )
    state["current_evaluation"] = evaluation
    return state
