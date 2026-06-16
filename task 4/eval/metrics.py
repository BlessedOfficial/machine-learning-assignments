from dataclasses import dataclass

from strategies.utils.answer import normalize_numeric_answer


@dataclass
class GradeResult:
    prediction: str
    expected: str
    exact_match: bool
    tolerance_match: bool
    precision_score: float
    abs_error: float | None
    rel_error: float | None

    @property
    def matched(self) -> bool:
        return self.exact_match or self.tolerance_match

    @property
    def match_type(self) -> str:
        if self.exact_match:
            return "exact"
        if self.tolerance_match:
            return "tolerance"
        return "miss"


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def grade_math_answer(
    prediction_raw: str,
    expected_raw: str,
    *,
    rel_tol: float = 0.01,
    abs_tol: float = 1e-9,
) -> GradeResult:
    """
    Math grading policy:
    1) exact numeric-string match after normalization
    2) if exact fails, tolerance match by abs/relative error
    """
    prediction = normalize_numeric_answer(prediction_raw)
    expected = normalize_numeric_answer(expected_raw)

    exact = prediction != "" and prediction == expected
    if exact:
        return GradeResult(
            prediction=prediction,
            expected=expected,
            exact_match=True,
            tolerance_match=False,
            precision_score=1.0,
            abs_error=0.0,
            rel_error=0.0,
        )

    pred_num = _to_float(prediction)
    exp_num = _to_float(expected)
    if pred_num is None or exp_num is None:
        return GradeResult(
            prediction=prediction,
            expected=expected,
            exact_match=False,
            tolerance_match=False,
            precision_score=0.0,
            abs_error=None,
            rel_error=None,
        )

    abs_err = abs(pred_num - exp_num)
    denom = max(abs(exp_num), 1.0)
    rel_err = abs_err / denom

    tolerance_ok = abs_err <= abs_tol or rel_err <= rel_tol
    precision = max(0.0, 1.0 - rel_err)

    return GradeResult(
        prediction=prediction,
        expected=expected,
        exact_match=False,
        tolerance_match=tolerance_ok,
        precision_score=precision,
        abs_error=abs_err,
        rel_error=rel_err,
    )
