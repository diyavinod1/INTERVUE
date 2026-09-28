"""
CREATE INTERVIEW PLAN node (PRD Sec. 9, 16).

Topic *selection* is deterministic: we always include (1) a resume/project
discussion opener, (2) every required job skill the candidate's resume
already claims (so we can verify depth), (3) required job skills the
candidate does NOT list (to probe the gap), and (4) one or two of the
candidate's own standout projects. This is reproducible and testable
without an LLM. The LLM is only used afterwards to phrase a one-sentence
rationale per topic (see llm_service.generate_plan_rationales) - purely a
natural-language polish step, not a decision step.

The resulting plan is a loose priority-ordered list, not a script: decision.py
is free to jump ahead, skip, or revisit topics based on how the interview
actually goes.
"""
from app.agents.state import InterviewState
from app.schemas.interview_plan import InterviewPlan, PlannedTopic
from app.services.llm_service import LLMService
from app.agents.prompts.context import render_candidate_profile, render_job_profile

_llm = LLMService()


async def create_plan_node(state: InterviewState) -> InterviewState:
    profile = state["candidate_profile"]
    job = state["job_profile"]

    topics: list[PlannedTopic] = []
    priority = 0

    # Build a realistic interview arc instead of a technical-topic queue.
    # Even a short interview should feel like a real conversation: introduction,
    # candidate background, role-relevant depth, then behavioral/situational judgment.
    topics.append(
        PlannedTopic(
            name="Introduce yourself & career story",
            priority=priority, source="behavioral", expected_difficulty="easy",
        )
    )
    priority += 1

    topics.append(
        PlannedTopic(
            name="Resume-wide background",
            priority=priority, source="resume", expected_difficulty="medium"
        )
    )
    priority += 1

    # Put role-specific depth early enough that a 5-question interview still
    # contains technical assessment when the job description provides skills.
    resume_skill_set = {s.lower() for s in profile.skills} | {t.lower() for t in profile.technologies}
    # Reserve room for behavioral and situational questions. A very long JD
    # must never crowd all of the human-interview coverage out of the plan.
    job_topics_added = 0
    for skill in job.required_skills:
        if skill.lower() in resume_skill_set and job_topics_added < 2:
            topics.append(
                PlannedTopic(name=skill, priority=priority, source="job", expected_difficulty="medium")
            )
            priority += 1
            job_topics_added += 1

    for skill in job.required_skills:
        if skill.lower() not in resume_skill_set and job_topics_added < 3:
            topics.append(
                PlannedTopic(name=skill, priority=priority, source="job", expected_difficulty="easy")
            )
            priority += 1
            job_topics_added += 1

    behavioral_topics = [
        ("Teamwork & communication", "medium"),
        ("Motivation & role fit", "medium"),
        ("Ownership & initiative", "medium"),
        ("Challenges, failure & learning", "medium"),
    ]

    # Situational questions test judgment rather than memorized technical
    # knowledge: ambiguity, conflict, prioritization, trade-offs, and what the
    # candidate would do in a realistic hypothetical scenario.
    situational_topics = [
        ("Hypothetical & situational judgment", "medium"),
        ("Prioritization under pressure", "medium"),
    ]
    for name, difficulty in situational_topics:
        topics.append(
            PlannedTopic(
                name=name, priority=priority, source="situational", expected_difficulty=difficulty
            )
        )
        priority += 1

    for name, difficulty in behavioral_topics:
        topics.append(
            PlannedTopic(
                name=name, priority=priority, source="behavioral", expected_difficulty=difficulty
            )
        )
        priority += 1

    for project in profile.projects[1:4]:
        topics.append(
            PlannedTopic(name=project.name, priority=priority, source="resume", expected_difficulty="medium")
        )
        priority += 1

    if not topics:
        topics.append(
            PlannedTopic(name=job.target_role or "your background", priority=0, source="role_fundamentals")
        )

    # Keep the roadmap broad enough to contain resume + behavioral + technical
    # coverage, while the adaptive decision node remains free to follow up.
    topics = topics[:10]

    rationale_data = await _llm.generate_plan_rationales(
        candidate_context=render_candidate_profile(profile),
        job_context=render_job_profile(job),
        topic_names=[t.name for t in topics],
    )
    rationales = rationale_data.get("rationales", {})
    for t in topics:
        t.rationale = rationales.get(t.name, t.rationale)

    plan = InterviewPlan(
        question_strategy=state.get("question_strategy", "standard"),
        topics=topics,
        opening_focus="Introduce yourself & career story",
    )

    state["interview_plan"] = plan
    state["current_topic"] = topics[0].name
    state["current_topic_source"] = topics[0].source
    state["current_difficulty"] = topics[0].expected_difficulty
    return state
