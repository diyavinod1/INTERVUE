import pytest
from pydantic import ValidationError

from app.schemas.evaluation import AnswerEvaluation


def test_valid_evaluation_parses():
    ev = AnswerEvaluation(
        overall_score=7, correctness=8, completeness=6, technical_depth=7, relevance=9, clarity=7,
        strengths=["Clear explanation"], weaknesses=["Missed edge cases"], missing_concepts=["idempotency"],
        feedback="Solid answer overall.", recommended_action="FOLLOW_UP",
    )
    assert ev.overall_score == 7


def test_out_of_range_scores_are_clamped_not_rejected():
    ev = AnswerEvaluation(
        overall_score=15, correctness=-3, completeness=6, technical_depth=7, relevance=9, clarity=7,
    )
    assert ev.overall_score == 10.0
    assert ev.correctness == 0.0


def test_non_numeric_score_falls_back_to_neutral():
    ev = AnswerEvaluation(
        overall_score="not a number", correctness=8, completeness=6, technical_depth=7, relevance=9, clarity=7,
    )
    assert ev.overall_score == 5.0


def test_invalid_recommended_action_is_rejected():
    with pytest.raises(ValidationError):
        AnswerEvaluation(
            overall_score=7, correctness=8, completeness=6, technical_depth=7, relevance=9, clarity=7,
            recommended_action="DO_A_BACKFLIP",
        )
