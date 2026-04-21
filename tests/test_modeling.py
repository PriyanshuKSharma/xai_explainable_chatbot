from __future__ import annotations

from financial_xai.modeling import LoanModelService


class StubModel:
    def predict(self, X):  # noqa: N803 - sklearn-like signature
        assert X == [[700.0]]
        return [1]

    def predict_proba(self, X):  # noqa: N803 - sklearn-like signature
        assert X == [[700.0]]
        return [[0.2, 0.8]]


def test_loan_model_bundle_feature_order_is_used() -> None:
    service = LoanModelService()
    service._model = {"model": StubModel(), "feature_order": ["credit_score"]}
    service._load_attempted = True

    out = service.predict({"credit_score": 700})
    assert out["prediction_source"] == "ml_model"
    assert out["model_features"] == ["credit_score"]
    assert out["approval_probability"] == 80.0

