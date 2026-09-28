"""
Helpers that render the candidate/job/plan context into a compact text block
reused across the planner, question generator, evaluator, and final report
prompts, so those prompts stay short and consistent rather than each
re-implementing their own serialization of the same objects.

All untrusted, candidate-controlled text (resume text, JD text, answers) is
passed through `sanitize_for_prompt` before being embedded, and is always
placed inside clearly labeled delimiters so the model can distinguish
"data about the candidate" from "instructions to the interviewer."
"""
from app.core.security import sanitize_for_prompt, sanitize_resume_for_prompt
from app.schemas.candidate import CandidateProfile, JobProfile
from app.schemas.interview_plan import InterviewPlan


def render_candidate_profile(profile: CandidateProfile) -> str:
    lines = []
    if profile.education:
        lines.append("Education: " + "; ".join(profile.education))
    if profile.experience:
        exp = "; ".join(f"{e.title} at {e.organization} ({e.duration})" for e in profile.experience)
        lines.append("Experience: " + exp)
    if profile.projects:
        proj = "; ".join(
            f"{p.name}: {p.description} [tech: {', '.join(p.technologies)}]" for p in profile.projects
        )
        lines.append("Projects: " + proj)
    if profile.skills:
        lines.append("Skills: " + ", ".join(profile.skills))
    if profile.technologies:
        lines.append("Technologies: " + ", ".join(profile.technologies))
    if profile.internships:
        lines.append("Internships: " + "; ".join(profile.internships))
    if profile.certifications:
        lines.append("Certifications: " + ", ".join(profile.certifications))
    if profile.achievements:
        lines.append("Achievements: " + "; ".join(profile.achievements))

    text = "\n".join(lines) if lines else "(No structured resume details were extracted.)"
    return sanitize_for_prompt(text, label="resume")


def render_full_resume(resume_raw_text: str) -> str:
    """Render the original extracted resume text so the interviewer can use
    details that were not captured by the structured resume parser."""
    text = (resume_raw_text or "").strip()
    if not text:
        return "(No raw resume text is available.)"
    return sanitize_resume_for_prompt(text)


def render_job_profile(job: JobProfile) -> str:
    lines = [f"Target role: {job.target_role}"] if job.target_role else []
    if job.required_skills:
        lines.append("Required skills: " + ", ".join(job.required_skills))
    if job.preferred_skills:
        lines.append("Preferred skills: " + ", ".join(job.preferred_skills))
    if job.technologies:
        lines.append("Technologies: " + ", ".join(job.technologies))
    if job.responsibilities:
        lines.append("Responsibilities: " + "; ".join(job.responsibilities))
    if job.experience_requirement:
        lines.append("Experience requirement: " + job.experience_requirement)

    text = "\n".join(lines) if lines else "(No structured job details were extracted.)"
    return sanitize_for_prompt(text, label="job description")


def render_plan(plan: InterviewPlan) -> str:
    if not plan.topics:
        return "(No plan yet.)"
    lines = [
        f"{i + 1}. {t.name} [priority={t.priority}, source={t.source}, expected_difficulty={t.expected_difficulty}] - {t.rationale}"
        for i, t in enumerate(plan.topics)
    ]
    return "\n".join(lines)


def render_recent_conversation(conversation_history: list[dict], max_turns: int = 6) -> str:
    """Only the most recent N turns - this is the "sensible context management"
    referenced in PRD Sec. 23, so prompts don't grow unbounded over a long
    interview."""
    recent = conversation_history[-max_turns:]
    if not recent:
        return "(This is the first question of the interview.)"

    lines = []
    for turn in recent:
        q = sanitize_for_prompt(turn.get("question", ""), label="previous question")
        a = sanitize_for_prompt(turn.get("answer", ""), label="previous answer")
        score = turn.get("evaluation", {}).get("overall_score")
        lines.append(f"Q ({turn.get('topic', '')}, {turn.get('difficulty', '')}): {q}")
        lines.append(f"A: {a}" + (f"  [scored {score}/10]" if score is not None else ""))
    return "\n".join(lines)
