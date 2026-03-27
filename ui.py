from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import streamlit as st

from financial_xai.history import read_json, utc_now_iso, write_json

BACKEND_URL = os.getenv("FINANCIAL_XAI_BACKEND_URL", "http://127.0.0.1:5000/chat")
BASE_DIR = Path(__file__).resolve().parent
CHAT_HISTORY_DIR = Path(os.getenv("FINANCIAL_XAI_CHAT_HISTORY_DIR", str(BASE_DIR / "data" / "chat_history")))
LATEST_HISTORY_PATH = CHAT_HISTORY_DIR / "streamlit_latest.json"
CHAT_HISTORY_AUTOSAVE = os.getenv("FINANCIAL_XAI_CHAT_HISTORY_AUTOSAVE", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
EXAMPLE_PROMPTS = [
    "My income is 85000, credit score is 742, loan amount is 1200000, term is 5 years, existing EMI is 12000",
    "Calculate compound interest on 150000 at 10% for 5 years compounded quarterly",
    "I invest 5000 monthly in SIP for 10 years at 12%",
    "Show me the stock price for AAPL",
    "FD or SIP is better for a low risk investor with a 3 year horizon?",
]


st.set_page_config(page_title="Financial Explainable AI Chatbot", page_icon=":moneybag:", layout="wide")
st.title("Financial Explainable AI Chatbot")
st.caption("Flask backend plus Streamlit frontend with finance calculators, loan intelligence, and live market hooks.")

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
                st.json(viz["data"])

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


with st.sidebar:
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

    try:
        response = requests.post(
            BACKEND_URL,
            json={"message": user_input, "conversation": st.session_state.conversation},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        st.session_state.conversation = payload.get("conversation")
    except requests.RequestException as exc:
        payload = {
            "answer": {
                "result": "The backend request failed.",
                "explanation": [f"Error: {exc}"],
                "insight": ["Make sure the Flask backend is running on port 5000."],
                "suggestion": ["Start the backend with python app.py and try again."],
            },
            "metadata": {},
            "follow_up_questions": [],
        }

    st.session_state.messages.append({"role": "assistant", "payload": payload})
    autosave_chat_history()
    with st.chat_message("assistant"):
        render_bot_payload(payload)
