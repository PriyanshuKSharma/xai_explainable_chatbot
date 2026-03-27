from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from financial_xai.history import utc_now_iso, write_json


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_BACKEND_URL = os.getenv("FINANCIAL_XAI_BACKEND_URL", "http://127.0.0.1:5000/chat")
CHAT_HISTORY_DIR = Path(os.getenv("FINANCIAL_XAI_CHAT_HISTORY_DIR", str(BASE_DIR / "data" / "chat_history")))


def export_cli_history(
    backend_url: str,
    conversation: dict[str, Any] | None,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "saved_at": utc_now_iso(),
        "backend_url": backend_url,
        "conversation": conversation,
        "messages": messages,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Quick CLI chat client to verify the backend + save history.")
    parser.add_argument("--backend", default=DEFAULT_BACKEND_URL, help="Backend chat endpoint URL.")
    parser.add_argument(
        "--out",
        default="",
        help="Optional output path for the saved chat history JSON.",
    )
    args = parser.parse_args()

    backend_url: str = args.backend
    out_path = Path(args.out) if args.out else CHAT_HISTORY_DIR / f"cli_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    conversation: dict[str, Any] | None = None
    messages: list[dict[str, Any]] = []

    print("Financial XAI CLI chat")
    print("- Type your message and press Enter")
    print("- Commands: /save, /reset, /exit")
    print(f"- Backend: {backend_url}")

    while True:
        try:
            user_message = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_message:
            continue

        command = user_message.lower()
        if command in {"/exit", "/quit"}:
            break
        if command == "/reset":
            conversation = None
            messages = []
            print("Conversation reset.")
            continue
        if command == "/save":
            write_json(out_path, export_cli_history(backend_url, conversation, messages))
            print(f"Saved: {out_path}")
            continue

        messages.append({"role": "user", "content": user_message})

        try:
            response = requests.post(
                backend_url,
                json={"message": user_message, "conversation": conversation},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            print(f"Request failed: {exc}")
            messages.append({"role": "assistant", "content": f"Request failed: {exc}"})
            continue

        conversation = payload.get("conversation")
        messages.append({"role": "assistant", "payload": payload})

        reply = payload.get("reply_markdown")
        if isinstance(reply, str) and reply.strip():
            print(f"\nAssistant>\n{reply}")
        else:
            print("\nAssistant>")
            print(json.dumps(payload, ensure_ascii=False, indent=2))

    write_json(out_path, export_cli_history(backend_url, conversation, messages))
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
