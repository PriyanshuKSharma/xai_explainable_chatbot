from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import urljoin, urlparse

from financial_xai.engine import FinancialAssistantEngine
from financial_xai.schemas import ChatRequest
from financial_xai.stock_service import StockDataService, StockDataError

from financial_xai.history import read_json, utc_now_iso, write_json

BACKEND_URL = os.getenv("FINANCIAL_XAI_BACKEND_URL", "http://127.0.0.1:5000/chat")
BACKEND_MODE = os.getenv("FINANCIAL_XAI_BACKEND_MODE", "").strip().lower()  # "remote" | "local" | ""
BASE_DIR = Path(__file__).resolve().parent
CHAT_HISTORY_DIR = Path(os.getenv("FINANCIAL_XAI_CHAT_HISTORY_DIR", str(BASE_DIR / "data" / "chat_history")))
LATEST_HISTORY_PATH = CHAT_HISTORY_DIR / "streamlit_latest.json"
CHAT_HISTORY_AUTOSAVE = os.getenv("FINANCIAL_XAI_CHAT_HISTORY_AUTOSAVE", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Streamlit renamed experimental_rerun to rerun; support both
if hasattr(st, "rerun"):
    RERUN = st.rerun
else:
    RERUN = st.experimental_rerun
EXAMPLE_PROMPTS = [
    "My income is 85000, credit score is 742, loan amount is 1200000, term is 5 years, existing EMI is 12000",
    "Calculate compound interest on 150000 at 10% for 5 years compounded quarterly",
    "I invest 5000 monthly in SIP for 10 years at 12%",
    "Show me the stock price for AAPL",
    "FD or SIP is better for a low risk investor with a 3 year horizon?",
]


st.set_page_config(page_title="Financial Explainable AI Chatbot", page_icon=":moneybag:", layout="wide")

ENGINE = FinancialAssistantEngine()
STOCKS = StockDataService()


loaded_history: dict[str, Any] | None = None
if CHAT_HISTORY_AUTOSAVE:
    loaded_history = read_json(LATEST_HISTORY_PATH)

if "messages" not in st.session_state:
    messages = loaded_history.get("messages") if loaded_history else []
    st.session_state.messages = messages if isinstance(messages, list) else []
if "conversation" not in st.session_state:
    st.session_state.conversation = loaded_history.get("conversation") if loaded_history else None
if "draft" not in st.session_state:
    st.session_state.draft = ""
if "view" not in st.session_state:
    # landing | chat
    st.session_state.view = "landing"


def show_landing() -> None:
    """Minimal landing page before entering chat."""
    st.title("Financial Explainable AI Chatbot")
    st.caption("Transparent finance answers with visible reasoning and math.")

    col_left, col_right = st.columns([1.15, 1])
    with col_left:
        st.subheader("Why it's different")
        st.markdown(
            "- Loan eligibility with explainable drivers (works even without model.pkl)\n"
            "- SI/CI calculators, SIP growth, FD/RD comparisons\n"
            "- Live stock snapshots via yfinance\n"
            "- Structured replies: result → explanation → insight → suggestion"
        )
        if st.button("Open Chat", type="primary", use_container_width=True):
            st.session_state.view = "chat"
            RERUN()

    with col_right:
        st.subheader("Try a prompt")
        examples = [
            "Calculate compound interest on 150000 at 10% for 5 years compounded quarterly",
            "My income is 85000, credit score is 742, loan amount is 1200000, term is 5 years, existing EMI is 12000",
            "Show me the stock price for AAPL",
            "FD or SIP is better for a low risk investor with a 3 year horizon?",
        ]
        for ex in examples:
            if st.button(ex, use_container_width=True):
                st.session_state.draft = ex
                st.session_state.view = "chat"
                RERUN()

    st.divider()
    st.subheader("API endpoints")
    st.code(
        """GET /health\nGET /prompt\nPOST /chat\nPOST /api/chat\nBackend: http://127.0.0.1:5000/chat\nFrontend: streamlit run ui.py""",
        language="" if False else None,
    )


# If user wants landing, render it and stop before chat UI mounts
if st.session_state.view == "landing":
    show_landing()
    st.stop()

st.title("Financial Explainable AI Chatbot")
st.caption("Flask backend plus Streamlit frontend with finance calculators, loan intelligence, and live market hooks.")


def set_prompt(prompt: str) -> None:
    st.session_state.draft = prompt


def export_chat_history() -> dict[str, Any]:
    return {
        "saved_at": utc_now_iso(),
        "backend_url": BACKEND_URL,
        "conversation": st.session_state.conversation,
        "messages": st.session_state.messages,
    }


def autosave_chat_history() -> None:
    if not CHAT_HISTORY_AUTOSAVE:
        return
    try:
        write_json(LATEST_HISTORY_PATH, export_chat_history())
    except OSError:
        # Never break the chat UI because the filesystem is not writable.
        return


def render_bot_payload(payload: dict[str, Any]) -> None:
    parsed_backend = urlparse(BACKEND_URL)
    backend_base = f"{parsed_backend.scheme}://{parsed_backend.netloc}/" if parsed_backend.scheme else ""

    # Check for new format
    formatted = payload.get("formatted")
    if formatted:
        st.markdown(f"### {formatted['type'].upper()} Result")
        st.write(formatted["result"])

        st.markdown("**Explanation**")
        for item in formatted["explanation"]:
            st.write(f"- {item}")

        viz = formatted.get("visualization")
        if viz:
            st.markdown(f"**Visualization ({viz['type']})**")
            if viz["type"] == "lime":
                data = viz["data"]
                if isinstance(data, dict):
                    prob = data.get("probability", 0)
                    st.metric("Approval Probability", f"{prob}%")
                    impacts = data.get("impacts", [])
                    if impacts:
                        st.info("\n".join([f"• {i}" for i in impacts]))
            elif viz["type"] == "chart":
                data = viz["data"]
                if isinstance(data, dict) and "schedule" in data:
                    import pandas as pd
                    df = pd.DataFrame(data["schedule"])
                    st.line_chart(df.set_index("year"))
            elif viz["type"] == "stock":
                data = viz.get("data") or {}
                if isinstance(data, dict) and data.get("chart_url"):
                    chart_url = urljoin(backend_base, str(data["chart_url"]))
                    try:
                        svg_resp = requests.get(chart_url, timeout=10)
                        svg_resp.raise_for_status()
                        components.html(svg_resp.text, height=300, scrolling=False)
                    except requests.RequestException as exc:
                        st.warning(f"Failed to load stock chart: {exc}")
                        st.json(data)
                elif isinstance(data, dict) and data.get("ticker"):
                    # Local-mode fallback: render chart directly without relying on Flask endpoints.
                    try:
                        svg = STOCKS.build_price_chart_svg(str(data["ticker"]), period="1mo", interval="1d")
                        components.html(svg, height=300, scrolling=False)
                    except (StockDataError, Exception) as exc:
                        st.json(data)
                else:
                    st.json(data)

        if formatted.get("suggestion"):
            st.markdown("**Suggestion**")
            st.write(formatted["suggestion"])
    else:
        # Fallback to old format
        answer = payload.get("answer", {})
        st.markdown("**Result**")
        st.write(answer.get("result", payload.get("reply_markdown", "No result returned.")))

        explanation = answer.get("explanation") or []
        if explanation:
            st.markdown("**Explanation**")
            for item in explanation:
                st.write(f"- {item}")

        insight = answer.get("insight") or []
        if insight:
            st.markdown("**Insight**")
            for item in insight:
                st.write(f"- {item}")

        suggestion = answer.get("suggestion") or []
        if suggestion:
            st.markdown("**Suggestion**")
            for item in suggestion:
                st.write(f"- {item}")

    follow_ups = payload.get("follow_up_questions") or []
    if follow_ups:
        st.markdown("**Follow-up Questions**")
        for item in follow_ups:
            st.write(f"- {item}")

    metadata = payload.get("metadata") or {}
    if metadata:
        with st.expander("Backend details"):
            st.json(metadata)


def call_backend_or_local(user_input: str) -> dict[str, Any]:
    """
    Streamlit Cloud cannot reach a Flask backend on 127.0.0.1.
    - If FINANCIAL_XAI_BACKEND_MODE=local: always run in-process.
    - Otherwise: try BACKEND_URL; on failure fall back to in-process engine.
    """
    mode = BACKEND_MODE
    if mode == "local":
        resp = ENGINE.respond(ChatRequest(message=user_input, conversation=st.session_state.conversation))
        return resp.model_dump(mode="json")

    try:
        parsed = urlparse(BACKEND_URL)
        if parsed.hostname in {"127.0.0.1", "localhost"}:
            raise requests.RequestException("BACKEND_URL points to localhost; using in-process engine instead.")
        response = requests.post(
            BACKEND_URL,
            json={"message": user_input, "conversation": st.session_state.conversation},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        resp = ENGINE.respond(ChatRequest(message=user_input, conversation=st.session_state.conversation))
        return resp.model_dump(mode="json")


with st.sidebar:
    if st.button("← Home", use_container_width=True):
        st.session_state.view = "landing"
        RERUN()

    st.subheader("Backend")
    st.code(BACKEND_URL)
    st.subheader("History")
    st.caption(f"Autosave: {'on' if CHAT_HISTORY_AUTOSAVE else 'off'}")

    if st.button("Save snapshot", use_container_width=True):
        snapshot_path = CHAT_HISTORY_DIR / f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            write_json(snapshot_path, export_chat_history())
            st.success(f"Saved to {snapshot_path}")
        except OSError as exc:
            st.error(f"Failed to save history: {exc}")

    st.download_button(
        "Download JSON",
        data=json.dumps(export_chat_history(), ensure_ascii=False, indent=2),
        file_name="financial_xai_chat_history.json",
        mime="application/json",
        use_container_width=True,
    )

    st.subheader("Examples")
    for prompt in EXAMPLE_PROMPTS:
        st.button(prompt, use_container_width=True, on_click=set_prompt, args=(prompt,))
    if st.button("Reset conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation = None
        st.session_state.draft = ""
        autosave_chat_history()
        st.rerun()

if st.button("← Home", key="home-main"):
    st.session_state.view = "landing"
    RERUN()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_bot_payload(message["payload"])
        else:
            st.write(message["content"])

user_input = st.chat_input("Ask about loans, SI, CI, SIP, stocks, FD, or RD...")
if st.session_state.draft and not user_input:
    user_input = st.session_state.draft
    st.session_state.draft = ""

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    payload = call_backend_or_local(user_input)
    st.session_state.conversation = payload.get("conversation")

    st.session_state.messages.append({"role": "assistant", "payload": payload})
    autosave_chat_history()
    with st.chat_message("assistant"):
        render_bot_payload(payload)
