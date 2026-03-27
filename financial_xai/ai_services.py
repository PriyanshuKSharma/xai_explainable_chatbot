from __future__ import annotations

import os
import json
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class AIContent(BaseModel):
    explanation: list[str]
    suggestion: str


class BaseAIService(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def generate_enhanced_content(
        self,
        intent: str,
        slots: dict[str, Any],
        metadata: dict[str, Any],
        base_result: str
    ) -> AIContent | None:
        pass


class GeminiService(BaseAIService):
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._model = None
        if self.api_key:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel("gemini-1.5-flash")

    def is_available(self) -> bool:
        return self._model is not None

    def generate_enhanced_content(
        self,
        intent: str,
        slots: dict[str, Any],
        metadata: dict[str, Any],
        base_result: str
    ) -> AIContent | None:
        if not self.is_available():
            return None

        prompt = self._build_prompt(intent, slots, metadata, base_result)
        try:
            import google.generativeai as genai
            response = self._model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(response.text)
            return AIContent(**data)
        except Exception as e:
            return None

    def _build_prompt(self, intent: str, slots: dict[str, Any], metadata: dict[str, Any], base_result: str) -> str:
        return f"""
        You are a Financial Explainable AI Assistant. 
        Intent: {intent}
        Data: {slots}
        Calculation: {metadata}
        Result: {base_result}

        Based on this, provide:
        1. 2-3 simple reasons explaining the result.
        2. A practical financial suggestion.

        Output JSON:
        {{
          "explanation": ["reason 1", "reason 2"],
          "suggestion": "string"
        }}
        """


class GroqService(BaseAIService):
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self._client = None
        if self.api_key and not self.api_key.startswith("your_"):
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except Exception as e:
                print(f"DEBUG: Groq Init Error: {e}")
        elif not self.api_key:
            print("DEBUG: Groq API Key is MISSING (os.getenv returned None)")
        else:
            print(f"DEBUG: Groq API Key is PLACEHOLDER: {self.api_key}")

    def is_available(self) -> bool:
        return self._client is not None

    def generate_enhanced_content(
        self,
        intent: str,
        slots: dict[str, Any],
        metadata: dict[str, Any],
        base_result: str
    ) -> AIContent | None:
        if not self.is_available():
            return None

        prompt = self._build_prompt(intent, slots, metadata, base_result)
        try:
            response = self._client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a specialized financial AI. Always output valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            return AIContent(**data)
        except Exception:
            return None

    def _build_prompt(self, intent: str, slots: dict[str, Any], metadata: dict[str, Any], base_result: str) -> str:
        return f"""
        Explain this financial result:
        Intent: {intent}
        Input: {slots}
        Stats: {metadata}
        Result: {base_result}

        Provide 2-3 explanation reasons and 1 suggestion.
        Format: {{"explanation": ["...", "..."], "suggestion": "..."}}
        """


class AIProvider:
    def __init__(self) -> None:
        self.services: list[BaseAIService] = [
            GeminiService(),
            GroqService(),
        ]

    def get_enhanced_content(
        self,
        intent: str,
        slots: dict[str, Any],
        metadata: dict[str, Any],
        base_result: str
    ) -> AIContent | None:
        for service in self.services:
            if service.is_available():
                content = service.generate_enhanced_content(intent, slots, metadata, base_result)
                if content:
                    return content
        return None
