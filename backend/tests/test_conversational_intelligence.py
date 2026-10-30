import pytest
from app.agents.prompts.context import render_latest_answer_analysis, render_recent_conversation
from app.agents.prompts.question_generator import question_generator_prompt
from app.agents.nodes.decision import decide_next_action_node
from app.agents.nodes.planning import create_plan_node
from app.schemas.candidate import CandidateProfile, JobProfile, Project
from app.schemas.evaluation import AnswerEvaluation
from app.schemas.interview import InterviewMode
from app.schemas.interview_plan import InterviewPlan, PlannedTopic
from app.services import interview_service, jd_service, llm_service, resume_service

pytestmark = pytest.mark.asyncio

FORBIDDEN_PHRASES = [
    "could you clarify or expand on what you just said",
    "can you tell me more about your experience with resume-wide background",
    "resume-wide background",
    "can you tell me more about your experience with",
    "that's interesting!",
    "great answer!",
    "let's dive deeper!",
]


def _check_no_robotic_phrases(text: str):
    lower = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in lower, f"Robotic phrase '{phrase}' found in generated text: {text}"


async def test_planning_eliminates_robotic_resume_wide_background():
    profile = CandidateProfile(
        projects=[Project(name="CloudStream", description="Kafka streaming service", technologies=["Kafka", "Go"])]
    )
    job = JobProfile(target_role="Backend Engineer", required_skills=["Kafka", "Go"])
    state = {
        "candidate_profile": profile,
        "job_profile": job,
    }
    result = await create_plan_node(state)
    topic_names = [t.name for t in result["interview_plan"].topics]
    assert "Resume-wide background" not in topic_names
    assert any("CloudStream" in name or "Project" in name for name in topic_names)


def test_clarify_loop_prevention():
    """Ensure candidate giving thin answers does not get stuck in an infinite CLARIFY loop."""
    plan = InterviewPlan(
        topics=[
            PlannedTopic(name="System Design", priority=0, source="job", expected_difficulty="medium"),
            PlannedTopic(name="PostgreSQL", priority=1, source="job", expected_difficulty="easy"),
        ]
    )
    # Turn 1: thin answer
    eval_1 = AnswerEvaluation(
        overall_score=3.5, correctness=4.0, completeness=2.0, technical_depth=2.0, relevance=5.0, clarity=4.0,
        recommended_action="CLARIFY"
    )
    state = {
        "current_question": "How do you scale the database?",
        "current_answer": "I would add more servers.",
        "current_topic": "System Design",
        "current_difficulty": "medium",
        "question_history": ["How do you scale the database?"],
        "answer_history": ["I would add more servers."],
        "evaluation_history": [eval_1.model_dump()],
        "conversation_history": [
            {"question": "How do you scale the database?", "answer": "I would add more servers.", "topic": "System Design", "difficulty": "medium", "evaluation": eval_1.model_dump()}
        ],
        "covered_topics": [],
        "topic_scores": {},
        "overall_score": 3.5,
        "consecutive_strong": 0,
        "consecutive_weak": 0,
        "questions_asked": 1,
        "question_limit": 8,
        "interview_plan": plan,
        "current_evaluation": eval_1,
        "next_action": "CLARIFY",
    }
    decide_next_action_node(state)

    # Turn 2: another thin answer on clarification
    eval_2 = AnswerEvaluation(
        overall_score=3.0, correctness=3.0, completeness=2.0, technical_depth=2.0, relevance=4.0, clarity=3.0,
        recommended_action="CLARIFY"
    )
    state["current_answer"] = "Just replicate it."
    state["current_evaluation"] = eval_2
    res2 = decide_next_action_node(state)

    # Must NOT repeat CLARIFY - must step down to fundamentals or change topic
    assert res2["next_action"] != "CLARIFY"
    assert res2["next_action"] == "DECREASE_DIFFICULTY"
    assert res2["current_difficulty"] == "easy"


def test_fallback_questions_contain_no_robotic_filler():
    """Verify fallback questions for all actions avoid robotic templates."""
    actions = [
        "FOLLOW_UP", "INCREASE_DIFFICULTY", "DECREASE_DIFFICULTY",
        "CHANGE_TOPIC", "CLARIFY", "ASK_BEHAVIORAL_QUESTION", "ASK_SITUATIONAL_QUESTION"
    ]
    for action in actions:
        q = llm_service._fallback_question("URL Shortener", "medium", action)
        _check_no_robotic_phrases(q)
        assert len(q.split()) > 5


def test_latest_answer_analysis_rendering():
    eval_dict = {
        "overall_score": 8.0,
        "strengths": ["Clear hash function strategy", "Properly identified database storage"],
        "weaknesses": ["Did not mention hash collision handling"],
        "missing_concepts": ["Collision resolution", "Rate limiting"],
        "feedback": "Strong baseline answer but missing collision mechanics.",
    }
    rendered = render_latest_answer_analysis(
        latest_question="How would you design a URL shortener?",
        latest_answer="I would hash the URL and store the mapping in PostgreSQL.",
        evaluation=eval_dict,
    )
    assert "LATEST QUESTION ASKED: How would you design a URL shortener?" in rendered
    assert "CANDIDATE'S ACTUAL ANSWER: I would hash the URL and store the mapping in PostgreSQL." in rendered
    assert "Did not mention hash collision handling" in rendered
    assert "Collision resolution" in rendered


def test_multi_turn_conversation_rendering():
    history = [
        {
            "question": "Tell me about yourself.",
            "answer": "I have 4 years of experience building distributed systems.",
            "topic": "Introduce yourself",
            "difficulty": "easy",
            "evaluation": {"overall_score": 8.0},
        },
        {
            "question": "Which database do you prefer for caching?",
            "answer": "Redis, because of in-memory speed.",
            "topic": "Caching",
            "difficulty": "medium",
            "evaluation": {"overall_score": 7.5},
        }
    ]
    rendered = render_recent_conversation(history)
    assert "Turn 1 [Introduce yourself | easy] [score: 8.0/10]:" in rendered
    assert "Turn 2 [Caching | medium] [score: 7.5/10]:" in rendered
    assert "Redis, because of in-memory speed." in rendered


async def test_full_conversational_turn_with_mocked_llm(db_session, monkeypatch):
    """Test multi-turn flow with context-aware question generation."""
    resume_text = "Alex Smith\nExperience: Senior Engineer at Acme Corp.\nProjects: Scalable Cache [Redis, Python]\nSkills: Python, Redis, Postgres"
    profile = resume_service.build_candidate_profile(resume_text)
    job_profile = jd_service.build_job_profile("Requirements: Python, Redis, PostgreSQL", target_role="Senior Backend Engineer")

    from app.repositories import interview_repository as repo

    candidate = repo.create_candidate(
        db_session,
        full_name="Alex Smith",
        target_role="Senior Backend Engineer",
        experience_level="Senior",
        resume_filename="resume.pdf",
        resume_raw_text=resume_text,
        resume_profile=profile,
        job_description_text="Requirements: Python, Redis, PostgreSQL",
        job_profile=job_profile,
    )
    interview = repo.create_interview(db_session, candidate_id=candidate.id, question_limit=6)

    # Verify start interview
    interview = await interview_service.start_interview(db_session, interview_id=interview.id, mode=InterviewMode.TEXT)
    q1 = repo.get_latest_unanswered_question(db_session, interview.id)
    assert q1 is not None
    _check_no_robotic_phrases(q1.text)

    # Turn 1: Candidate gives strong technical answer mentioning Redis
    interview = await interview_service.submit_answer(
        db_session,
        interview_id=interview.id,
        answer_text="At Acme Corp, I designed a multi-tier caching layer using Redis clustered across 3 nodes to offload 80% of read traffic from PostgreSQL.",
        mode=InterviewMode.TEXT,
        audio_duration_seconds=None,
        response_latency_ms=1200,
    )
    q2 = repo.get_latest_unanswered_question(db_session, interview.id)
    assert q2 is not None
    _check_no_robotic_phrases(q2.text)

    # Turn 2: Candidate gives answer requiring deeper follow-up on failure modes
    interview = await interview_service.submit_answer(
        db_session,
        interview_id=interview.id,
        answer_text="When Redis nodes failed, we fell back directly to PostgreSQL replicas, though that occasionally spiked database CPU to 90%.",
        mode=InterviewMode.TEXT,
        audio_duration_seconds=None,
        response_latency_ms=1500,
    )
    q3 = repo.get_latest_unanswered_question(db_session, interview.id)
    assert q3 is not None
    _check_no_robotic_phrases(q3.text)

    # Verify conversation history contains all turns with preserved context
    messages = interview_service.build_conversation_messages(db_session, interview.id)
    assert len(messages) >= 5  # Q1, A1, Q2, A2, Q3
    for msg in messages:
        _check_no_robotic_phrases(msg["text"])
