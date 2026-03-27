#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import os
import random
import tempfile
from pathlib import Path


def _clamp_int(value: float, *, low: int, high: int) -> int:
    return int(max(low, min(high, round(value))))


def _sigmoid(x: float) -> float:
    # Numerically stable enough for our small magnitudes here.
    return 1.0 / (1.0 + math.exp(-x))


def _read_header(csv_path: Path) -> list[str] | None:
    if not csv_path.exists():
        return None
    with csv_path.open("r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                return [cell.strip() for cell in row]
            break
    return None


def _generate_row(rng: random.Random) -> dict[str, int]:
    # Income: roughly 20k–250k, skewed slightly high.
    income = _clamp_int(rng.lognormvariate(math.log(65000), 0.45), low=20000, high=250000)

    # Credit score: 300–850 (normal-ish around 650).
    credit_score = _clamp_int(rng.gauss(650, 75), low=300, high=850)

    # Loan amount: correlated with income and mildly with credit score.
    # Keep it within 1k–150k to stay reasonable for demo/training.
    base = income * rng.uniform(0.08, 0.55)
    credit_factor = 0.85 + ((credit_score - 300) / 550) * 0.35  # ~0.85–1.20
    loan_amount = _clamp_int(base * credit_factor, low=1000, high=150000)

    # Approval probability: higher credit/income, lower loan-to-income ratio.
    loan_to_income = loan_amount / max(income, 1)
    logit = (
        -1.15
        + 0.0125 * (credit_score - 650)
        + 0.000012 * (income - 65000)
        - 5.25 * (loan_to_income - 0.25)
    )
    approval_prob = _sigmoid(logit)
    approved = 1 if rng.random() < approval_prob else 0

    return {
        "Income": income,
        "CreditScore": credit_score,
        "LoanAmount": loan_amount,
        "Approved": approved,
    }


def _write_csv_atomic(out_path: Path, rows: list[dict[str, int]], header: list[str]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        newline="",
        delete=False,
        dir=str(out_path.parent),
        prefix=f".{out_path.name}.",
        suffix=".tmp",
    ) as tmp:
        tmp_path = Path(tmp.name)
        writer = csv.DictWriter(tmp, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    os.replace(tmp_path, out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a large synthetic loan dataset CSV.")
    parser.add_argument("--rows", type=int, default=50000, help="Number of rows to generate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("loan_data.csv"),
        help="Output CSV path (default: loan_data.csv).",
    )
    parser.add_argument(
        "--schema-from",
        type=Path,
        default=Path("loan_data.csv"),
        help="CSV to read header/schema from (default: loan_data.csv).",
    )
    args = parser.parse_args()

    if args.rows <= 0:
        raise SystemExit("--rows must be > 0")

    rng = random.Random(args.seed)

    header = _read_header(args.schema_from) or ["Income", "CreditScore", "LoanAmount", "Approved"]
    expected = {"Income", "CreditScore", "LoanAmount", "Approved"}
    if set(header) != expected:
        raise SystemExit(
            f"Unsupported schema in {args.schema_from}: {header}. "
            f"Expected columns: {sorted(expected)}"
        )

    rows: list[dict[str, int]] = []
    approved_count = 0
    for _ in range(args.rows):
        row = _generate_row(rng)
        approved_count += row["Approved"]
        rows.append(row)

    _write_csv_atomic(args.out, rows, header)

    approval_rate = approved_count / args.rows
    print(f"Wrote {args.rows} rows to {args.out} (approval_rate={approval_rate:.3f}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

