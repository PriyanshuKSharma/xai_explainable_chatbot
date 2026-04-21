from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import joblib
except ImportError:  # pragma: no cover - handled at runtime
    joblib = None

from financial_xai.loan_xai import assess_loan_application


MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "model.pkl"
FEATURE_ORDER = [
    "monthly_income",
    "credit_score",
    "monthly_debt_payments",
    "loan_amount",
    "loan_term_years",
    "annual_rate",
    "employment_years",
]


class LoanModelService:
    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        self.model_path = model_path
        self._model: Any | None = None
        self._load_attempted = False

    def _unwrap_model(self, loaded: Any) -> tuple[Any, list[str] | None]:
        """
        Support both legacy pickles (raw sklearn estimators) and a bundled dict:
        {"model": estimator, "feature_order": [...]}.
        """
        if isinstance(loaded, dict) and "model" in loaded:
            model = loaded.get("model")
            feature_order = loaded.get("feature_order")
            if isinstance(feature_order, list) and all(isinstance(x, str) for x in feature_order):
                return model, feature_order
            return model, None
        return loaded, None

    def _load_model(self) -> Any | None:
        if self._load_attempted:
            return self._model

        self._load_attempted = True
        if joblib is None or not self.model_path.exists():
            self._model = None
            return self._model

        self._model = joblib.load(self.model_path)
        return self._model

    def is_available(self) -> bool:
        return self._load_model() is not None

    def predict(self, slots: dict[str, Any]) -> dict[str, Any]:
        explanation = assess_loan_application(slots)
        loaded = self._load_model()

        if loaded is None:
            return {
                **explanation,
                "prediction_source": "transparent_rule_engine",
                "model_loaded": False,
            }

        model, feature_order = self._unwrap_model(loaded)
        order = feature_order or FEATURE_ORDER

        vector = [float(slots.get(feature, 0.0)) for feature in order]
        raw_prediction = model.predict([vector])[0]

        probability = None
        if hasattr(model, "predict_proba"):
            probability = round(float(model.predict_proba([vector])[0][1]) * 100, 1)

        prediction = "Approved" if int(raw_prediction) == 1 else "Rejected"
        merged_probability = probability if probability is not None else explanation["approval_probability"]

        return {
            **explanation,
            "prediction": prediction,
            "approval_probability": merged_probability,
            "prediction_source": "ml_model",
            "model_loaded": True,
            "model_features": order,
        }
