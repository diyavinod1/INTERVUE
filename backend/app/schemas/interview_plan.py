"""
The InterviewPlan is a *loose* roadmap, not a script. LangGraph's decision
node is allowed to skip, reorder, or revisit topics based on how the
candidate actually performs - see agents/nodes/decision.py. The plan exists
so question generation always has a sense of "what haven't we covered yet
that we should," rather than picking topics at random.
"""
from pydantic import BaseModel, Field


class PlannedTopic(BaseModel):
    name: str
    priority: int = 1  # lower = earlier
    source: str = "job"  # "resume" | "job" | "behavioral" | "situational" | "role_fundamentals"
    rationale: str = ""
    expected_difficulty: str = "medium"  # "easy" | "medium" | "hard"


class InterviewPlan(BaseModel):
    # The candidate-selected interview length is persisted inside the existing
    # JSON plan so no database migration is required.
    question_strategy: str = "standard"  # quick | standard | deep | adaptive
    topics: list[PlannedTopic] = Field(default_factory=list)
    opening_focus: str = ""  # what the very first question should orient around
