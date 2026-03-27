# financial_xai package

This package contains the backend logic for the Financial Explainable AI Chatbot.

## How the package flows

```text
User message
  -> intent_router.py detects intent and extracts values
  -> engine.py selects the correct handler
  -> calculations.py / modeling.py / stock_service.py run the domain logic
  -> formatting.py shapes the reply
  -> schemas.py defines the request and response objects
```

## Files in this directory

### `__init__.py`
Package marker for `financial_xai`.

### `schemas.py`
Defines the main Pydantic models used across the backend.

It includes:
- `FinancialIntent` for supported intent types
- `ConversationState` for follow-up chat memory
- `ChatRequest` and `ChatResponse` for API input and output
- `StructuredAnswer` for the standard `Result / Explanation / Insight / Suggestion` format

### `intent_router.py`
Handles natural-language routing.

Its job is to:
- detect whether the user is asking about loans, SI, CI, SIP, stocks, or bank plans
- extract important values such as income, credit score, rate, years, SIP amount, and stock ticker
- continue an active conversation when the assistant is asking follow-up questions

### `engine.py`
This is the main orchestration layer of the package.

It:
- receives a parsed `ChatRequest`
- decides which feature handler to run
- asks follow-up questions when required data is missing
- calls the right service for loans, stock data, or calculations
- returns a structured explainable response

This is the core file to read first if you want to understand the chatbot behavior end to end.

### `calculations.py`
Contains pure finance calculation utilities.

It currently includes:
- simple interest
- compound interest
- SIP future value
- FD maturity
- RD maturity
- EMI calculation

This file is focused on deterministic math only.

### `loan_xai.py`
Contains the transparent fallback loan assessment logic.

It creates an explainable loan decision using factors such as:
- credit score
- loan amount versus income
- existing debt burden
- employment stability
- projected EMI when rate is available

This is used even when no trained ML model exists, so the system still works.

### `modeling.py`
Connects the chatbot to a trained loan model stored at `models/model.pkl`.

It:
- loads the model if the file exists
- builds the feature vector in the expected order
- runs model prediction
- falls back to `loan_xai.py` if the model is missing
- keeps the response explainable even when the prediction comes from ML

### `stock_service.py`
Handles live stock lookup using `yfinance`.

It returns a small stock snapshot such as:
- ticker
- latest price
- daily move
- recent trend
- rough risk level
- timestamp

### `formatting.py`
Formats output into the structured chatbot text block.

It also contains helpers for:
- currency formatting
- percentage formatting
- bullet rendering

### `prompting.py`
Loads the reusable master prompt from `prompts/master_prompt.md`.

This keeps the prompt outside the core Python logic so it can be edited independently.

## Suggested reading order

If you are new to this package, read files in this order:

1. `engine.py`
2. `schemas.py`
3. `intent_router.py`
4. `calculations.py`
5. `modeling.py`
6. `loan_xai.py`
7. `stock_service.py`
8. `formatting.py`
9. `prompting.py`

## Notes

- `engine.py` is the control center.
- `calculations.py` is the math layer.
- `modeling.py` is the ML integration layer.
- `loan_xai.py` is the explainability fallback.
- `stock_service.py` is the live market data layer.
