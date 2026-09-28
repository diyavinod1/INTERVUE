from app.services.resume_service import build_candidate_profile

SAMPLE_RESUME = """
Diya Vinod

EDUCATION
B.Tech in Computer Science, XYZ University, 2024

EXPERIENCE
ML Intern at Acme Corp | Jun 2023 - Aug 2023
Built data pipelines for model training.

PROJECTS
RAG Chatbot: Built a RAG chatbot using LangChain and FAISS for document Q&A.
Portfolio Site: A personal portfolio built with React and Tailwind.

SKILLS
Python, PyTorch, React, FastAPI, PostgreSQL

CERTIFICATIONS
AWS Certified Cloud Practitioner
"""


def test_extracts_skills_present_in_resume():
    profile = build_candidate_profile(SAMPLE_RESUME)
    assert "Python" in profile.skills or "Python" in profile.technologies
    assert "React" in profile.technologies


def test_does_not_invent_skills_not_present():
    profile = build_candidate_profile(SAMPLE_RESUME)
    assert "Kubernetes" not in profile.technologies
    assert "Rust" not in profile.technologies


def test_extracts_projects_with_technologies():
    profile = build_candidate_profile(SAMPLE_RESUME)
    names = [p.name for p in profile.projects]
    assert any("RAG Chatbot" in n for n in names)
    rag_project = next(p for p in profile.projects if "RAG Chatbot" in p.name)
    assert "LangChain" in rag_project.technologies
    assert "FAISS" in rag_project.technologies


def test_empty_sections_stay_empty_not_guessed():
    minimal_resume = "John Doe\n\nSKILLS\nJavaScript"
    profile = build_candidate_profile(minimal_resume)
    assert profile.certifications == []
    assert profile.internships == []
