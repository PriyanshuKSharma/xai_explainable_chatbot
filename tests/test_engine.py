from financial_xai.engine import FinancialAssistantEngine
from financial_xai.schemas import ChatRequest, FinancialIntent


class FakeStockService:
    def get_stock_snapshot(self, ticker: str) -> dict[str, object]:
        return {
            "ticker": ticker,
            "price": 189.42,
            "daily_change": 1.82,
            "daily_change_pct": 0.97,
            "trend": "uptrend",
            "risk_level": "medium",
            "as_of": "2026-03-27 09:15:00",
        }


def test_compound_interest_response() -> None:
    engine = FinancialAssistantEngine()
    response = engine.respond(ChatRequest(message="Compound interest on 100000 at 8% for 2 years"))

    assert response.intent == FinancialIntent.COMPOUND_INTEREST
    assert "Compound interest is" in response.answer.result
    assert response.follow_up_questions == []


def test_loan_query_requests_missing_information() -> None:
    engine = FinancialAssistantEngine()
    response = engine.respond(ChatRequest(message="My credit score is 600, will I get a loan?"))

    assert response.intent == FinancialIntent.LOAN_ELIGIBILITY
    assert "monthly income" in " ".join(question.lower() for question in response.follow_up_questions)
    assert "loan_amount" in response.missing_fields


def test_complete_loan_query_returns_assessment() -> None:
    engine = FinancialAssistantEngine()
    response = engine.respond(
        ChatRequest(
            message=(
                "My income is 85000, credit score is 742, loan amount is 1200000, "
                "term is 5 years, existing EMI is 12000"
            )
        )
    )

    assert response.intent == FinancialIntent.LOAN_ELIGIBILITY
    assert "Loan assessment:" in response.answer.result
    assert response.metadata["prediction_source"] in {"transparent_rule_engine", "ml_model"}


def test_stock_query_requires_ticker() -> None:
    engine = FinancialAssistantEngine()
    response = engine.respond(ChatRequest(message="Show me the stock price"))

    assert response.intent == FinancialIntent.STOCK_GUIDANCE
    assert response.follow_up_questions == ["Which stock ticker should I look up?"]


def test_stock_query_returns_live_snapshot_when_service_available() -> None:
    engine = FinancialAssistantEngine(stock_data_service=FakeStockService())
    response = engine.respond(ChatRequest(message="Show me the stock price for AAPL"))

    assert response.intent == FinancialIntent.STOCK_GUIDANCE
    assert "Latest price for AAPL is 189.42" in response.answer.result
    assert response.metadata["ticker"] == "AAPL"
    assert response.metadata["chart_url"].startswith("/api/stock/chart?ticker=AAPL")
    assert "![AAPL price chart](" in response.reply_markdown


def test_stock_definition_routes_to_education() -> None:
    engine = FinancialAssistantEngine(stock_data_service=FakeStockService())
    response = engine.respond(ChatRequest(message="What is a stock?"))

    assert response.intent == FinancialIntent.FINANCIAL_EDUCATION
    assert "ownership" in response.answer.result.lower()


def test_bank_fd_rate_lookup_uses_dataset() -> None:
    engine = FinancialAssistantEngine(stock_data_service=FakeStockService())
    response = engine.respond(ChatRequest(message="FD interest rate in SBI for 2 years"))

    assert response.intent == FinancialIntent.BANK_PLAN_COMPARISON
    assert "SBI FD rate" in response.answer.result
    assert response.metadata["bank_rates"][0]["bank"] == "SBI"
