"""
Resume parsing service.

Design choice: structured extraction (education / experience / skills /
projects / etc.) is done with deterministic text-processing heuristics, NOT
an LLM call. Reasons (PRD Sec. 7, 18, 45):
  - The PRD is explicit that we must never invent resume details - a
    heuristic section/keyword extractor structurally cannot hallucinate
    content that isn't in the text, whereas an LLM extraction step always
    carries some risk of it.
  - This is exactly the kind of "straightforward" decision the PRD says
    should use deterministic logic, saving LLM calls for where genuine
    semantic reasoning is needed (question generation, evaluation).
  - It keeps resume upload fast and free of any external dependency.

The extractor is intentionally simple and readable: split into lines,
detect common section headers, bucket lines under the current section, and
mine skills/technologies from a curated keyword list. It will not be
perfect on every resume format, but it is honest about what it found -
sections it can't confidently detect are simply left empty rather than
guessed at.
"""
import io
import re

import docx
from pypdf import PdfReader

from app.core.logging import get_logger
from app.schemas.candidate import CandidateProfile, Experience, Project

logger = get_logger(__name__)

_SECTION_HEADERS = {
    "education": ["education", "academic background"],
    "experience": ["experience", "work experience", "employment", "professional experience"],
    "skills": ["skills", "technical skills", "core competencies"],
    "projects": ["projects", "personal projects", "academic projects"],
    "internships": ["internship", "internships"],
    "certifications": ["certifications", "certificates", "licenses"],
    "achievements": ["achievements", "awards", "honors"],
}

# A curated (non-exhaustive) list of common tech/skill keywords used to mine
# a "technologies" list out of free text - deliberately broad but bounded,
# so we never claim a skill the resume text doesn't actually contain.
_TECH_KEYWORDS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Ruby", "PHP", "Kotlin", "Swift",
    "React", "React Native", "Vue", "Angular", "Next.js", "Node.js", "Express", "Django", "Flask", "FastAPI",
    "Spring", "Spring Boot", ".NET", "GraphQL", "REST", "gRPC",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Supabase", "Firebase", "DynamoDB", "Cassandra",
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform", "CI/CD", "Jenkins", "GitHub Actions",
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy",
    "LangChain", "LangGraph", "OpenAI", "LLM", "NLP", "Computer Vision", "RAG", "FAISS", "Pinecone",
    "HTML", "CSS", "Tailwind", "SASS", "Webpack", "Vite",
    "Git", "Linux", "Bash", "Kafka", "RabbitMQ", "Microservices", "Agile", "Scrum",
]


def extract_text(filename: str, raw_bytes: bytes) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        return _extract_pdf_text(raw_bytes)
    if ext == "docx":
        return _extract_docx_text(raw_bytes)
    raise ValueError(f"Unsupported resume extension: {ext}")


def _extract_pdf_text(raw_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(raw_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_docx_text(raw_bytes: bytes) -> str:
    document = docx.Document(io.BytesIO(raw_bytes))
    return "\n".join(p.text for p in document.paragraphs)


def _detect_section(line: str) -> str | None:
    normalized = line.strip().lower().rstrip(":")
    if len(normalized) > 40:
        return None
    for section, headers in _SECTION_HEADERS.items():
        if normalized in headers:
            return section
    return None


def _bucket_lines_by_section(text: str) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {section: [] for section in _SECTION_HEADERS}
    current_section: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip(" \t\u2022-").strip()
        if not line:
            continue
        detected = _detect_section(line)
        if detected:
            current_section = detected
            continue
        if current_section:
            buckets[current_section].append(line)

    return buckets


def _mine_technologies(text: str) -> list[str]:
    found = []
    for keyword in _TECH_KEYWORDS:
        pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(keyword) + r"(?![A-Za-z0-9])", re.IGNORECASE)
        if pattern.search(text):
            found.append(keyword)
    return found


def _parse_skills_lines(lines: list[str]) -> list[str]:
    skills: list[str] = []
    for line in lines:
        parts = re.split(r"[,\u2022|/]", line)
        for part in parts:
            cleaned = part.strip(" .")
            if cleaned and len(cleaned) <= 40:
                skills.append(cleaned)
    # de-duplicate while preserving order
    seen = set()
    unique = []
    for s in skills:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def _parse_projects(lines: list[str]) -> list[Project]:
    projects: list[Project] = []
    for line in lines:
        # Common resume pattern: "Project Name: description of what it does"
        if ":" in line:
            name, _, description = line.partition(":")
            name, description = name.strip(), description.strip()
        elif " - " in line:
            name, _, description = line.partition(" - ")
            name, description = name.strip(), description.strip()
        else:
            name, description = line[:60].strip(), line
        if not name:
            continue
        projects.append(Project(name=name, description=description, technologies=_mine_technologies(line)))
    return projects


def _parse_experience(lines: list[str]) -> list[Experience]:
    experiences: list[Experience] = []
    for line in lines:
        title, organization, duration = line, "", ""
        if " at " in line:
            title, _, rest = line.partition(" at ")
            organization = rest
        elif "|" in line:
            parts = [p.strip() for p in line.split("|")]
            title = parts[0]
            organization = parts[1] if len(parts) > 1 else ""
            duration = parts[2] if len(parts) > 2 else ""
        experiences.append(Experience(title=title.strip(), organization=organization.strip(), duration=duration.strip(), description=line))
    return experiences


def build_candidate_profile(resume_text: str) -> CandidateProfile:
    """
    Build a CandidateProfile from raw extracted resume text. Never invents
    fields that weren't detected - empty lists mean "not found," which the
    interview planner treats as "don't ask about this," not "assume none."
    """
    buckets = _bucket_lines_by_section(resume_text)

    profile = CandidateProfile(
        education=buckets["education"][:10],
        experience=_parse_experience(buckets["experience"])[:10],
        skills=_parse_skills_lines(buckets["skills"])[:30],
        technologies=_mine_technologies(resume_text),
        projects=_parse_projects(buckets["projects"])[:10],
        internships=buckets["internships"][:10],
        certifications=buckets["certifications"][:10],
        achievements=buckets["achievements"][:10],
    )

    logger.info(
        "resume_parsed skills=%d technologies=%d projects=%d experience=%d",
        len(profile.skills), len(profile.technologies), len(profile.projects), len(profile.experience),
    )
    return profile
