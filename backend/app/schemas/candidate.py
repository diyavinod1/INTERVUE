"""
Structured representations of the candidate and the job they're targeting.

CandidateProfile is produced by resume_service from parsed resume text.
JobProfile is produced by jd_service from the pasted job description.

Both are deliberately conservative: fields default to empty rather than
being guessed, because the PRD is explicit that we must never invent
resume/JD details that aren't actually present.
"""
from pydantic import BaseModel, Field


class Project(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)


class Experience(BaseModel):
    title: str = ""
    organization: str = ""
    duration: str = ""
    description: str = ""


class CandidateProfile(BaseModel):
    name: str = ""
    education: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    internships: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)


class JobProfile(BaseModel):
    target_role: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    experience_requirement: str = ""
    key_technical_areas: list[str] = Field(default_factory=list)


class SetupInterviewRequest(BaseModel):
    full_name: str
    target_role: str
    experience_level: str
    job_description: str


class CandidateResponse(BaseModel):
    id: str
    full_name: str
    target_role: str
    experience_level: str
    resume_filename: str
    resume_profile: CandidateProfile
    job_profile: JobProfile

    model_config = {"from_attributes": True}
