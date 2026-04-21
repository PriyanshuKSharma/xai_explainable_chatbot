from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from financial_xai.calculations import compound_interest, fd_maturity, rd_maturity, simple_interest, sip_future_value
from financial_xai.formatting import format_currency, format_percent, format_structured_reply
from financial_xai.intent_router import detect_intent, extract_slots
from financial_xai.bank_service import BankProductService
from financial_xai.modeling import LoanModelService
from financial_xai.schemas import ChatRequest, ChatResponse, ConversationState, FinancialIntent, StructuredAnswer, NewChatResponse, Visualization
from financial_xai.stock_service import StockDataError, StockDataService
from financial_xai.ai_services import AIProvider


@dataclass
class HandlerResult:
    answer: StructuredAnswer
    missing_fields: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class FinancialAssistantEngine:
    def __init__(
        self,
        loan_model_service: LoanModelService | None = None,
        stock_data_service: StockDataService | None = None,
        bank_product_service: BankProductService | None = None,
        ai_provider: AIProvider | None = None,
    ) -> None:
        self.loan_model_service = loan_model_service or LoanModelService()
        self.stock_data_service = stock_data_service or StockDataService()
        self.bank_product_service = bank_product_service or BankProductService()
        self.ai_provider = ai_provider or AIProvider()

    def respond(self, request: ChatRequest) -> ChatResponse:
        previous_state = request.conversation or ConversationState()
        intent = detect_intent(request.message, previous_state)
        extracted_slots = extract_slots(request.message, intent)

        if previous_state.active_intent == intent:
            merged_slots = {**previous_state.collected_data, **extracted_slots}
        else:
            merged_slots = extracted_slots

        result = self._dispatch(intent, request.message, merged_slots)
        conversation = ConversationState(
            active_intent=intent,
            collected_data=merged_slots,
            pending_questions=result.follow_up_questions,
        )

        # Map intent to new format types
        intent_map = {
            FinancialIntent.LOAN_ELIGIBILITY: "loan",
            FinancialIntent.SIP_PROJECTION: "sip",
            FinancialIntent.STOCK_GUIDANCE: "stock",
            FinancialIntent.SIMPLE_INTEREST: "si",
            FinancialIntent.COMPOUND_INTEREST: "ci",
        }
        resp_type = intent_map.get(intent, "general")

        # Extract visualization data
        viz_type = "chart"
        viz_data = {}
        if resp_type == "loan":
            viz_type = "lime"
            # Extract impact reasons for visualization
            viz_data = {
                "probability": result.metadata.get("approval_probability"),
                "impacts": result.metadata.get("top_positive", []) + result.metadata.get("top_negative", [])
            }
        elif resp_type == "sip":
            viz_type = "chart"
            # Generate growth schedule if not present
            viz_data = result.metadata
        elif resp_type == "stock":
            viz_type = "stock"
            viz_data = result.metadata
        elif resp_type in ("si", "ci"):
            viz_type = "chart"
            viz_data = result.metadata

        # AI-powered refinement (Gemini/Groq)
        enhanced = self.ai_provider.get_enhanced_content(
            intent=resp_type,
            slots=merged_slots,
            metadata=result.metadata,
            base_result=result.answer.result
        )

        explanation = result.answer.explanation
        suggestion = result.answer.suggestion[0] if result.answer.suggestion else None

        if enhanced:
            # Prepend Gemini explanation but keep rule-based one for transparency
            explanation = enhanced.explanation + [f"(Verified by rule engine: {e})" for e in explanation[:1]]
            suggestion = enhanced.suggestion

        formatted = NewChatResponse(
            type=resp_type,
            result=result.answer.result,
            explanation=explanation,
            visualization=Visualization(type=viz_type, data=viz_data),
            suggestion=suggestion,
        )

        reply_markdown = format_structured_reply(result.answer)
        if resp_type == "stock" and "error" not in (result.metadata or {}) and "price" in (result.metadata or {}):
            ticker = str(result.metadata.get("ticker") or merged_slots.get("ticker") or "").strip()
            if ticker:
                chart_url = f"/api/stock/chart?ticker={quote(ticker)}&period=1mo"
                result.metadata.setdefault("chart_url", chart_url)
                reply_markdown = f"{reply_markdown}\n\nChart:\n![{ticker} price chart]({chart_url})"

        return ChatResponse(
            intent=intent,
            answer=result.answer,
            reply_markdown=reply_markdown,
            missing_fields=result.missing_fields,
            follow_up_questions=result.follow_up_questions,
            conversation=conversation,
            metadata=result.metadata,
            formatted=formatted,
        )

    def _dispatch(self, intent: FinancialIntent, message: str, slots: dict[str, Any]) -> HandlerResult:
        handlers = {
            FinancialIntent.LOAN_ELIGIBILITY: self._handle_loan_eligibility,
            FinancialIntent.SIMPLE_INTEREST: self._handle_simple_interest,
            FinancialIntent.COMPOUND_INTEREST: self._handle_compound_interest,
            FinancialIntent.SIP_PROJECTION: self._handle_sip_projection,
            FinancialIntent.STOCK_GUIDANCE: self._handle_stock_guidance,
            FinancialIntent.BANK_PLAN_COMPARISON: self._handle_bank_plan_comparison,
            FinancialIntent.FINANCIAL_EDUCATION: self._handle_education,
            FinancialIntent.GENERAL_FINANCE: self._handle_general_finance,
        }
        return handlers[intent](message, slots)

    def _missing_answer(
        self,
        result: str,
        explanation: list[str],
        insight: list[str],
        suggestion: list[str],
        missing_fields: list[str],
        follow_up_questions: list[str],
    ) -> HandlerResult:
        return HandlerResult(
            answer=StructuredAnswer(
                result=result,
                explanation=explanation,
                insight=insight,
                suggestion=suggestion,
            ),
            missing_fields=missing_fields,
            follow_up_questions=follow_up_questions,
        )

    def _handle_simple_interest(self, _: str, slots: dict[str, Any]) -> HandlerResult:
        required = ["principal", "annual_rate", "years"]
        missing = [field for field in required if field not in slots]
        if missing:
            return self._missing_answer(
                result="I need a little more information before I can calculate simple interest accurately.",
                explanation=[
                    "I detected a simple interest request.",
                    f"I have captured these inputs so far: {', '.join(sorted(slots.keys())) or 'none yet'}.",
                    "Simple interest needs principal, annual rate, and time period.",
                ],
                insight=["Simple interest grows linearly because interest is charged only on the original principal."],
                suggestion=["Share the principal amount, annual interest rate, and time period."],
                missing_fields=missing,
                follow_up_questions=[
                    "What is the principal amount?",
                    "What annual interest rate should I use?",
                    "What is the investment or loan duration?",
                ],
            )

        calculation = simple_interest(float(slots["principal"]), float(slots["annual_rate"]), float(slots["years"]))
        answer = StructuredAnswer(
            result=f"Simple interest is {format_currency(calculation['interest'])}, so the total amount becomes {format_currency(calculation['total_amount'])}.",
            explanation=[
                "I used the formula SI = (Principal x Rate x Time) / 100.",
                f"Principal = {format_currency(float(slots['principal']))}, rate = {format_percent(float(slots['annual_rate']))}, time = {slots['years']} years.",
                "Because this is simple interest, the interest is calculated only on the original amount.",
            ],
            insight=["Simple interest is predictable, but it grows more slowly than compounding over long durations."],
            suggestion=["If you want a stronger growth comparison, ask me to calculate the compound-interest version too."],
        )
        return HandlerResult(answer=answer, metadata=calculation)

    def _handle_compound_interest(self, _: str, slots: dict[str, Any]) -> HandlerResult:
        required = ["principal", "annual_rate", "years"]
        missing = [field for field in required if field not in slots]
        if missing:
            return self._missing_answer(
                result="I need a few more details before I can calculate compound interest.",
                explanation=[
                    "I detected a compound interest request.",
                    f"I have captured these inputs so far: {', '.join(sorted(slots.keys())) or 'none yet'}.",
                    "Compound interest needs principal, annual rate, and time period.",
                ],
                insight=["Compounding becomes more powerful as time increases because each cycle earns on past growth too."],
                suggestion=["Share the principal, annual rate, and duration. You can also mention monthly or quarterly compounding."],
                missing_fields=missing,
                follow_up_questions=[
                    "What is the principal amount?",
                    "What annual interest rate should I use?",
                    "How long is the investment or loan period?",
                ],
            )

        compounds_per_year = int(slots.get("compounds_per_year", 1))
        calculation = compound_interest(float(slots["principal"]), float(slots["annual_rate"]), float(slots["years"]), compounds_per_year)

        frequency_text = {1: "annual", 2: "half-yearly", 4: "quarterly", 12: "monthly"}.get(compounds_per_year, f"{compounds_per_year} times per year")
        answer = StructuredAnswer(
            result=f"Compound interest is {format_currency(calculation['interest'])}, so the total amount becomes {format_currency(calculation['total_amount'])}.",
            explanation=[
                "I used the formula A = P x (1 + r / n) ^ (n x t).",
                f"Principal = {format_currency(float(slots['principal']))}, rate = {format_percent(float(slots['annual_rate']))}, time = {slots['years']} years.",
                f"I used {frequency_text} compounding for this estimate.",
            ],
            insight=["Compound interest rewards longer holding periods because each cycle earns on the accumulated base."],
            suggestion=["For recurring monthly investing, compare this with an SIP projection next."],
        )
        return HandlerResult(answer=answer, metadata={**calculation, "compounds_per_year": compounds_per_year})

    def _handle_sip_projection(self, _: str, slots: dict[str, Any]) -> HandlerResult:
        required = ["monthly_investment", "annual_rate", "years"]
        missing = [field for field in required if field not in slots]
        if missing:
            return self._missing_answer(
                result="I need a bit more information before I can estimate the SIP value.",
                explanation=[
                    "I detected a SIP planning request.",
                    f"I have captured these inputs so far: {', '.join(sorted(slots.keys())) or 'none yet'}.",
                    "SIP projections depend on monthly contribution, expected annual return, and time horizon.",
                ],
                insight=["Even moderate monthly contributions can grow meaningfully when the investment horizon is long."],
                suggestion=["Share your monthly SIP amount, expected annual return, and investment duration."],
                missing_fields=missing,
                follow_up_questions=[
                    "How much will you invest every month?",
                    "What annual return assumption should I use?",
                    "What is the investment duration?",
                ],
            )

        calculation = sip_future_value(float(slots["monthly_investment"]), float(slots["annual_rate"]), float(slots["years"]))
        
        # Generate a simple growth schedule for visualization
        years = float(slots["years"])
        schedule = []
        for y in range(int(years) + 1):
            val = sip_future_value(float(slots["monthly_investment"]), float(slots["annual_rate"]), float(y))
            schedule.append({"year": y, "value": val["maturity_amount"]})
        
        answer = StructuredAnswer(
            result=f"Estimated SIP value is {format_currency(calculation['maturity_amount'])} on a total investment of {format_currency(calculation['invested_amount'])}.",
            explanation=[
                f"You invest {format_currency(float(slots['monthly_investment']))} every month for {slots['years']} years.",
                f"At an assumed annual return of {format_percent(float(slots['annual_rate']))}, estimated gains are {format_currency(calculation['estimated_gain'])}.",
                "This estimate uses monthly compounding with end-of-month contributions.",
            ],
            insight=["Time horizon is usually the strongest growth lever in SIP investing because compounding keeps stacking on earlier returns."],
            suggestion=["If you want a safer comparison, ask me to compare this SIP with FD or RD over the same horizon."],
        )
        return HandlerResult(answer=answer, metadata={**calculation, "schedule": schedule})

    def _handle_loan_eligibility(self, _: str, slots: dict[str, Any]) -> HandlerResult:
        required = ["monthly_income", "credit_score", "loan_amount", "loan_term_years", "monthly_debt_payments"]
        missing = [field for field in required if field not in slots]
        if missing:
            return self._missing_answer(
                result="I need a few more details before I can make a transparent loan assessment.",
                explanation=[
                    "I detected a loan eligibility request.",
                    f"I have captured these inputs so far: {', '.join(sorted(slots.keys())) or 'none yet'}.",
                    "A meaningful loan assessment depends on income, credit score, loan size, term, and current debt burden.",
                ],
                insight=["In most lending decisions, debt burden and credit history matter more than any single factor alone."],
                suggestion=["Share your monthly income, credit score, loan amount, loan term, and existing monthly EMI or debt payment."],
                missing_fields=missing,
                follow_up_questions=[
                    "What is your monthly income?",
                    "What is your credit score?",
                    "What loan amount are you applying for?",
                    "What is the loan term?",
                    "How much do you already pay monthly toward EMIs or debt?",
                ],
            )

        assessment = self.loan_model_service.predict(slots)
        explanation = assessment.get("top_positive", []) + assessment.get("top_negative", [])
        if assessment.get("prediction_source") == "ml_model":
            explanation.append("Prediction came from models/model.pkl, while the explanation stays transparent using the rule-based loan engine.")
        else:
            explanation.append("No trained model was found, so the result comes from the transparent fallback approval engine.")

        if assessment.get("projected_emi") is not None and assessment.get("total_obligation_ratio") is not None:
            explanation.append(
                f"Estimated EMI is {format_currency(float(assessment['projected_emi']))}, and total debt burden is about {assessment['total_obligation_ratio']:.2f}% of monthly income."
            )
        else:
            explanation.append("No interest rate was provided, so this assessment focuses on income, loan size, and existing debt instead of exact EMI.")

        top_negative = assessment.get("top_negative") or ["Maintain low debt burden and a strong repayment record."]
        improvement_tip = top_negative[0]
        answer = StructuredAnswer(
            result=f"Loan assessment: {assessment['prediction']} with an estimated approval probability of {assessment['approval_probability']:.1f}%.",
            explanation=explanation[:4],
            insight=assessment.get("global_insights", [])[:3],
            suggestion=[
                f"Best improvement area right now: {improvement_tip}",
                "If you want a stricter affordability estimate, also share the expected loan interest rate.",
            ],
        )
        return HandlerResult(answer=answer, metadata=assessment)

    def _handle_stock_guidance(self, _: str, slots: dict[str, Any]) -> HandlerResult:
        ticker = slots.get("ticker")
        if not ticker:
            return self._missing_answer(
                result="I can fetch live stock data, but I need a ticker symbol first.",
                explanation=[
                    "I detected a stock-related request.",
                    "Live market lookups need a symbol such as AAPL or RELIANCE.NS.",
                    "Without a ticker, I can only give general stock guidance.",
                ],
                insight=["Ticker-based lookups are the safest way to avoid guessing the wrong company."],
                suggestion=["Tell me the ticker symbol you want to track, for example AAPL or RELIANCE.NS."],
                missing_fields=["ticker"],
                follow_up_questions=["Which stock ticker should I look up?"] ,
            )

        try:
            snapshot = self.stock_data_service.get_stock_snapshot(str(ticker))
        except StockDataError as exc:
            answer = StructuredAnswer(
                result=f"I could not fetch live stock data for {ticker} right now.",
                explanation=[
                    str(exc),
                    "This usually means the ticker is invalid, the market feed returned no data, or the runtime has no network access.",
                    "I avoided inventing a price or trend.",
                ],
                insight=["Live stock answers are only reliable when the market data source is reachable and the symbol is valid."],
                suggestion=["Try a valid ticker like AAPL or RELIANCE.NS, or rerun once network access is available."],
            )
            return HandlerResult(answer=answer, metadata={"ticker": ticker, "error": str(exc)})

        answer = StructuredAnswer(
            result=f"Latest price for {snapshot['ticker']} is {snapshot['price']} with a {snapshot['trend']} signal.",
            explanation=[
                f"Daily move is {snapshot['daily_change']} ({snapshot['daily_change_pct']}%).",
                f"Recent risk level looks {snapshot['risk_level']} based on short-window price spread.",
                f"Data source timestamp: {snapshot['as_of']}.",
            ],
            insight=[
                "Short-term price signals are useful context, but long-term decisions still depend on business quality and valuation.",
                "A higher-volatility stock usually needs a longer holding horizon and stronger risk control.",
            ],
            suggestion=[
                "If you want, I can now compare this stock risk with SIP or FD-style alternatives.",
                "The next upgrade here is charting and richer indicators such as moving averages or RSI.",
            ],
        )
        return HandlerResult(answer=answer, metadata=snapshot)

    def _handle_bank_plan_comparison(self, message: str, slots: dict[str, Any]) -> HandlerResult:
        product_type = slots.get("product_type")
        bank = slots.get("bank")
        years = float(slots.get("years", 3))

        wants_rate = any(k in message.lower() for k in ("rate", "interest", "roi", "yield"))
        if (wants_rate or bank) and (product_type in {"FD", "RD", "SAVINGS"} or product_type is None):
            matches = self.bank_product_service.find_rates(
                product=str(product_type) if product_type else None,
                bank=str(bank) if bank else None,
                tenure_years=years if years else None,
            )
            if bank and product_type and matches:
                top = matches[0]
                answer = StructuredAnswer(
                    result=f"{top.bank} {top.product} rate (dataset): {top.rate_annual_pct:.2f}% p.a. for {years:g} years.",
                    explanation=[
                        "This is read from the local bank dataset bundled with the project (not a live feed).",
                        f"Matched rule: bank={top.bank}, product={top.product}, tenure {top.tenure_years_min:g}–{top.tenure_years_max:g} years.",
                        f"Compounding: {top.compounding or 'not specified'}.",
                    ],
                    insight=[
                        "FD/RD rates can vary by tenure bucket and customer category (senior citizen, etc.).",
                        "For explainability, using a local dataset makes the response reproducible and auditable.",
                    ],
                    suggestion=[
                        "If you want, tell me if you are a senior citizen and the exact tenure in months for a closer match.",
                        "You can update the dataset at data/banks/bank_products.json to reflect your bank’s official table.",
                    ],
                )
                return HandlerResult(answer=answer, metadata={"bank_rates": [top.__dict__]})

            if product_type and not bank:
                best = self.bank_product_service.best_rate(product=str(product_type), tenure_years=years)
                if best:
                    answer = StructuredAnswer(
                        result=f"Best {best.product} rate in the local dataset: {best.rate_annual_pct:.2f}% p.a. ({best.bank}) for {years:g} years.",
                        explanation=[
                            "This is from the local dataset bundled with the project (not live rates).",
                            f"Tenure match: {best.tenure_years_min:g}–{best.tenure_years_max:g} years.",
                            f"Compounding: {best.compounding or 'not specified'}.",
                        ],
                        insight=["Dataset-driven answers are stable and explainable, but you must keep the file updated."],
                        suggestion=[
                            "Tell me the bank name if you want a bank-specific rate lookup.",
                            "If you share your lump sum or monthly amount, I can also compute maturity value.",
                        ],
                    )
                    return HandlerResult(answer=answer, metadata={"bank_rates": [best.__dict__]})

        risk_appetite = slots.get("risk_appetite", "medium")
        monthly_amount = slots.get("monthly_amount")
        lump_sum = slots.get("lump_sum")

        scores = {"FD": 0, "RD": 0, "SIP": 0}
        if risk_appetite == "low":
            scores["FD"] += 3
            scores["RD"] += 2
            scores["SIP"] -= 1
        elif risk_appetite == "medium":
            scores["FD"] += 1
            scores["RD"] += 2
            scores["SIP"] += 2
        else:
            scores["FD"] -= 1
            scores["RD"] += 1
            scores["SIP"] += 3

        if years >= 5:
            scores["SIP"] += 2
        elif years <= 2:
            scores["FD"] += 2
            scores["RD"] += 1

        if monthly_amount is not None:
            scores["RD"] += 1
            scores["SIP"] += 2
        if lump_sum is not None:
            scores["FD"] += 2

        recommendation = max(scores, key=scores.get)
        suggestion = [
            f"If your priority is {'growth' if recommendation == 'SIP' else 'stability'}, {recommendation} is the stronger first choice.",
            "A split strategy can also work well: keep emergency money in FD or RD and use SIP for long-term growth.",
        ]

        if lump_sum is not None and "annual_rate" in slots:
            fd_preview = fd_maturity(float(lump_sum), float(slots["annual_rate"]), years)
            suggestion.append(f"With a lump sum of {format_currency(float(lump_sum))} at {format_percent(float(slots['annual_rate']))}, an FD-style maturity estimate is {format_currency(fd_preview['total_amount'])}.")
        elif monthly_amount is not None and "annual_rate" in slots:
            rd_preview = rd_maturity(float(monthly_amount), float(slots["annual_rate"]), years)
            suggestion.append(f"With monthly savings of {format_currency(float(monthly_amount))}, a recurring monthly plan at {format_percent(float(slots['annual_rate']))} grows to about {format_currency(rd_preview['maturity_amount'])}.")

        answer = StructuredAnswer(
            result=f"For a {years:g}-year horizon and {risk_appetite} risk appetite, {recommendation} is the best fit among FD, RD, and SIP.",
            explanation=[
                f"Your profile currently looks most aligned with {recommendation}.",
                "FD offers fixed returns and low risk, which makes it strong for capital protection.",
                "RD suits disciplined monthly saving with lower risk and predictable growth.",
                "SIP is market-linked, so it usually fits longer horizons and higher return goals.",
            ],
            insight=[
                "Safer products protect capital but usually cap upside, while SIPs exchange certainty for growth potential.",
                "Time horizon matters: longer horizons generally improve the case for market-linked investing.",
            ],
            suggestion=suggestion[:3],
        )
        return HandlerResult(answer=answer, metadata={"scores": scores})

    def _handle_education(self, message: str, _: dict[str, Any]) -> HandlerResult:
        lowered = message.lower()
        if any(term in lowered for term in ("stock", "stocks", "share", "shares", "equity")):
            answer = StructuredAnswer(
                result="A stock (share/equity) is a unit of ownership in a company.",
                explanation=[
                    "When you buy a stock, you become a shareholder and participate in the company’s upside and downside.",
                    "Returns can come from price appreciation and, sometimes, dividends.",
                    "Key risks include business performance risk and market volatility (prices can move quickly).",
                ],
                insight=["A stock price is not the same thing as a company’s value; valuation depends on profits, growth, and expectations."],
                suggestion=[
                    "If you name a ticker (e.g., AAPL), I can fetch a live snapshot and show a price chart.",
                    "If you tell me your time horizon and risk appetite, I can explain whether stocks fit your profile.",
                ],
            )
            return HandlerResult(answer=answer)

        if "bond" in lowered or "debenture" in lowered:
            answer = StructuredAnswer(
                result="A bond is a loan you give to an issuer (company or government) in exchange for interest payments and principal repayment.",
                explanation=[
                    "Bonds typically have a fixed maturity date and an interest rate (coupon).",
                    "Prices can still move because interest rates and credit risk change over time.",
                    "Safer issuers usually pay lower yields; riskier issuers pay higher yields.",
                ],
                insight=["Bond returns are sensitive to interest-rate changes: when rates rise, existing bond prices often fall (and vice versa)."],
                suggestion=["If you share your time horizon and risk tolerance, I can compare bonds vs FD/RD/SIP in plain terms."],
            )
            return HandlerResult(answer=answer)

        if "mutual fund" in lowered or "etf" in lowered:
            answer = StructuredAnswer(
                result="A mutual fund/ETF pools money from many investors to buy a basket of assets (stocks/bonds/etc.).",
                explanation=[
                    "A mutual fund is usually bought/sold at end-of-day NAV; an ETF trades on an exchange like a stock.",
                    "They can provide diversification by holding many instruments at once.",
                    "Returns are market-linked, so they are not guaranteed.",
                ],
                insight=["Diversification reduces single-company risk, but it cannot remove overall market risk."],
                suggestion=["Tell me your monthly amount and years, and I can project a SIP-style scenario (with transparent assumptions)."],
            )
            return HandlerResult(answer=answer)

        if "inflation" in lowered:
            answer = StructuredAnswer(
                result="Inflation is the general rise in prices over time, which reduces the purchasing power of money.",
                explanation=[
                    "If inflation is 6% and your savings earn 5%, your real (inflation-adjusted) return is roughly negative.",
                    "That is why long-term goals often need growth assets (with higher volatility) to beat inflation.",
                    "Safe instruments help protect capital, but may not always beat inflation.",
                ],
                insight=["Always compare returns against inflation to understand your real wealth change."],
                suggestion=["If you share your goal amount and timeline, I can suggest a mix of FD/RD/SIP scenarios with assumptions."],
            )
            return HandlerResult(answer=answer)

        if any(w in lowered for w in ("compound interest", "compounding", "compund", "compound intrest")):
            answer = StructuredAnswer(
                result="Compound interest means you earn returns on both the original principal and the interest already added earlier.",
                explanation=[
                    "In simple interest, growth happens only on the original amount.",
                    "In compound interest, every compounding cycle adds interest to the base for the next cycle.",
                    "That is why compounding becomes much more powerful over longer periods.",
                ],
                insight=["Time is the biggest multiplier in compounding because growth starts building on itself."],
                suggestion=["If you want, I can calculate a compound-interest example with your own numbers."],
            )
            return HandlerResult(answer=answer)

        if "sip" in lowered:
            answer = StructuredAnswer(
                result="A SIP is a fixed amount invested regularly, usually every month, into a mutual fund or similar market-linked product.",
                explanation=[
                    "It spreads investing over time instead of relying on one big entry point.",
                    "Regular investing builds discipline and helps average market entry prices.",
                    "Returns are not guaranteed because SIPs depend on market performance.",
                ],
                insight=["SIPs are often preferred for long-term wealth creation because regular contributions combine well with compounding."],
                suggestion=["Share your monthly amount, duration, and expected return if you want a projection."],
            )
            return HandlerResult(answer=answer)

        dynamic_edu = self.ai_provider.get_financial_education(message)
        if dynamic_edu:
            answer = StructuredAnswer(
                result="Here is some insight concerning your query.",
                explanation=dynamic_edu.explanation,
                insight=["This information was evaluated dynamically by the robust AI reasoning engine."],
                suggestion=[dynamic_edu.suggestion],
            )
            return HandlerResult(answer=answer)

        answer = StructuredAnswer(
            result="I can explain loans, SI, CI, SIPs, stocks, and bank plans in a transparent and calculation-friendly way.",
            explanation=[
                "This assistant is designed to keep the reasoning visible instead of giving opaque answers.",
                "For calculations, I use explicit formulas and step-by-step logic.",
                "For loan decisions, I use a transparent scoring approach so the main approval drivers stay visible.",
            ],
            insight=["Explainability increases trust because users can see which factors shaped the result."],
            suggestion=["Ask me a specific finance question or share a scenario with numbers."],
        )
        return HandlerResult(answer=answer)

    def _handle_general_finance(self, _: str, __: dict[str, Any]) -> HandlerResult:
        answer = StructuredAnswer(
            result="I can help across the main finance topics: loans, interest, investing, stocks, and bank products.",
            explanation=[
                "Loan support covers eligibility, EMI burden, credit score context, and explainable approval factors.",
                "Interest support covers simple interest, compound interest, SIP projections, FD maturity, and RD maturity.",
                "Investing support covers stocks, mutual funds, ETFs, inflation, and basic risk-versus-return guidance.",
                "Bank-plan support compares FD, RD, and SIP-style choices using time horizon and risk appetite.",
            ],
            insight=[
                "Finance becomes easier to understand when you split it into borrowing, saving, investing, and market risk.",
                "I can give either a quick definition or a number-based calculation depending on what you ask.",
            ],
            suggestion=[
                "Try: explain compound interest, calculate simple interest on 50000 at 9 percent for 3 years, or what is a stock.",
                "You can also ask for loan eligibility, SIP projection, FD vs RD, or a live stock lookup.",
            ],
        )
        return HandlerResult(
            answer=answer,
            follow_up_questions=["What would you like help with: loans, interest, investing, stocks, inflation, or bank plans?"],
        )
