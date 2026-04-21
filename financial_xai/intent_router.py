from __future__ import annotations

import re
from typing import Any

from financial_xai.schemas import ConversationState, FinancialIntent


KEYWORDS: dict[FinancialIntent, tuple[str, ...]] = {
    FinancialIntent.LOAN_ELIGIBILITY: (
        "loan",
        "eligibility",
        "eligible",
        "approval",
        "approved",
        "rejected",
        "credit score",
        "emi",
        "borrow",
    ),
    FinancialIntent.SIMPLE_INTEREST: ("simple interest", "si"),
    FinancialIntent.COMPOUND_INTEREST: ("compound interest", "ci", "compounding", "compund", "compund interest"),
    FinancialIntent.SIP_PROJECTION: ("sip", "systematic investment", "mutual fund", "monthly investment"),
    FinancialIntent.STOCK_GUIDANCE: ("stock", "stocks", "share", "market", "ticker", "quote", "price"),
    FinancialIntent.BANK_PLAN_COMPARISON: (
        "fd",
        "fixed deposit",
        "rd",
        "recurring deposit",
        "bank plan",
        "bank investment",
    ),
    FinancialIntent.FINANCIAL_EDUCATION: (
        "what is",
        "explain",
        "difference between",
        "how does",
        "meaning of",
    ),
}

TICKER_PATTERN = re.compile(r"\b([A-Za-z]{1,10}(?:\.[A-Za-z]{1,4})?)\b")


def _score_intents(message: str) -> dict[FinancialIntent, int]:
    scores: dict[FinancialIntent, int] = {}
    for intent, keywords in KEYWORDS.items():
        count = 0
        for keyword in keywords:
            if len(keyword) <= 3:
                # Use word boundary for short keywords
                if re.search(rf"\b{re.escape(keyword)}\b", message, re.IGNORECASE):
                    count += 1
            elif keyword in message:
                count += 1
        scores[intent] = count
    return scores


def detect_intent(message: str, state: ConversationState | None = None) -> FinancialIntent:
    lowered = message.lower()
    trimmed = lowered.strip()
    scores = _score_intents(lowered)
    best_intent = max(scores, key=scores.get, default=FinancialIntent.GENERAL_FINANCE)
    best_score = scores.get(best_intent, 0)
    loan_cues = (
        "loan",
        "borrow",
        "emi",
        "credit score",
        "cibil",
        "approval",
        "approved",
        "rejected",
        "eligibility",
        "eligible",
        "monthly income",
        "income",
        "salary",
    )
    has_loan_signal = any(term in lowered for term in loan_cues)

    # Single-keyword queries are usually definitional, not live lookups.
    if trimmed in {"stock", "stocks", "share", "shares", "equity"}:
        return FinancialIntent.FINANCIAL_EDUCATION

    if has_loan_signal:
        return FinancialIntent.LOAN_ELIGIBILITY

    if state and state.active_intent and state.pending_questions:
        if best_score <= 1 or best_intent == state.active_intent:
            return state.active_intent

    # Only treat as a ticker-based stock lookup when the phrasing indicates a quote/chart request.
    # Avoid routing definitional questions like "what is stocks" to the live market path.
    if _find_ticker(message) and any(word in lowered for word in ("price", "quote", "ticker", "chart", "trend")):
        return FinancialIntent.STOCK_GUIDANCE
    if any(term in lowered for term in ("compound interest", "compounding", "compund", "compound intrest")):
        return FinancialIntent.COMPOUND_INTEREST
    if any(term in lowered for term in ("simple interest", "simple intrest")):
        return FinancialIntent.SIMPLE_INTEREST
    education_markers = KEYWORDS.get(FinancialIntent.FINANCIAL_EDUCATION, ())
    if any(marker in lowered for marker in education_markers):
        looks_like_lookup = any(word in lowered for word in ("price", "quote", "rate", "roi", "yield")) or re.search(r"\d", lowered)
        if not looks_like_lookup:
            return FinancialIntent.FINANCIAL_EDUCATION
    if best_score > 0:
        return best_intent
    if "interest" in lowered:
        return FinancialIntent.FINANCIAL_EDUCATION
    return FinancialIntent.GENERAL_FINANCE


def _parse_number(raw: str | None) -> float | None:
    if raw is None:
        return None
    return float(raw.replace(",", ""))

# unit-aware amount parsing helpers
UNIT_MULTIPLIERS = {
    "crore": 10_000_000,
    "cr": 10_000_000,
    "lakh": 100_000,
    "lac": 100_000,
    "million": 1_000_000,
    "mn": 1_000_000,
    "billion": 1_000_000_000,
    "bn": 1_000_000_000,
}

WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _parse_word_number(raw: str) -> float | None:
    token = raw.strip().lower()
    return float(WORD_NUMBERS[token]) if token in WORD_NUMBERS else None


def _find_unit_amount(text: str) -> float | None:
    """
    Detect amounts expressed with alphabetical units (e.g., '1 crore', '50 lakh', '2 million').
    Returns numeric value in absolute currency units.
    """
    pattern = re.compile(
        r"(?P<num>[0-9]+(?:\.[0-9]+)?|[A-Za-z]+)\s*(?P<unit>crore|cr|lakh|lac|million|mn|billion|bn)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None

    raw_num = match.group("num")
    unit = match.group("unit").lower()
    multiplier = UNIT_MULTIPLIERS.get(unit, 1)

    try:
        value = float(raw_num.replace(",", ""))
    except ValueError:
        value = _parse_word_number(raw_num)

    if value is None:
        return None
    return value * multiplier


def _find_first(patterns: list[str], text: str) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _parse_number(match.group(1))
    return None


def _find_percentage(text: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", text, flags=re.IGNORECASE)
    return _parse_number(match.group(1)) if match else None


def _find_years(text: str) -> float | None:
    year_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:years?|yrs?)", text, flags=re.IGNORECASE)
    if year_match:
        return _parse_number(year_match.group(1))

    month_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:months?|mos?)", text, flags=re.IGNORECASE)
    if month_match:
        months = _parse_number(month_match.group(1))
        return round(months / 12, 2) if months is not None else None
    return None


def _find_credit_score(text: str) -> float | None:
    patterns = [
        r"credit score\D{0,15}([0-9]{3})",
        r"cibil\D{0,15}([0-9]{3})",
        r"score\D{0,15}([0-9]{3})",
    ]
    return _find_first(patterns, text)


def _find_risk_appetite(text: str) -> str | None:
    lowered = text.lower()
    if "low risk" in lowered or "safe" in lowered or "conservative" in lowered:
        return "low"
    if "medium risk" in lowered or "moderate" in lowered or "balanced" in lowered:
        return "medium"
    if "high risk" in lowered or "aggressive" in lowered:
        return "high"
    return None


def _find_compounding_frequency(text: str) -> int | None:
    lowered = text.lower()
    if "monthly compounding" in lowered or "compounded monthly" in lowered:
        return 12
    if "quarterly compounding" in lowered or "compounded quarterly" in lowered:
        return 4
    if "half yearly" in lowered or "half-yearly" in lowered or "semi annual" in lowered:
        return 2
    if "annual compounding" in lowered or "compounded annually" in lowered:
        return 1
    return None


def _find_stock_view(text: str) -> str | None:
    lowered = text.lower()
    if "volatile" in lowered or "volatility" in lowered:
        return "volatile"
    if "uptrend" in lowered or "bullish" in lowered or "rising" in lowered:
        return "uptrend"
    if "downtrend" in lowered or "bearish" in lowered or "falling" in lowered:
        return "downtrend"
    return None


def _find_bank(text: str) -> str | None:
    match = re.search(
        r"\b(SBI|HDFC|ICICI|AXIS|KOTAK|PNB|BOB|CANARA|IDFC|YES|INDUSIND)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).upper()


def _find_ticker(text: str) -> str | None:
    protected_words = {
        "loan",
        "sip",
        "fd",
        "rd",
        "stock",
        "stocks",
        "share",
        "shares",
        "price",
        "show",
        "what",
        "give",
        "market",
        "a",
        "is",
        "the",
        "of",
        "for",
        "me",
    }
    for token in TICKER_PATTERN.findall(text):
        normalized = token.upper()
        if normalized.lower() in protected_words:
            continue
        if any(char.isdigit() for char in normalized):
            continue
        if len(normalized) == 1:
            continue
        return normalized
    return None


def extract_slots(message: str, intent: FinancialIntent) -> dict[str, Any]:
    slots: dict[str, Any] = {}
    years = _find_years(message)
    rate = _find_percentage(message)
    risk_appetite = _find_risk_appetite(message)

    if years is not None:
        slots["years"] = years
    if rate is not None:
        slots["annual_rate"] = rate
    if risk_appetite is not None:
        slots["risk_appetite"] = risk_appetite

    if intent in {FinancialIntent.SIMPLE_INTEREST, FinancialIntent.COMPOUND_INTEREST}:
        principal = _find_first(
            [
                r"(?:principal|amount|sum|deposit)\D{0,15}([0-9][0-9,]*(?:\.[0-9]+)?)",
                r"([0-9][0-9,]*(?:\.[0-9]+)?)\D{0,10}(?:principal|amount|deposit)",
                r"on\D{0,10}([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
            message,
        )
        if principal is None:
            principal = _find_unit_amount(message)
        if principal is not None:
            slots["principal"] = principal

    if intent == FinancialIntent.COMPOUND_INTEREST:
        frequency = _find_compounding_frequency(message)
        if frequency is not None:
            slots["compounds_per_year"] = frequency

    if intent == FinancialIntent.SIP_PROJECTION:
        monthly_investment = _find_first(
            [
                r"(?:monthly investment|monthly sip|sip amount)\D{0,15}([0-9][0-9,]*(?:\.[0-9]+)?)",
                r"invest(?:ing)?\D{0,10}([0-9][0-9,]*(?:\.[0-9]+)?)\D{0,10}(?:monthly|every month)",
                r"([0-9][0-9,]*(?:\.[0-9]+)?)\D{0,10}(?:monthly|per month)",
            ],
            message,
        )
        if monthly_investment is not None:
            slots["monthly_investment"] = monthly_investment

    if intent == FinancialIntent.LOAN_ELIGIBILITY:
        monthly_income = _find_first(
            [
                r"(?:income|salary|earn(?:ing)?)\D{0,15}([0-9][0-9,]*(?:\.[0-9]+)?)",
                r"([0-9][0-9,]*(?:\.[0-9]+)?)\D{0,10}(?:income|salary)",
            ],
            message,
        )
        loan_amount = _find_first(
            [
                r"(?:loan amount|loan of|borrow|need loan)\D{0,15}([0-9][0-9,]*(?:\.[0-9]+)?)",
                r"([0-9][0-9,]*(?:\.[0-9]+)?)\D{0,10}(?:loan)",
            ],
            message,
        )
        if loan_amount is None:
            loan_amount = _find_unit_amount(message)
        monthly_debt_payments = _find_first(
            [
                r"(?:existing emi|existing debt|monthly debt|current emi)\D{0,15}([0-9][0-9,]*(?:\.[0-9]+)?)",
                r"([0-9][0-9,]*(?:\.[0-9]+)?)\D{0,10}(?:existing emi|monthly debt|current emi)",
            ],
            message,
        )
        employment_years = _find_first(
            [
                r"(?:working for|job for|employment)\D{0,15}([0-9]+(?:\.[0-9]+)?)",
                r"([0-9]+(?:\.[0-9]+)?)\D{0,10}(?:years in job|years of work)",
            ],
            message,
        )
        credit_score = _find_credit_score(message)

        if monthly_income is not None:
            slots["monthly_income"] = monthly_income
        if loan_amount is not None:
            slots["loan_amount"] = loan_amount
        if credit_score is not None:
            slots["credit_score"] = credit_score
        if monthly_debt_payments is not None:
            slots["monthly_debt_payments"] = monthly_debt_payments
        if employment_years is not None:
            slots["employment_years"] = employment_years
        if years is not None:
            slots["loan_term_years"] = years

    if intent == FinancialIntent.BANK_PLAN_COMPARISON:
        lowered = message.lower()
        product_type = None
        if "fixed deposit" in lowered or re.search(r"\bfd\b", lowered):
            product_type = "FD"
        elif "recurring deposit" in lowered or re.search(r"\brd\b", lowered):
            product_type = "RD"
        elif "savings" in lowered:
            product_type = "SAVINGS"

        bank = _find_bank(message)

        lump_sum = _find_first(
            [
                r"(?:lump sum|deposit|invest once)\D{0,15}([0-9][0-9,]*(?:\.[0-9]+)?)",
                r"(?:invest)\D{0,10}([0-9][0-9,]*(?:\.[0-9]+)?)\D{0,10}(?:one time|lump sum)",
            ],
            message,
        )
        monthly_amount = _find_first(
            [
                r"(?:monthly savings|monthly amount|monthly investment)\D{0,15}([0-9][0-9,]*(?:\.[0-9]+)?)",
                r"([0-9][0-9,]*(?:\.[0-9]+)?)\D{0,10}(?:monthly|per month)",
            ],
            message,
        )
        if lump_sum is not None:
            slots["lump_sum"] = lump_sum
        if monthly_amount is not None:
            slots["monthly_amount"] = monthly_amount
        if product_type is not None:
            slots["product_type"] = product_type
        if bank is not None:
            slots["bank"] = bank

    if intent == FinancialIntent.STOCK_GUIDANCE:
        stock_view = _find_stock_view(message)
        ticker = _find_ticker(message)
        if stock_view is not None:
            slots["stock_view"] = stock_view
        if ticker is not None:
            slots["ticker"] = ticker

    return slots
