from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Candidate(Base):
    """
    A candidate + the interview context derived from their resume and the
    job description they're targeting. `resume_profile` and `job_profile`
    are the structured outputs of resume_service / jd_service - stored as
    JSON because their shape is inherently semi-structured (skills lists,
    project lists of varying detail) but every other field that IS always
    present (name, role, experience level) is a proper typed column.
    """

    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    target_role: Mapped[str] = mapped_column(String(255))
    experience_level: Mapped[str] = mapped_column(String(50))

    resume_filename: Mapped[str] = mapped_column(String(255))
    resume_raw_text: Mapped[str] = mapped_column(Text)
    resume_profile: Mapped[dict] = mapped_column(JSON)  # CandidateProfile (see schemas)

    job_description_text: Mapped[str] = mapped_column(Text)
    job_profile: Mapped[dict] = mapped_column(JSON)  # JobProfile (see schemas)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")
