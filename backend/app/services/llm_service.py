"""
LLMService: the one place agent nodes talk to "the LLM."

This is where LangChain actually earns its place in the stack (PRD Sec.
15): ChatPromptTemplate.format_messages() turns our structured context into
well-formed chat messages, and this service converts those into the
provider-agnostic LLMMessage list that providers/llm/openrouter.py sends
over the wire. Swapping OpenRouter for another provider means writing one
new class in providers/llm/ and changing one line in `_provider` below -
nothing in agents/ changes.

Structured-output calls (planner rationale, evaluation, final report) ask
the model for JSON and parse it defensively: models - especially free-tier
ones - sometimes wrap JSON in markdown fences or add stray text, so we
strip fences and take the first {...} block before parsing, and always fall
back to a safe default rather than raising and crashing the interview.
"""
import json
import re

from langchain_core.prompts import ChatPromptTemplate

from app.agents.prompts.evaluator import evaluator_prompt
from app.agents.prompts.final_report import final_report_prompt
from app.agents.prompts.planner import planner_prompt
from app.agents.prompts.question_generator import opening_question_prompt, question_generator_prompt
from app.core.logging import get_logger
from app.providers.llm.base import LLMMessage
from app.providers.llm.openrouter import LLMProviderError, OpenRouterProvider
from app.schemas.evaluation import AnswerEvaluation

logger = get_logger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(raw_text: str) -> dict:
    match = _JSON_BLOCK_RE.search(raw_text)
    if not match:
        raise ValueError(f"No JSON object found in model output: {raw_text[:200]}")
    return json.loads(match.group(0))


class LLMService:
    def __init__(self) -> None:
        # Provider abstraction lives behind this one attribute - see module
        # docstring for how to swap it.
        self._provider = OpenRouterProvider()

    async def _run(self, prompt: ChatPromptTemplate, variables: dict, *, temperature: float, max_tokens: int, json_mode: bool) -> str:
        formatted = prompt.format_messages(**variables)
        messages = [LLMMessage(role=_role_of(m), content=m.content) for m in formatted]
        response = await self._provider.complete(
            messages, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode
        )
        if response.used_fallback:
            logger.info("llm_fallback_used model=%s", response.model_used)
        return response.text

    # ---- Planning ----
    async def generate_plan_rationales(self, *, candidate_context: str, job_context: str, topic_names: list[str]) -> dict:
        try:
            raw = await self._run(
                planner_prompt,
                {
                    "candidate_context": candidate_context,
                    "job_context": job_context,
                    "topic_names": "\n".join(f"- {t}" for t in topic_names),
                },
                temperature=0.4,
                max_tokens=500,
                json_mode=True,
            )
            return _extract_json(raw)
        except (LLMProviderError, ValueError, json.JSONDecodeError) as e:
            logger.warning("plan_rationale_generation_failed error=%s -- using deterministic fallback", e)
            return {
                "rationales": {name: f"Relevant to the {name} area of this role." for name in topic_names},
                "opening_focus": topic_names[0] if topic_names else "background and experience",
            }

    # ---- Question generation ----
    async def generate_question(
        self,
        *,
        candidate_name: str,
        candidate_context: str,
        full_resume: str,
        job_context: str,
        current_topic: str,
        current_difficulty: str,
        action: str,
        topic_source: str,
        recent_conversation: str,
        question_history: list[str],
    ) -> str:
        try:
            raw = await self._run(
                question_generator_prompt,
                {
                    "candidate_name": candidate_name,
                    "candidate_context": candidate_context,
                    "full_resume": full_resume,
                    "job_context": job_context,
                    "current_topic": current_topic,
                    "current_difficulty": current_difficulty,
                    "action": action,
                    "topic_source": topic_source,
                    "recent_conversation": recent_conversation,
                    "question_history": "\n".join(f"- {q}" for q in question_history[-15:]) or "(none yet)",
                },
                temperature=0.8,
                max_tokens=200,
                json_mode=False,
            )
            return raw.strip().strip('"')
        except LLMProviderError as e:
            logger.error("question_generation_failed error=%s -- using deterministic fallback", e)
            return _fallback_question(current_topic, current_difficulty, action)

    async def generate_opening_question(
        self, *, candidate_name: str, candidate_context: str, full_resume: str, job_context: str, opening_focus: str
    ) -> str:
        try:
            raw = await self._run(
                opening_question_prompt,
                {
                    "candidate_name": candidate_name,
                    "candidate_context": candidate_context,
                    "full_resume": full_resume,
                    "job_context": job_context,
                    "opening_focus": opening_focus,
                },
                temperature=0.7,
                max_tokens=220,
                json_mode=False,
            )
            return raw.strip().strip('"')
        except LLMProviderError as e:
            logger.error("opening_question_generation_failed error=%s -- using deterministic fallback", e)
            return (
                f"Hi {candidate_name.split()[0] if candidate_name else 'there'}, thanks for joining. "
                f"I've reviewed your background - let's start with {opening_focus}. "
                f"Could you walk me through your experience with it?"
            )

    # ---- Evaluation ----
    async def evaluate_answer(self, *, topic: str, question_type: str, difficulty: str, question: str, answer: str) -> AnswerEvaluation:
        try:
            raw = await self._run(
                evaluator_prompt,
                {"topic": topic, "question_type": question_type, "difficulty": difficulty, "question": question, "answer": answer},
                temperature=0.2,
                max_tokens=500,
                json_mode=True,
            )
            data = _extract_json(raw)
            return AnswerEvaluation.model_validate(data)
        except (LLMProviderError, ValueError, json.JSONDecodeError) as e:
            logger.error("evaluation_failed error=%s -- using neutral fallback evaluation", e)
            return _fallback_evaluation(answer)

    # ---- Final report ----
    async def generate_final_report_narrative(
        self,
        *,
        candidate_name: str,
        target_role: str,
        overall_score: float,
        topic_scores: dict[str, float],
        evaluation_summaries: str,
    ) -> dict:
        try:
            raw = await self._run(
                final_report_prompt,
                {
                    "candidate_name": candidate_name,
                    "target_role": target_role,
                    "overall_score": round(overall_score, 1),
                    "topic_scores": json.dumps({k: round(v, 1) for k, v in topic_scores.items()}),
                    "evaluation_summaries": evaluation_summaries,
                },
                temperature=0.4,
                max_tokens=700,
                json_mode=True,
            )
            return _extract_json(raw)
        except (LLMProviderError, ValueError, json.JSONDecodeError) as e:
            logger.error("final_report_generation_failed error=%s -- using deterministic fallback", e)
            return {
                "summary": (
                    f"{candidate_name} completed the interview for {target_role} with an overall "
                    f"score of {round(overall_score, 1)}/10 across {len(topic_scores)} topic areas."
                ),
                "strengths": [],
                "weaknesses": [],
                "technical_gaps": [],
                "recommended_learning_areas": list(topic_scores.keys())[:3],
            }


def _role_of(message) -> str:
    # ChatPromptTemplate emits SystemMessage/HumanMessage/AIMessage objects;
    # map them to the plain role strings our provider abstraction expects.
    mapping = {"system": "system", "human": "user", "ai": "assistant"}
    return mapping.get(message.type, "user")


def _fallback_question(topic: str, difficulty: str, action: str) -> str:
    """Used only if OpenRouter (primary + fallback model) is fully
    unreachable, so the interview can still proceed rather than crash."""
    if action == "ASK_BEHAVIORAL_QUESTION":
        if topic == "Introduce yourself & career story":
            return "To start, could you tell me about yourself and walk me through the experiences that have shaped your career so far?"
        if topic == "Motivation & role fit":
            return "What interests you about this role, and what are you hoping to contribute and learn next?"
        return f"Can you tell me about a time you demonstrated {topic.lower()} in a project, internship, or team setting?"
    if action == "ASK_SITUATIONAL_QUESTION":
        return f"Imagine a realistic situation involving {topic.lower()}. What would you do first, and why?"
    if action == "CHANGE_TOPIC":
        return f"Let's move to a different area - can you tell me about your experience with {topic}?"
    if action == "INCREASE_DIFFICULTY":
        return f"Let's go a level deeper on {topic} - what edge cases or trade-offs would you consider?"
    if action == "DECREASE_DIFFICULTY":
        return f"Let's take a step back - can you explain the fundamentals of {topic} in your own words?"
    if action == "CLARIFY":
        return "Could you clarify or expand on what you just said?"
    return f"Can you tell me more about your experience with {topic}?"


def _fallback_evaluation(answer: str) -> AnswerEvaluation:
    """Neutral, conservative fallback used only if the evaluator LLM call
    fails entirely - keeps the interview moving (as FOLLOW_UP) rather than
    silently corrupting scoring state."""
    word_count = len(answer.split())
    base_score = 5.0 if word_count >= 15 else 3.0
    return AnswerEvaluation(
        overall_score=base_score,
        correctness=base_score,
        completeness=base_score,
        technical_depth=base_score,
        relevance=base_score,
        clarity=base_score,
        strengths=[],
        weaknesses=["Automated evaluation was unavailable for this answer."],
        missing_concepts=[],
        feedback="Evaluation service temporarily unavailable; neutral score applied.",
        recommended_action="FOLLOW_UP",
    )
