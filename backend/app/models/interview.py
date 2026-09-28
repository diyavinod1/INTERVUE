from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Interview(Base):
    """
    One interview session tied to a candidate. This row is the durable
    counterpart of the LangGraph InterviewState - every time a graph node
    changes something meaningful (topic, difficulty, score, status) the
    InterviewService writes it back here, so a server restart never loses
    interview progress.
    """

    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"))

    status: Mapped[str] = mapped_column(String(30), default="created")
    # created -> in_progress -> completed

    mode: Mapped[str] = mapped_column(String(10), default="text")  # "text" | "voice"

    interview_plan: Mapped[dict] = mapped_column(JSON, default=dict)  # InterviewPlan
    current_topic: Mapped[str] = mapped_column(String(120), default="")
    current_difficulty: Mapped[str] = mapped_column(String(20), default="medium")

    questions_asked: Mapped[int] = mapped_column(Integer, default=0)
    question_limit: Mapped[int] = mapped_column(Integer, default=10)

    overall_score: Mapped[float] = mapped_column(default=0.0)
    topic_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    consecutive_strong: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_weak: Mapped[int] = mapped_column(Integer, default=0)
    covered_topics: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    candidate = relationship("Candidate", back_populates="interviews")
    questions = relationship(
        "Question", back_populates="interview", cascade="all, delete-orphan", order_by="Question.sequence_index"
    )
    final_report = relationship(
        "FinalReport", back_populates="interview", uselist=False, cascade="all, delete-orphan"
    )
