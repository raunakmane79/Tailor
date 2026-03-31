from __future__ import annotations
import json
import re
import requests
from typing import List, Dict, Any

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _call(self, prompt: str, temperature: float = 0.4) -> str:
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 4096,
            },
        }

        response = requests.post(
            f"{GEMINI_URL}?key={self.api_key}",
            headers=headers,
            json=body,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Unexpected Gemini response: {data}") from e

    @staticmethod
    def _extract_json(text: str) -> Any:
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        start = min((text.find(c) for c in ["{", "["] if text.find(c) != -1), default=0)
        text = text[start:]
        return json.loads(text)

    def analyze_ats(self, resume_text: str, job_description: str) -> Dict:
        prompt = f"""
You are an expert ATS analyst.

RESUME:
\"\"\"
{resume_text}
\"\"\"

JOB DESCRIPTION:
\"\"\"
{job_description}
\"\"\"

Return ONLY valid JSON:
{{
  "ats_score": <integer 0-100>,
  "score_note": "<one sentence>",
  "present_keywords": ["keyword1", "keyword2"],
  "missing_keywords": ["keyword1", "keyword2"],
  "key_requirements": ["req1", "req2", "req3"]
}}
"""
        raw = self._call(prompt, temperature=0.2)
        try:
            return self._extract_json(raw)
        except Exception:
            return {
                "ats_score": 50,
                "score_note": "Could not parse analysis.",
                "present_keywords": [],
                "missing_keywords": [],
                "key_requirements": [],
            }

    def generate_suggestions(
        self,
        lines: List[Dict],
        job_description: str,
        ats_analysis: Dict,
    ) -> List[Dict]:
        missing_kw = ats_analysis.get("missing_keywords", [])
        key_reqs = ats_analysis.get("key_requirements", [])

        lines_block = "\n".join(
            f"[{l['index']}] ({l['char_count']} chars) {l['text']}"
            for l in lines
            if l["text"].strip()
        )

        prompt = f"""
You are a professional resume writer and ATS optimization expert.

MISSING KEYWORDS:
{json.dumps(missing_kw)}

KEY REQUIREMENTS:
{json.dumps(key_reqs)}

JOB DESCRIPTION:
\"\"\"
{job_description[:3000]}
\"\"\"

RESUME LINES:
{lines_block}

TASK:
Select the most impactful lines to rewrite.
For each chosen line, provide exactly 3 rewrite options.

STRICT RULES:
- Preserve approximate length
- Do not change dates
- Do not invent fake metrics
- Keep tone professional
- Return ONLY valid JSON in this format:

[
  {{
    "line_index": 12,
    "original": "original text here",
    "options": ["option 1", "option 2", "option 3"],
    "reason": "why this line should change",
    "keywords_added": ["sql", "forecasting"]
  }}
]
"""
        raw = self._call(prompt, temperature=0.5)

        try:
            data = self._extract_json(raw)
            return data if isinstance(data, list) else []
        except Exception:
            return []
