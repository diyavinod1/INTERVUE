from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    interview_id: Mapped[str] = mapped_column(String(36), ForeignKey("interviews.id"), index=True)

    sequence_index: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(String(120))
    difficulty: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)

    # Why this question was asked (e.g. {"type": "resume_followup", "source": "..."})
    reason: Mapped[dict] = mapped_column(JSON, default=dict)
    action_type: Mapped[str] = mapped_column(String(40))  # e.g. FOLLOW_UP, CHANGE_TOPIC, ...

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="questions")
    answer = relationship("Answer", back_populates="question", uselist=False, cascade="all, delete-orphan")
