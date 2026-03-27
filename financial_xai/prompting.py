from __future__ import annotations

from pathlib import Path


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "master_prompt.md"


def load_master_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")
