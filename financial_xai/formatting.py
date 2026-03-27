from __future__ import annotations

from typing import Iterable

from financial_xai.schemas import StructuredAnswer


def format_currency(value: float) -> str:
    return f"Rs. {value:,.2f}"


def format_percent(value: float) -> str:
    return f"{value:.2f}%"


def join_bullets(items: Iterable[str]) -> str:
    values = [f"- {item}" for item in items]
    return "\n".join(values)


def format_structured_reply(answer: StructuredAnswer) -> str:
    parts = [
        "Result:",
        answer.result,
        "",
        "Explanation:",
        join_bullets(answer.explanation),
        "",
        "Insight:",
        join_bullets(answer.insight),
        "",
        "Suggestion:",
        join_bullets(answer.suggestion),
    ]
    return "\n".join(parts)
