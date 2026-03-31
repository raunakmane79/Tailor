import json
import re
import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"


class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _call(self, prompt: str, temperature: float = 0.4) -> str:
        headers = {"Content-Type": "application/json"}

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048,
            },
        }

        response = requests.post(
            f"{GEMINI_URL}?key={self.api_key}",
            headers=headers,
            json=body,
            timeout=60,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Gemini API Error: {response.text}")

        data = response.json()

        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _extract_json(self, text: str):
        text = re.sub(r"```json|```", "", text).strip()

        start = min([i for i in [text.find("{"), text.find("[")] if i != -1])
        text = text[start:]

        return json.loads(text)

    def analyze_ats(self, resume_text: str, job_description: str):
        prompt = f"""
Analyze the resume against the job description.

Return ONLY JSON:

{{
  "ats_score": number,
  "score_note": "text",
  "present_keywords": [],
  "missing_keywords": [],
  "key_requirements": []
}}

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}
"""

        raw = self._call(prompt)
        return self._extract_json(raw)

    def generate_suggestions(self, lines, job_description, ats_analysis):
        prompt = f"""
Improve resume lines based on job description.

Return ONLY JSON list:

[
  {{
    "line_index": 0,
    "original": "",
    "options": ["", "", ""],
    "reason": ""
  }}
]

LINES:
{lines}

JOB DESCRIPTION:
{job_description}
"""

        raw = self._call(prompt, temperature=0.6)
        return self._extract_json(raw)
