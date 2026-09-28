"""
Follow-up questions use the exact same prompt as every other adaptive
question (see question_generator.py) with action="FOLLOW_UP" - a follow-up
IS a question generation call, just one where the instruction to the model
is "dig into what they just said" rather than "change topic" or "go
harder." Keeping a separate prompt template here would just duplicate the
question_generator template and risk them drifting out of sync, so this
module simply re-exports it under the name PRD Sec. 43's file layout
expects.
"""
from app.agents.prompts.question_generator import question_generator_prompt as followup_prompt

__all__ = ["followup_prompt"]
