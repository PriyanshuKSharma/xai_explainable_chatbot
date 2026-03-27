from __future__ import annotations

from typing import Any

from financial_xai.calculations import emi


def assess_loan_application(data: dict[str, Any]) -> dict[str, Any]:
    monthly_income = float(data["monthly_income"])
    credit_score = float(data["credit_score"])
    loan_amount = float(data["loan_amount"])
    loan_term_years = float(data["loan_term_years"])
    monthly_debt_payments = float(data.get("monthly_debt_payments", 0))
    annual_interest_rate = data.get("annual_rate")
    employment_years = data.get("employment_years")

    base_score = 0.5
    feature_impacts: list[tuple[str, float]] = []

    if credit_score >= 750:
        feature_impacts.append(("Credit score is strong for most lending policies.", 0.18))
    elif credit_score >= 700:
        feature_impacts.append(("Credit score is comfortably above the risky range.", 0.10))
    elif credit_score >= 650:
        feature_impacts.append(("Credit score is acceptable but not especially strong.", 0.02))
    elif credit_score >= 600:
        feature_impacts.append(("Credit score is borderline and can reduce approval odds.", -0.08))
    else:
        feature_impacts.append(("Credit score is low and becomes the biggest approval risk.", -0.20))

    loan_to_annual_income = loan_amount / max(monthly_income * 12, 1)
    if loan_to_annual_income <= 3:
        feature_impacts.append(("Requested loan size is reasonable relative to annual income.", 0.12))
    elif loan_to_annual_income <= 5:
        feature_impacts.append(("Loan size is manageable but not especially conservative.", 0.03))
    elif loan_to_annual_income <= 7:
        feature_impacts.append(("Loan size is stretching income capacity.", -0.08))
    else:
        feature_impacts.append(("Loan size is very high relative to annual income.", -0.18))

    existing_debt_ratio = monthly_debt_payments / max(monthly_income, 1)
    if existing_debt_ratio <= 0.10:
        feature_impacts.append(("Existing debt obligations are light compared with income.", 0.05))
    elif existing_debt_ratio <= 0.25:
        feature_impacts.append(("Existing debt is moderate and should be watched.", 0.0))
    else:
        feature_impacts.append(("Existing debt load is already heavy.", -0.08))

    projected_emi = None
    total_obligation_ratio = None
    if annual_interest_rate is not None:
        projected_emi = emi(loan_amount, float(annual_interest_rate), loan_term_years)
        total_obligation_ratio = (monthly_debt_payments + projected_emi) / max(monthly_income, 1)
        if total_obligation_ratio <= 0.35:
            feature_impacts.append(("Projected debt burden remains comfortably within affordability.", 0.18))
        elif total_obligation_ratio <= 0.45:
            feature_impacts.append(("Projected debt burden is acceptable but leaves less cushion.", 0.08))
        elif total_obligation_ratio <= 0.55:
            feature_impacts.append(("Projected debt burden is elevated and can trigger caution.", -0.08))
        else:
            feature_impacts.append(("Projected debt burden is high and is likely to hurt approval odds.", -0.20))

    if employment_years is not None:
        employment_years = float(employment_years)
        if employment_years >= 3:
            feature_impacts.append(("Employment history is stable, which supports repayment confidence.", 0.05))
        elif employment_years < 1:
            feature_impacts.append(("Short employment history slightly weakens stability.", -0.05))

    raw_score = base_score + sum(weight for _, weight in feature_impacts)
    approval_probability = round(max(0.05, min(0.95, raw_score)) * 100, 1)

    if approval_probability >= 65:
        prediction = "Approved"
    elif approval_probability >= 48:
        prediction = "Needs review"
    else:
        prediction = "Rejected"

    ranked_factors = sorted(feature_impacts, key=lambda item: abs(item[1]), reverse=True)
    top_positive = [reason for reason, weight in ranked_factors if weight > 0][:2]
    top_negative = [reason for reason, weight in ranked_factors if weight < 0][:2]

    global_insights = [
        "Higher credit scores consistently improve approval probability in this transparent scoring model.",
        "Lower debt burden relative to income tends to move approval from borderline to stable.",
        "Loan amounts that stretch annual income usually become the first affordability warning signal.",
    ]

    if total_obligation_ratio is not None:
        global_insights.append(
            "Once total monthly obligations move much beyond roughly 45 percent of income, approval usually weakens sharply."
        )

    return {
        "prediction": prediction,
        "approval_probability": approval_probability,
        "projected_emi": projected_emi,
        "loan_to_annual_income": round(loan_to_annual_income, 2),
        "existing_debt_ratio": round(existing_debt_ratio * 100, 2),
        "total_obligation_ratio": round(total_obligation_ratio * 100, 2) if total_obligation_ratio is not None else None,
        "top_positive": top_positive,
        "top_negative": top_negative,
        "global_insights": global_insights,
    }
