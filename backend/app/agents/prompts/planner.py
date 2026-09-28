"""
Planner prompt: given the candidate + job profiles, produce short natural-
language *rationale* strings for a topic list. Note that WHICH topics get
picked is decided deterministically in agents/nodes/planning.py (matching
skills/projects to the job requirements) - the LLM's only job here is to
explain, in one sentence each, why each topic is worth exploring. This
keeps the plan itself reproducible/testable while still reading naturally.
"""
from langchain_core.prompts import ChatPromptTemplate

PLANNER_SYSTEM_PROMPT = """You are helping prepare rationale notes for a realistic technical + behavioral + situational interview plan.
You will be given a candidate's background, a target job, and a list of topic names that have
already been selected by the interview system. For EACH topic, write exactly one short sentence
(under 20 words) explaining why it is worth exploring for THIS candidate and THIS job.
Also write one short sentence for "opening_focus" describing what the very first question should
orient around.

Respond ONLY with a JSON object of this exact shape, nothing else:
{{"rationales": {{"<topic name>": "<one sentence>", ...}}, "opening_focus": "<one sentence>"}}

Do not include any text outside the JSON object. Do not invent skills or projects the candidate
does not have - only use what's given below."""

PLANNER_USER_TEMPLATE = """CANDIDATE BACKGROUND:
{candidate_context}

TARGET JOB:
{job_context}

TOPICS ALREADY SELECTED (do not add or remove topics, just explain them):
{topic_names}"""

planner_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", PLANNER_SYSTEM_PROMPT),
        ("user", PLANNER_USER_TEMPLATE),
    ]
)
