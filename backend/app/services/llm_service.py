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
        latest_answer_analysis: str = "",
        latest_answer: str = "",
        latest_question: str = "",
    ) -> str:
        try:
            analysis_text = latest_answer_analysis
            if not analysis_text and latest_answer:
                analysis_text = f"LATEST QUESTION ASKED: {latest_question}\nCANDIDATE'S ACTUAL ANSWER: {latest_answer}"

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
                    "latest_answer_analysis": analysis_text or "(No previous answer in this turn.)",
                },
                temperature=0.65,
                max_tokens=350,
                json_mode=False,
            )
            return raw.strip().strip('"')
        except LLMProviderError as e:
            logger.error("question_generation_failed error=%s -- using context-aware fallback", e)
            return _fallback_question(current_topic, current_difficulty, action, latest_answer=latest_answer)

    async def generate_opening_question(
        self, *, candidate_name: str, candidate_context: str, full_resume: str, job_context: str, opening_focus: str
    ) -> str:
        first_name = candidate_name.split()[0] if candidate_name else "there"
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
                max_tokens=300,
                json_mode=False,
            )
            return raw.strip().strip('"')
        except LLMProviderError as e:
            logger.error("opening_question_generation_failed error=%s -- using human fallback", e)
            if "introduce" in opening_focus.lower() or "career story" in opening_focus.lower():
                return (
                    f"Hi {first_name}, thanks for taking the time to speak today. "
                    "To start off, could you introduce yourself and walk me through the key highlights and experiences most relevant to this role?"
                )
            return (
                f"Hi {first_name}, thanks for joining. I've reviewed your background and would love to start by exploring your work with {opening_focus}. "
                "Could you walk me through the architecture and your primary contributions there?"
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


def _fallback_question(topic: str, difficulty: str, action: str, latest_answer: str = "") -> str:
    """Used only if OpenRouter (primary + fallback model) is fully unreachable.
    Formulates a realistic, professional engineering question grounded in the topic
    rather than asking generic chatbot filler."""
    clean_topic = topic.replace("Resume-wide background", "Core Engineering Projects")

    if action == "ASK_BEHAVIORAL_QUESTION":
        if "introduce" in clean_topic.lower() or "career story" in clean_topic.lower():
            return "To kick things off, could you briefly introduce yourself and walk me through the key projects and milestones that shaped your background?"
        if "motivation" in clean_topic.lower() or "role fit" in clean_topic.lower():
            return "What specifically drew you to this role, and how does it align with the technical challenges you're eager to tackle next?"
        return f"Could you walk me through a situation where you had to lead or navigate {clean_topic.lower()} in a past project or engineering team?"

    if action == "ASK_SITUATIONAL_QUESTION":
        return f"Imagine a high-stakes scenario involving {clean_topic.lower()} where requirements are ambiguous and deadlines are tight. How would you prioritize your initial steps?"

    if action == "CHANGE_TOPIC":
        return f"That gives clear perspective. Let's switch gears over to {clean_topic}—walk me through how you've designed or built components in this area."

    if action == "INCREASE_DIFFICULTY":
        return f"Let's explore the scale and edge cases of {clean_topic}: how would you architect this to guarantee high throughput, fault tolerance, and zero data loss?"

    if action == "DECREASE_DIFFICULTY":
        return f"Let's step back to core architecture: what are the primary building blocks and standard lifecycle when implementing {clean_topic}?"

    if action == "CLARIFY":
        return f"Walk me through the concrete technical mechanics and trade-offs of the approach you just described for {clean_topic}."

    if action == "FOLLOW_UP":
        return f"Looking closer at how you'd execute that in {clean_topic}, what are the most critical failure modes or bottlenecks you would anticipate?"

    return f"Walk me through your practical hands-on experience designing and debugging systems involving {clean_topic}."


def _fallback_evaluation(answer: str) -> AnswerEvaluation:
    """Neutral fallback used only if the evaluator LLM call fails entirely.
    Keeps the interview moving constructively as a FOLLOW_UP without triggering
    artificial clarification traps."""
    word_count = len(answer.split())
    base_score = 6.0 if word_count >= 15 else (5.0 if word_count >= 5 else 4.0)
    return AnswerEvaluation(
        overall_score=base_score,
        correctness=base_score,
        completeness=5.0,
        technical_depth=base_score,
        relevance=5.0,
        clarity=5.0,
        strengths=["Candidate provided a responsive answer."],
        weaknesses=["Automated evaluation was temporarily unavailable; conservative baseline applied."],
        missing_concepts=[],
        feedback="Evaluation service temporarily unavailable; standard baseline score applied.",
        recommended_action="FOLLOW_UP",
    )
