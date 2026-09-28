from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class FinalReport(Base):
    __tablename__ = "final_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    interview_id: Mapped[str] = mapped_column(String(36), ForeignKey("interviews.id"), unique=True)

    overall_score: Mapped[float] = mapped_column(Float)
    topic_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list] = mapped_column(JSON, default=list)
    technical_gaps: Mapped[list] = mapped_column(JSON, default=list)
    recommended_learning_areas: Mapped[list] = mapped_column(JSON, default=list)
    question_count: Mapped[int] = mapped_column(default=0)
    summary: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="final_report")
