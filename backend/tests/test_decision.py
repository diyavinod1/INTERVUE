from app.agents.nodes.decision import decide_next_action_node
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview_plan import InterviewPlan, PlannedTopic


def _base_state(**overrides):
    plan = InterviewPlan(
        topics=[
            PlannedTopic(name="React", priority=0, source="resume", expected_difficulty="medium"),
            PlannedTopic(name="System Design", priority=1, source="job", expected_difficulty="medium"),
            PlannedTopic(name="PostgreSQL", priority=2, source="job", expected_difficulty="easy"),
        ]
    )
    state = {
        "current_question": "How did you structure auth?",
        "current_answer": "I used JWT stored in local storage.",
        "current_topic": "React",
        "current_difficulty": "medium",
        "question_history": [],
        "answer_history": [],
        "evaluation_history": [],
        "conversation_history": [],
        "covered_topics": [],
        "topic_scores": {},
        "overall_score": 0.0,
        "consecutive_strong": 0,
        "consecutive_weak": 0,
        "questions_asked": 3,
        "question_limit": 10,
        "interview_plan": plan,
    }
    state.update(overrides)
    return state


def _eval(score, completeness=None):
    completeness = completeness if completeness is not None else score
    return AnswerEvaluation(
        overall_score=score,
        correctness=score,
        completeness=completeness,
        technical_depth=score,
        relevance=score,
        clarity=score,
    )


def test_strong_answer_increases_difficulty():
    state = _base_state(current_evaluation=_eval(9.0))
    result = decide_next_action_node(state)
    assert result["next_action"] == "INCREASE_DIFFICULTY"
    assert result["current_difficulty"] == "hard"


def test_moderately_strong_answer_follows_up():
    state = _base_state(current_evaluation=_eval(8.0))
    result = decide_next_action_node(state)
    assert result["next_action"] == "FOLLOW_UP"
    assert result["current_topic"] == "React"


def test_weak_answer_decreases_difficulty_first():
    state = _base_state(current_evaluation=_eval(3.0, completeness=6.0))
    result = decide_next_action_node(state)
    assert result["next_action"] == "DECREASE_DIFFICULTY"
    assert result["current_difficulty"] == "easy"


def test_two_consecutive_weak_answers_changes_topic():
    state = _base_state(current_evaluation=_eval(3.0, completeness=6.0), consecutive_weak=1)
    result = decide_next_action_node(state)
    assert result["next_action"] in ("CHANGE_TOPIC", "ASK_JOB_SPECIFIC_QUESTION", "ASK_RESUME_QUESTION")
    assert result["current_topic"] != "React"


def test_vague_incomplete_answer_triggers_clarify():
    state = _base_state(current_evaluation=_eval(4.5, completeness=2.0))
    result = decide_next_action_node(state)
    assert result["next_action"] == "CLARIFY"
    # Clarify should NOT change topic or difficulty.
    assert result["current_topic"] == "React"
    assert result["current_difficulty"] == "medium"


def test_topic_exhausted_after_three_questions_moves_on_even_with_ok_score():
    conversation = [
        {"question": "q1", "answer": "a1", "topic": "React", "difficulty": "easy", "evaluation": {"overall_score": 6}},
        {"question": "q2", "answer": "a2", "topic": "React", "difficulty": "medium", "evaluation": {"overall_score": 6}},
        {"question": "q3", "answer": "a3", "topic": "React", "difficulty": "medium", "evaluation": {"overall_score": 6}},
    ]
    state = _base_state(current_evaluation=_eval(6.0), conversation_history=conversation)
    result = decide_next_action_node(state)
    assert result["current_topic"] != "React"


def test_question_limit_reached_finishes_interview():
    state = _base_state(current_evaluation=_eval(6.0), questions_asked=10, question_limit=10)
    result = decide_next_action_node(state)
    assert result["next_action"] == "FINISH_INTERVIEW"
    assert result["interview_status"] == "completed"


def test_overall_score_and_topic_scores_are_tracked():
    state = _base_state(current_evaluation=_eval(8.0))
    result = decide_next_action_node(state)
    assert result["overall_score"] == 8.0
    assert result["topic_scores"]["React"] == 8.0
    assert len(result["conversation_history"]) == 1


def test_behavioral_topic_moves_on_after_one_question():
    from app.schemas.interview_plan import PlannedTopic

    plan = InterviewPlan(
        topics=[
            PlannedTopic(name="Introduce yourself & career story", priority=0, source="behavioral", expected_difficulty="easy"),
            PlannedTopic(name="React", priority=1, source="job", expected_difficulty="medium"),
            PlannedTopic(name="Hypothetical & situational judgment", priority=2, source="situational", expected_difficulty="medium"),
        ]
    )
    conversation = []
    state = _base_state(
        current_topic="Introduce yourself & career story",
        current_difficulty="easy",
        current_evaluation=_eval(8.0),
        conversation_history=conversation,
        interview_plan=plan,
        questions_asked=1,
        question_limit=5,
    )
    result = decide_next_action_node(state)
    assert result["current_topic"] == "React"
    assert result["next_action"] == "ASK_JOB_SPECIFIC_QUESTION"


def test_situational_topic_routes_to_hypothetical_question():
    plan = InterviewPlan(
        topics=[
            PlannedTopic(name="React", priority=0, source="job", expected_difficulty="medium"),
            PlannedTopic(name="Hypothetical & situational judgment", priority=1, source="situational", expected_difficulty="medium"),
        ]
    )
    conversation = [{
        "question": "How would you design this?",
        "answer": "I would start by clarifying requirements and constraints.",
        "topic": "React",
        "difficulty": "medium",
        "evaluation": {"overall_score": 8},
    }, {
        "question": "What about the trade-off?",
        "answer": "I would measure the impact before choosing.",
        "topic": "React",
        "difficulty": "medium",
        "evaluation": {"overall_score": 8},
    }, {
        "question": "Go deeper.",
        "answer": "I would document the decision and validate it.",
        "topic": "React",
        "difficulty": "medium",
        "evaluation": {"overall_score": 8},
    }]
    state = _base_state(
        current_topic="React",
        current_evaluation=_eval(8.0),
        conversation_history=conversation,
        interview_plan=plan,
        questions_asked=3,
        question_limit=5,
    )
    result = decide_next_action_node(state)
    assert result["current_topic"] == "Hypothetical & situational judgment"
    assert result["next_action"] == "ASK_SITUATIONAL_QUESTION"
