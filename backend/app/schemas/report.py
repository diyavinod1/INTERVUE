from pydantic import BaseModel, Field


class QuestionAnswerSummary(BaseModel):
    topic: str
    difficulty: str
    question: str
    answer: str
    score: float
    feedback: str


class FinalReportResponse(BaseModel):
    interview_id: str
    candidate_name: str
    target_role: str
    overall_score: float
    topic_scores: dict[str, float]
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    technical_gaps: list[str] = Field(default_factory=list)
    recommended_learning_areas: list[str] = Field(default_factory=list)
    question_count: int
    summary: str
    qa_history: list[QuestionAnswerSummary] = Field(default_factory=list)
