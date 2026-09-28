"""
Final report prompt: synthesize a short natural-language summary and
recommended learning areas from the FULL evaluation history. Topic scores
and overall score are computed deterministically in
agents/nodes/final_report.py (simple aggregation, not LLM guesswork) - the
LLM only writes the narrative summary and suggests learning areas, and is
explicitly told never to make personality/psychological claims (PRD Sec.
36).
"""
from langchain_core.prompts import ChatPromptTemplate

FINAL_REPORT_SYSTEM_PROMPT = """You are writing a short, honest post-interview summary for a candidate
based on their technical and behavioral interview performance. Use ONLY the evaluation data given below - do not
invent claims about the candidate's personality, intelligence, honesty, confidence, or mental
state. Stick to observable interview performance, technical strengths/gaps, behavioral strengths/areas to improve, and concrete learning recommendations. Do not make personality claims.

Respond ONLY with a JSON object of this exact shape:
{{"summary": "<3-5 sentence honest overall summary>",
"strengths": ["...", ...up to 5],
"weaknesses": ["...", ...up to 5],
"technical_gaps": ["...", ...up to 5],
"recommended_learning_areas": ["...", ...up to 5]}}"""

FINAL_REPORT_USER_TEMPLATE = """CANDIDATE: {candidate_name}
TARGET ROLE: {target_role}
OVERALL SCORE: {overall_score}/10
TOPIC SCORES: {topic_scores}

PER-QUESTION EVALUATIONS:
{evaluation_summaries}

Write the final report now."""

final_report_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", FINAL_REPORT_SYSTEM_PROMPT),
        ("user", FINAL_REPORT_USER_TEMPLATE),
    ]
)
