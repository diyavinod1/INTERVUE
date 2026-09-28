from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("questions.id"), unique=True)
    interview_id: Mapped[str] = mapped_column(String(36), ForeignKey("interviews.id"), index=True)

    text: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(10))  # "text" | "voice"

    # Measurable voice signals only - never psychological inference (see PRD Sec. 36).
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    filler_word_count: Mapped[int] = mapped_column(Integer, default=0)
    response_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    question = relationship("Question", back_populates="answer")
    evaluation = relationship("Evaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan")
