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
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
            },
        }

        response = requests.post(
            f"{GEMINI_URL}?key={self.api_key}",
            headers=headers,
            json=body,
            timeout=60,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Gemini API Error: {response.status_code} - {response.text}")

        data = response.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            raise RuntimeError(f"Unexpected Gemini response: {data}")

    def _extract_json(self, text: str):
        if not text or not text.strip():
            raise ValueError("Empty model response.")

        cleaned = text.strip()
        cleaned = re.sub(r"```json|```", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", cleaned)
        if not match:
            raise ValueError(f"No JSON found in model response:\n{cleaned}")

        candidate = match.group(1)

        candidate = re.sub(r",\s*([\]}])", r"\1", candidate)

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parse failed: {e}\n\nRaw response:\n{cleaned}")

    def analyze_ats(self, resume_text: str, job_description: str):
        prompt = f"""
You are an ATS analyst.

Return ONLY valid JSON.
Do not include markdown.
Do not include explanation text.

Schema:
{{
  "ats_score": 0,
  "score_note": "",
  "present_keywords": [],
  "missing_keywords": [],
  "key_requirements": []
}}

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}
"""
        raw = self._call(prompt, temperature=0.2)
        return self._extract_json(raw)

    def generate_suggestions(self, lines, job_description, ats_analysis):
        missing_keywords = ats_analysis.get("missing_keywords", [])
        key_requirements = ats_analysis.get("key_requirements", [])

        lines_block = "\n".join(
            f"[{line['index']}] ({line['char_count']} chars) {line['text']}"
            for line in lines
            if line.get("text", "").strip()
        )

        prompt = f"""
You are a resume tailoring engine.

Return ONLY a valid JSON array.
No markdown.
No comments.
No intro text.
No trailing commas.

Required output schema:
[
  {{
    "line_index": 12,
    "original": "original line text",
    "options": ["option 1", "option 2", "option 3"],
    "reason": "short reason",
    "keywords_added": ["keyword1", "keyword2"]
  }}
]

Rules:
- Select only lines that actually need improvement
- Return 5 to 12 items max
- options must always contain exactly 3 strings
- Do not invent fake experience, metrics, tools, dates, or roles
- Keep each rewrite close in length to the original
- Use only keywords that fit naturally
- line_index must match one of the provided indices

Missing keywords:
{json.dumps(missing_keywords)}

Key requirements:
{json.dumps(key_requirements)}

Resume lines:
{lines_block}

Job description:
{job_description[:3000]}
"""
        raw = self._call(prompt, temperature=0.4)
        parsed = self._extract_json(raw)

        if not isinstance(parsed, list):
            raise ValueError(f"Expected a JSON array but got: {type(parsed).__name__}")

        cleaned = []
        for item in parsed:
            if not isinstance(item, dict):
                continue

            if not isinstance(item.get("line_index"), int):
                continue

            if not isinstance(item.get("original"), str):
                continue

            options = item.get("options")
            if not isinstance(options, list) or len(options) != 3 or not all(isinstance(x, str) for x in options):
                continue

            cleaned.append({
                "line_index": item["line_index"],
                "original": item["original"],
                "options": options,
                "reason": item.get("reason", ""),
                "keywords_added": item.get("keywords_added", []),
            })

        if not cleaned:
            raise ValueError(f"No valid suggestions could be parsed.\n\nRaw model output:\n{raw}")

        return cleaned
