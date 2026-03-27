from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request

from financial_xai.engine import FinancialAssistantEngine
from financial_xai.prompting import load_master_prompt
from financial_xai.schemas import ChatRequest


BASE_DIR = Path(__file__).resolve().parent
engine = FinancialAssistantEngine()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    @app.get("/")
    def home() -> tuple[dict[str, object], int]:
        return (
            {
                "name": "Financial Explainable AI Chatbot",
                "ui": "Run streamlit run ui.py",
                "endpoints": ["GET /health", "GET /prompt", "POST /chat", "POST /api/chat"],
            },
            200,
        )

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    @app.get("/prompt")
    def prompt() -> tuple[dict[str, str], int]:
        return {"master_prompt": load_master_prompt()}, 200

    @app.post("/chat")
    @app.post("/api/chat")
    def chat() -> tuple[object, int]:
        payload = request.get_json(silent=True) or {}
        message = str(payload.get("message", "")).strip()
        if not message:
            return jsonify({"error": "message is required"}), 400

        chat_request = ChatRequest(
            message=message,
            conversation=payload.get("conversation"),
        )
        response = engine.respond(chat_request)
        return jsonify(response.model_dump()), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
