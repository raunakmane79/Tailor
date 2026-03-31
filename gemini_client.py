from __future__ import annotations
import json
import re
import requests
from typing import List, Dict, Any

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
                "maxOutputTokens": 4096,
            },
        }

        resp = requests.post(
            f"{GEMINI_URL}?key={self.api_key}",
            headers=headers,
            json=body,
            timeout=60,
        )

        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise RuntimeError(
                f"Gemini API request failed: {resp.status_code} - {resp.text}"
            ) from e

        data = resp.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Unexpected Gemini response: {data}") from e

    @staticmethod
    def _extract_json(text: str) -> Any:
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

        start_positions = [text.find(c) for c in ["{", "["] if text.find(c) != -1]
        if not start_positions:
            raise ValueError("No JSON object or array found in model response.")

        start = min(start_positions)
        text = text[start:]

        return json.loads(text)

    def analyze_ats(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        prompt = f"""
You are an expert ATS (Applicant Tracking System) analyst.

RESUME:
\"\"\"
{resume_text}
\"\"\"

JOB DESCRIPTION:
\"\"\"
{job_description}
\"\"\"

Analyze the resume against the job description and return ONLY a valid JSON object with this exact structure:
{{
  "ats_score": <integer 0-100 representing current keyword match percentage>,
  "score_note": "<one sentence explaining the score>",
  "present_keywords": ["keyword1", "keyword2"],
  "missing_keywords": ["keyword1", "keyword2"],
  "key_requirements": [
    "<requirement 1>",
    "<requirement 2>",
    "<requirement 3>"
  ]
}}

Rules:
- Return JSON only
- present_keywords: important skills/tools/terms from the job description already present in the resume
- missing_keywords: important skills/tools/terms from the job description absent from the resume
- key_requirements: 5-8 of the most important requirements
- Be specific about skills, tools, certifications, and action verbs
- ats_score should reflect realistic keyword overlap
"""

        raw = self._call(prompt, temperature=0.2)
        parsed = self._extract_json(raw)

        if not isinstance(parsed, dict):
            raise ValueError("ATS analysis response was not a JSON object.")

        return {
            "ats_score": parsed.get("ats_score", 0),
            "score_note": parsed.get("score_note", ""),
            "present_keywords": parsed.get("present_keywords", []),
            "missing_keywords": parsed.get("missing_keywords", []),
            "key_requirements": parsed.get("key_requirements", []),
        }

    def generate_suggestions(
        self,
        lines: List[Dict[str, Any]],
        job_description: str,
        ats_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        missing_kw = ats_analysis.get("missing_keywords", [])
        key_reqs = ats_analysis.get("key_requirements", [])

        lines_block = "\n".join(
            f"[{line['index']}] ({line['char_count']} chars) {line['text']}"
            for line in lines
            if line.get("text", "").strip()
        )

        prompt = f"""
You are a professional resume writer and ATS optimization expert.

MISSING KEYWORDS THAT SHOULD BE ADDED WHERE NATURAL:
{json.dumps(missing_kw)}

KEY JOB REQUIREMENTS:
{json.dumps(key_reqs)}

JOB DESCRIPTION:
\"\"\"
{job_description[:3000]}
\"\"\"

RESUME LINES:
{lines_block}

TASK:
Select the 8-15 most impactful resume lines to improve.
For each selected line, provide EXACTLY 3 rewrite options.

STRICT RULES:
- Preserve approximate line length
- Do not change dates
- Do not invent fake metrics, tools, results, or experience
- Keep wording professional and ATS-friendly
- Only rewrite lines that truly benefit from improvement
- Return ONLY valid JSON in this exact format:

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
        parsed = self._extract_json(raw)

        if not isinstance(parsed, list):
            raise ValueError("Suggestion response was not a JSON array.")

        cleaned: List[Dict[str, Any]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue

            line_index = item.get("line_index")
            original = item.get("original", "")
            options = item.get("options", [])
            reason = item.get("reason", "")
            keywords_added = item.get("keywords_added", [])

            if not isinstance(line_index, int):
                continue
            if not isinstance(options, list) or len(options) != 3:
                continue

            cleaned.append(
                {
                    "line_index": line_index,
                    "original": original,
                    "options": options,
                    "reason": reason,
                    "keywords_added": keywords_added,
                }
            )

        return cleaned
"""
        raw = self._call(prompt, temperature=0.5)

        try:
            data = self._extract_json(raw)
            return data if isinstance(data, list) else []
        except Exception:
            return []
