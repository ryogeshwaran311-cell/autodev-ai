from __future__ import annotations
import json
from google import genai
from google.genai import types
from app.config import get_settings

class GeminiService:
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        if not self.settings.mock_ai and self.settings.gemini_api_key:
            self.client = genai.Client(api_key=self.settings.gemini_api_key)

    async def json(self, system: str, prompt: str, fallback: dict) -> dict:
        if self.settings.mock_ai or not self.client:
            return fallback

        response = await self.client.aio.models.generate_content(
            model=self.settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=24000,
            ),
        )
        try:
            return json.loads(response.text or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Gemini returned invalid JSON: {exc}") from exc
