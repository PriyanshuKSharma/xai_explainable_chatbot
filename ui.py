from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


BACKEND_URL = os.getenv("FINANCIAL_XAI_BACKEND_URL", "http://127.0.0.1:5000/chat")
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

if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation" not in st.session_state:
    st.session_state.conversation = None
if "draft" not in st.session_state:
    st.session_state.draft = ""


def set_prompt(prompt: str) -> None:
    st.session_state.draft = prompt


def render_bot_payload(payload: dict[str, Any]) -> None:
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
    st.subheader("Examples")
    for prompt in EXAMPLE_PROMPTS:
        st.button(prompt, use_container_width=True, on_click=set_prompt, args=(prompt,))
    if st.button("Reset conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation = None
        st.session_state.draft = ""
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
    with st.chat_message("assistant"):
        render_bot_payload(payload)
