from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FinancialIntent(str, Enum):
    LOAN_ELIGIBILITY = "loan_eligibility"
    SIMPLE_INTEREST = "simple_interest"
    COMPOUND_INTEREST = "compound_interest"
    SIP_PROJECTION = "sip_projection"
    STOCK_GUIDANCE = "stock_guidance"
    BANK_PLAN_COMPARISON = "bank_plan_comparison"
    FINANCIAL_EDUCATION = "financial_education"
    GENERAL_FINANCE = "general_finance"


class ConversationState(BaseModel):
    active_intent: FinancialIntent | None = None
    collected_data: dict[str, Any] = Field(default_factory=dict)
    pending_questions: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation: ConversationState | None = None


class StructuredAnswer(BaseModel):
    result: str
    explanation: list[str]
    insight: list[str]
    suggestion: list[str]


class ChatResponse(BaseModel):
    intent: FinancialIntent
    answer: StructuredAnswer
    reply_markdown: str
    missing_fields: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    conversation: ConversationState
    metadata: dict[str, Any] = Field(default_factory=dict)
