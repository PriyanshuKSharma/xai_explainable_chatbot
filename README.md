# Financial Explainable AI Chatbot

A production-style finance project with this runtime flow:

```text
Streamlit Chat UI -> Flask API -> ML/Finance/Stock Services -> Explainable Response
```

The backend now supports:

- Loan eligibility with a real `models/model.pkl` when available
- Transparent fallback loan scoring when the model file is missing
- Simple interest, compound interest, SIP, FD, and RD calculations
- Live stock lookup via `yfinance`
- Structured explainable responses for chat consumption

## Architecture

```text
ui.py                     Streamlit frontend
app.py                    Flask API entrypoint
financial_xai/engine.py   Chat orchestration and response shaping
financial_xai/modeling.py Model loading and fallback loan prediction
financial_xai/stock_service.py Live stock market lookup
financial_xai/calculations.py Finance calculations
models/model.pkl          Optional trained loan model
```

## Install

```bash
pip install -r requirements.txt
```

## Run

Terminal 1:

```bash
python app.py
```

Terminal 2:

```bash
streamlit run ui.py
```

Backend URL:

```text
http://127.0.0.1:5000/chat
```

## Streamlit Cloud deploy note

If you deploy only the Streamlit app (without deploying Flask), `FINANCIAL_XAI_BACKEND_URL=http://127.0.0.1:5000/chat` will fail on Streamlit Cloud.

Options:
- Run in-process (recommended on Streamlit Cloud): set `FINANCIAL_XAI_BACKEND_MODE=local` in Streamlit secrets.
- Or deploy `app.py` separately (Render/Fly/Railway/etc.) and set `FINANCIAL_XAI_BACKEND_URL` to that public URL in Streamlit secrets.

## Model file

Place your trained model at:

```text
models/model.pkl
```

### Training your own model

This repo includes a training script that writes a compatible `models/model.pkl`:

```bash
./.venv/bin/python scripts/train_loan_model.py --data loan_data.csv --out models/model.pkl
```

By default it trains a `LogisticRegression` model and saves a *bundle* that includes the model plus `feature_order`.

### Feature order

If your `models/model.pkl` is a raw sklearn estimator, the backend uses this default feature order:

1. `monthly_income`
2. `credit_score`
3. `monthly_debt_payments`
4. `loan_amount`
5. `loan_term_years`
6. `annual_rate`
7. `employment_years`

If your `models/model.pkl` is a bundle created by `scripts/train_loan_model.py`, the backend uses the bundle’s `feature_order` automatically (so it can train on a smaller schema like `Income/CreditScore/LoanAmount` too).

If `model.pkl` is missing, the backend still runs by falling back to the transparent rule-based loan engine.

## Example prompts

- `My income is 85000, credit score is 742, loan amount is 1200000, term is 5 years, existing EMI is 12000`
- `Calculate compound interest on 150000 at 10% for 5 years compounded quarterly`
- `I invest 5000 monthly in SIP for 10 years at 12%`
- `Show me the stock price for AAPL`
- `Show me the stock price for RELIANCE.NS`
- `FD or SIP is better for a low risk investor with a 3 year horizon?`

## API endpoints

- `GET /health`
- `GET /prompt`
- `POST /chat`
- `POST /api/chat`

Example request:

```json
{
  "message": "Show me the stock price for AAPL",
  "conversation": null
}
```

## Tests

```bash
python -m pytest
```

## Docker

You can run the entire application using Docker.

### 1. Build the image

```bash
docker build -t xai-chatbot .
```

### 2. Run the container

```bash
# Set HOST=0.0.0.0 so the Flask API is accessible from the host
docker run -p 8501:8501 -p 5000:5000 -e HOST=0.0.0.0 --env-file .env xai-chatbot
```

### Using Docker Compose

For a smoother experience, use Docker Compose:

```bash
docker-compose up --build
```

The application will be available at:

- **Frontend (Streamlit):** `http://localhost:8501`
- **Backend (API):** `http://localhost:5000`

## Next upgrades

- Add LIME visualizations for model-backed loan predictions
- Add stock and SIP charts inside Streamlit
- Add Docker and deployment manifests
- Add OpenAI-powered reasoning on top of the structured backend
