from app.services.jd_service import build_job_profile

SAMPLE_JD = """
We are hiring a Full Stack Developer.

Requirements
Python
FastAPI
PostgreSQL
3+ years of experience

Preferred Qualifications
Docker
AWS

Responsibilities
Build and maintain backend services
Collaborate with the frontend team
"""


def test_required_skills_extracted():
    profile = build_job_profile(SAMPLE_JD, target_role="Full Stack Developer")
    assert "Python" in profile.required_skills
    assert "FastAPI" in profile.required_skills
    assert "PostgreSQL" in profile.required_skills


def test_preferred_skills_are_separate_from_required():
    profile = build_job_profile(SAMPLE_JD, target_role="Full Stack Developer")
    assert "Docker" in profile.preferred_skills
    assert "Docker" not in profile.required_skills


def test_experience_requirement_extracted():
    profile = build_job_profile(SAMPLE_JD, target_role="Full Stack Developer")
    assert "3" in profile.experience_requirement


def test_responsibilities_extracted():
    profile = build_job_profile(SAMPLE_JD, target_role="Full Stack Developer")
    assert any("backend" in r.lower() for r in profile.responsibilities)
