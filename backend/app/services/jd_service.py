"""
Job description analysis service.

Same design philosophy as resume_service.py: deterministic section +
keyword extraction, not an LLM call, so we never claim the JD "requires" or
"prefers" something that isn't actually written in it (PRD Sec. 21).
"""
import re

from app.services.resume_service import _TECH_KEYWORDS, _mine_technologies  # reuse the same curated keyword list
from app.schemas.candidate import JobProfile

_REQUIRED_HEADERS = ["requirements", "required qualifications", "must have", "qualifications"]
_PREFERRED_HEADERS = ["preferred qualifications", "preferred", "nice to have", "bonus points"]
_RESPONSIBILITY_HEADERS = ["responsibilities", "what you'll do", "role overview", "key responsibilities"]

_EXPERIENCE_PATTERN = re.compile(r"(\d+\+?\s*-?\s*\d*\s*years?)", re.IGNORECASE)


def _split_into_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"required": [], "preferred": [], "responsibilities": [], "other": []}
    current = "other"
    for raw_line in text.splitlines():
        line = raw_line.strip(" \t\u2022-").strip()
        if not line:
            continue
        normalized = line.lower().rstrip(":")
        if len(normalized) <= 50:
            if normalized in _REQUIRED_HEADERS:
                current = "required"
                continue
            if normalized in _PREFERRED_HEADERS:
                current = "preferred"
                continue
            if normalized in _RESPONSIBILITY_HEADERS:
                current = "responsibilities"
                continue
        sections[current].append(line)
    return sections


def _extract_skills_from_lines(lines: list[str]) -> list[str]:
    skills = []
    for line in lines:
        for keyword in _TECH_KEYWORDS:
            pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(keyword) + r"(?![A-Za-z0-9])", re.IGNORECASE)
            if pattern.search(line) and keyword not in skills:
                skills.append(keyword)
    return skills


def build_job_profile(job_description_text: str, target_role: str) -> JobProfile:
    sections = _split_into_sections(job_description_text)

    required_skills = _extract_skills_from_lines(sections["required"]) or _extract_skills_from_lines(sections["other"])
    preferred_skills = [s for s in _extract_skills_from_lines(sections["preferred"]) if s not in required_skills]
    all_technologies = _mine_technologies(job_description_text)

    experience_match = _EXPERIENCE_PATTERN.search(job_description_text)
    experience_requirement = experience_match.group(1) if experience_match else ""

    responsibilities = sections["responsibilities"][:10] or sections["other"][:5]

    # "Key technical areas" = required skills first, then any additional
    # technologies mentioned anywhere in the JD that weren't already captured.
    key_areas = list(dict.fromkeys(required_skills + [t for t in all_technologies if t not in required_skills]))

    return JobProfile(
        target_role=target_role,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        responsibilities=responsibilities,
        technologies=all_technologies,
        experience_requirement=experience_requirement,
        key_technical_areas=key_areas[:15],
    )
