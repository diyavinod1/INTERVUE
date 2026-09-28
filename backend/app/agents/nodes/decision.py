"""
DECIDE NEXT ACTION + UPDATE STATE node (PRD Sec. 16, 18).

This is the real "agent" in the system. It is almost entirely deterministic
- score thresholds and counters, not another LLM call - because the PRD is
explicit (Sec. 18) that not every decision should cost an LLM round trip,
and because deterministic logic here is exactly what makes the adaptive
behavior testable (see tests/test_decision.py): given the same evaluation
history, the decision is always the same.

The evaluator LLM call *does* propose a `recommended_action` (see
prompts/evaluator.py), but it is advisory only - this node has visibility
into interview-level state (consecutive strong/weak streaks, how many
questions this topic has already had, how many questions remain) that a
single-answer evaluation call does not, so it makes the final call.

Decision rules, in priority order:
  1. Hard stop: no questions remaining -> FINISH_INTERVIEW.
  2. Very low completeness/clarity (answer was too vague to score
     meaningfully) -> CLARIFY.
  3. Weak answer (overall_score <= 4):
       - two weak answers in a row on the same topic -> the gap is
         identified; move on -> CHANGE_TOPIC.
       - otherwise -> DECREASE_DIFFICULTY (simplify, same topic).
  4. Strong answer (overall_score >= 7.5):
       - topic already explored 3+ times -> CHANGE_TOPIC (thoroughly
         covered, no need to keep pushing).
       - otherwise if score is very high (>= 8.5) -> INCREASE_DIFFICULTY.
       - otherwise -> FOLLOW_UP (there's a thread worth pulling).
  5. Middling answer -> FOLLOW_UP, unless the topic has already had 3+
     questions, in which case -> CHANGE_TOPIC.

When the action is CHANGE_TOPIC, the next topic is pulled from the
interview plan (skipping already-covered topics, honoring priority order).
Its `source` field (resume / job / role_fundamentals) becomes the more
specific action reported to the question generator (ASK_RESUME_QUESTION /
ASK_JOB_SPECIFIC_QUESTION), which the PRD lists as a distinct action.
"""
from app.agents.state import InterviewState

_STRONG_THRESHOLD = 7.5
_VERY_STRONG_THRESHOLD = 8.5
_WEAK_THRESHOLD = 4.0
_MAX_QUESTIONS_PER_TOPIC = 3


def _record_turn(state: InterviewState) -> None:
    """Append this turn to every rolling-memory list and update aggregate
    scores. Runs once per answered question, before deciding what's next."""
    evaluation = state["current_evaluation"]
    topic = state["current_topic"]

    state.setdefault("question_history", []).append(state["current_question"])
    state.setdefault("answer_history", []).append(state["current_answer"])
    state.setdefault("evaluation_history", []).append(evaluation.model_dump())
    state.setdefault("conversation_history", []).append(
        {
            "question": state["current_question"],
            "answer": state["current_answer"],
            "topic": topic,
            "difficulty": state["current_difficulty"],
            "evaluation": evaluation.model_dump(),
        }
    )

    topic_scores = state.setdefault("topic_scores", {})
    prior = topic_scores.get(topic)
    topic_scores[topic] = evaluation.overall_score if prior is None else (prior + evaluation.overall_score) / 2

    history = state["evaluation_history"]
    state["overall_score"] = sum(e["overall_score"] for e in history) / len(history)

    if evaluation.overall_score >= _STRONG_THRESHOLD:
        state["consecutive_strong"] = state.get("consecutive_strong", 0) + 1
        state["consecutive_weak"] = 0
    elif evaluation.overall_score <= _WEAK_THRESHOLD:
        state["consecutive_weak"] = state.get("consecutive_weak", 0) + 1
        state["consecutive_strong"] = 0
    else:
        state["consecutive_strong"] = 0
        state["consecutive_weak"] = 0


def _questions_asked_on_topic(state: InterviewState, topic: str) -> int:
    return sum(1 for qa in state.get("conversation_history", []) if qa["topic"] == topic)


def _topic_question_cap(state: InterviewState, topic: str) -> int:
    """Keep non-technical interview areas broad instead of over-probing one topic.

    A real interview normally asks one focused question per behavioral/situational
    area before returning to technical depth. Technical/resume topics can receive
    follow-ups when the candidate gives an answer worth exploring.
    """
    plan = state.get("interview_plan")
    if not plan:
        return _MAX_QUESTIONS_PER_TOPIC
    planned = next((t for t in plan.topics if t.name == topic), None)
    if planned and planned.source in {"behavioral", "situational"}:
        return 1
    if topic == "Resume-wide background":
        return 1
    # Give the first role-skill question a chance to stand on its own before
    # the interview returns to human/behavioral signals. Later, a revisit can
    # still be selected when the longer interview has room for depth.
    if planned and planned.source == "job":
        return 1
    return _MAX_QUESTIONS_PER_TOPIC


def _pick_next_topic(state: InterviewState) -> tuple[str, str, str]:
    """Returns (topic_name, difficulty, source) for the next topic to move
    to, preferring plan order and skipping topics that have already had
    their fair share of questions."""
    plan = state["interview_plan"]
    covered = set(state.get("covered_topics", []))
    covered.add(state["current_topic"])

    for planned in sorted(plan.topics, key=lambda t: t.priority):
        if planned.name not in covered or _questions_asked_on_topic(state, planned.name) < _topic_question_cap(state, planned.name):
            if planned.name != state["current_topic"]:
                return planned.name, planned.expected_difficulty, planned.source

    # Every planned topic is exhausted - recycle the first one at a harder
    # difficulty rather than stalling.
    first = plan.topics[0]
    return first.name, "hard", first.source


def _action_for_source(source: str) -> str:
    if source == "resume":
        return "ASK_RESUME_QUESTION"
    if source == "job":
        return "ASK_JOB_SPECIFIC_QUESTION"
    if source == "behavioral":
        return "ASK_BEHAVIORAL_QUESTION"
    if source == "situational":
        return "ASK_SITUATIONAL_QUESTION"
    return "CHANGE_TOPIC"


def decide_next_action_node(state: InterviewState) -> InterviewState:
    _record_turn(state)

    questions_asked = state.get("questions_asked", 0)
    question_limit = state.get("question_limit", 10)
    evaluation = state["current_evaluation"]
    topic = state["current_topic"]
    topic_exposure = _questions_asked_on_topic(state, topic)

    # Fixed-length interviews stop exactly at the candidate-selected limit.
    # Adaptive interviews use the same 12-question ceiling but can finish early
    # once they have enough evidence across multiple topics.
    if questions_asked >= question_limit:
        state["next_action"] = "FINISH_INTERVIEW"
        state["interview_status"] = "completed"
        return state

    if state.get("question_strategy") == "adaptive" and questions_asked >= 6:
        recent_scores = [e["overall_score"] for e in state.get("evaluation_history", [])[-2:]]
        distinct_topics = len({qa["topic"] for qa in state.get("conversation_history", [])})
        enough_coverage = distinct_topics >= 4
        strong_recent = len(recent_scores) == 2 and all(score >= _STRONG_THRESHOLD for score in recent_scores)
        solid_overall = state.get("overall_score", 0.0) >= 6.5
        # If the candidate has demonstrated enough breadth and consistent
        # evidence, do not manufacture extra questions just to hit the cap.
        if enough_coverage and solid_overall and strong_recent:
            state["next_action"] = "FINISH_INTERVIEW"
            state["interview_status"] = "completed"
            return state

        # Once nine questions have been answered, adaptive mode only continues
        # when another question is likely to resolve a meaningful gap.
        if questions_asked >= 9 and distinct_topics >= 4 and state.get("overall_score", 0.0) >= 5.5:
            state["next_action"] = "FINISH_INTERVIEW"
            state["interview_status"] = "completed"
            return state

    # Answer was too thin/unclear to trust a score-based decision.
    if evaluation.completeness <= 3.0 and evaluation.overall_score <= 5.0:
        state["next_action"] = "CLARIFY"
        return state

    if evaluation.overall_score <= _WEAK_THRESHOLD:
        if state.get("consecutive_weak", 0) >= 2:
            next_topic, next_difficulty, source = _pick_next_topic(state)
            state["current_topic"] = next_topic
            state["current_difficulty"] = next_difficulty
            state["current_topic_source"] = source
            state.setdefault("covered_topics", []).append(topic)
            state["next_action"] = _action_for_source(source)
        else:
            state["current_difficulty"] = _step_difficulty(state["current_difficulty"], down=True)
            state["next_action"] = "DECREASE_DIFFICULTY"
        return state

    if evaluation.overall_score >= _STRONG_THRESHOLD:
        if topic_exposure >= _topic_question_cap(state, topic):
            next_topic, next_difficulty, source = _pick_next_topic(state)
            state["current_topic"] = next_topic
            state["current_difficulty"] = next_difficulty
            state["current_topic_source"] = source
            state.setdefault("covered_topics", []).append(topic)
            state["next_action"] = _action_for_source(source)
        elif evaluation.overall_score >= _VERY_STRONG_THRESHOLD:
            state["current_difficulty"] = _step_difficulty(state["current_difficulty"], down=False)
            state["next_action"] = "INCREASE_DIFFICULTY"
        else:
            state["next_action"] = "FOLLOW_UP"
        return state

    # Middling answer.
    if topic_exposure >= _topic_question_cap(state, topic):
        next_topic, next_difficulty, source = _pick_next_topic(state)
        state["current_topic"] = next_topic
        state["current_difficulty"] = next_difficulty
        state["current_topic_source"] = source
        state.setdefault("covered_topics", []).append(topic)
        state["next_action"] = _action_for_source(source)
    else:
        state["next_action"] = "FOLLOW_UP"
    return state


def _step_difficulty(current: str, *, down: bool) -> str:
    order = ["easy", "medium", "hard"]
    idx = order.index(current) if current in order else 1
    idx = max(0, idx - 1) if down else min(len(order) - 1, idx + 1)
    return order[idx]


def should_finish(state: InterviewState) -> bool:
    return state.get("next_action") == "FINISH_INTERVIEW"
