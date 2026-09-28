from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    answer_id: Mapped[str] = mapped_column(String(36), ForeignKey("answers.id"), unique=True)
    interview_id: Mapped[str] = mapped_column(String(36), ForeignKey("interviews.id"), index=True)

    overall_score: Mapped[float] = mapped_column(Float)
    correctness: Mapped[float] = mapped_column(Float)
    completeness: Mapped[float] = mapped_column(Float)
    technical_depth: Mapped[float] = mapped_column(Float)
    relevance: Mapped[float] = mapped_column(Float)
    clarity: Mapped[float] = mapped_column(Float)

    strengths: Mapped[list] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list] = mapped_column(JSON, default=list)
    missing_concepts: Mapped[list] = mapped_column(JSON, default=list)

    feedback: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(String(40))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    answer = relationship("Answer", back_populates="evaluation")
