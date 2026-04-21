#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
from pathlib import Path
from typing import Any

from joblib import dump
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


DEFAULT_FEATURES = [
    "monthly_income",
    "credit_score",
    "monthly_debt_payments",
    "loan_amount",
    "loan_term_years",
    "annual_rate",
    "employment_years",
]

COLUMN_ALIASES = {
    "income": "monthly_income",
    "monthlyincome": "monthly_income",
    "creditscore": "credit_score",
    "cibil": "credit_score",
    "loanamount": "loan_amount",
    "loan": "loan_amount",
    "monthlydebtpayments": "monthly_debt_payments",
    "existingemi": "monthly_debt_payments",
    "loantermyears": "loan_term_years",
    "term": "loan_term_years",
    "annualrate": "annual_rate",
    "rate": "annual_rate",
    "employmentyears": "employment_years",
}


def _norm(col: str) -> str:
    return "".join(ch for ch in col.strip().lower() if ch.isalnum())


def _resolve_column_map(header: list[str]) -> dict[str, str]:
    # csv_column -> canonical_feature_name
    mapping: dict[str, str] = {}
    for col in header:
        key = _norm(col)
        canonical = COLUMN_ALIASES.get(key, None)
        if canonical is None and key in { _norm(f) for f in DEFAULT_FEATURES }:
            # If already canonical (e.g., monthly_income), keep it.
            canonical = col.strip().lower()
        if canonical:
            mapping[col] = canonical
    return mapping


def _read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit("CSV has no header row.")
        rows = [row for row in reader if row]
        return list(reader.fieldnames), rows


def _as_float(raw: Any) -> float:
    if raw is None:
        return 0.0
    s = str(raw).strip().replace(",", "")
    if s == "":
        return 0.0
    return float(s)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a loan eligibility model and write models/model.pkl.")
    parser.add_argument("--data", type=Path, default=Path("loan_data.csv"), help="Input CSV path.")
    parser.add_argument("--out", type=Path, default=Path("models/model.pkl"), help="Output .pkl path.")
    parser.add_argument("--target", type=str, default="Approved", help="Target column name (default: Approved).")
    parser.add_argument(
        "--features",
        type=str,
        default="",
        help="Comma-separated feature list. Default: auto-detect from CSV header.",
    )
    parser.add_argument("--test-size", type=float, default=0.2, help="Holdout fraction (default: 0.2).")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42).")
    args = parser.parse_args()

    if not args.data.exists():
        raise SystemExit(f"Dataset not found: {args.data}")

    header, rows = _read_csv_rows(args.data)
    if not rows:
        raise SystemExit("Dataset has no data rows.")

    # Determine target column (case-insensitive match).
    target_col = None
    for col in header:
        if col.strip().lower() == args.target.strip().lower():
            target_col = col
            break
    if target_col is None:
        raise SystemExit(f"Target column '{args.target}' not found in CSV header: {header}")

    col_map = _resolve_column_map([c for c in header if c != target_col])

    if args.features.strip():
        feature_order = [f.strip().lower() for f in args.features.split(",") if f.strip()]
    else:
        # Auto-detect: include known features present in CSV.
        feature_order = []
        for csv_col, canonical in col_map.items():
            if canonical in DEFAULT_FEATURES and canonical not in feature_order:
                feature_order.append(canonical)

    # Fallback for the provided synthetic dataset schema.
    if not feature_order:
        # Try common old schema: Income/CreditScore/LoanAmount
        possible = {"monthly_income", "credit_score", "loan_amount"}
        for canonical in DEFAULT_FEATURES:
            if canonical in possible:
                feature_order.append(canonical)

    if not feature_order:
        raise SystemExit("No usable feature columns detected. Provide --features explicitly.")

    # Build X/y
    X: list[list[float]] = []
    y: list[int] = []

    # Build reverse map: canonical_feature -> csv_column
    canonical_to_csv: dict[str, str] = {}
    for csv_col, canonical in col_map.items():
        if canonical not in canonical_to_csv:
            canonical_to_csv[canonical] = csv_col

    for row in rows:
        try:
            label = int(float(str(row.get(target_col, "0")).strip() or "0"))
        except ValueError:
            continue

        vector: list[float] = []
        for feature in feature_order:
            csv_col = canonical_to_csv.get(feature)
            vector.append(_as_float(row.get(csv_col)) if csv_col else 0.0)

        X.append(vector)
        y.append(1 if label == 1 else 0)

    if len(set(y)) < 2:
        raise SystemExit("Target column must contain both classes (0 and 1) to train a classifier.")

    n = len(y)
    class0 = sum(1 for v in y if v == 0)
    class1 = n - class0

    # For tiny datasets, stratified splitting can fail (needs enough rows per class in both splits).
    use_stratify = min(class0, class1) >= 2 and n >= 10

    # Ensure test split has at least 2 rows when evaluating, otherwise sklearn can error.
    if args.test_size <= 0:
        test_size: int | float = 0
    else:
        proposed = int(round(n * args.test_size)) if args.test_size < 1 else int(args.test_size)
        proposed = max(2, proposed)
        proposed = min(n - 2, proposed) if n > 4 else max(1, n - 1)
        test_size = proposed

    if test_size == 0:
        X_train, y_train = X, y
        X_test, y_test = [], []
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=args.seed,
            stratify=y if use_stratify else None,
        )

    pipeline: Pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=args.seed)),
        ]
    )
    pipeline.fit(X_train, y_train)

    acc = None
    auc = None
    if X_test:
        y_pred = pipeline.predict(X_test)
        y_prob = None
        try:
            y_prob = pipeline.predict_proba(X_test)[:, 1]
        except Exception:
            y_prob = None

        acc = float(accuracy_score(y_test, y_pred))
        auc = float(roc_auc_score(y_test, y_prob)) if y_prob is not None else None

        print(f"Trained LogisticRegression on {len(X_train)} rows; test_rows={len(X_test)} (stratify={use_stratify}).")
        print(f"Accuracy: {acc:.4f}" + (f"  ROC-AUC: {auc:.4f}" if auc is not None else ""))
        print(classification_report(y_test, y_pred, digits=4))
    else:
        print(f"Trained LogisticRegression on {len(X_train)} rows; no test split (test_size=0).")

    bundle = {
        "schema_version": 1,
        "trained_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": pipeline,
        "feature_order": feature_order,
        "metrics": {"accuracy": acc, "roc_auc": auc},
        "source_data": str(args.data),
        "target": target_col,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    dump(bundle, args.out)
    print(f"Wrote model bundle to {args.out} with features={feature_order}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
