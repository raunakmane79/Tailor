"""
gemini_client.py
─────────────────
Wraps Google Gemini 1.5 Flash via the REST API.
Two main calls:
  1. analyze_ats()     → keyword gap + ATS score
  2. generate_suggestions() → 3 tailored options per line that needs changing
"""

from __future__ import annotations
import json
import re
import requests
from typing import List, Dict, Any


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


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
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Unexpected Gemini response: {data}") from e

    @staticmethod
    def _extract_json(text: str) -> Any:
        """Strip markdown fences and parse JSON."""
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        # Find first { or [
        start = min(
            (text.find(c) for c in ["{", "["] if text.find(c) != -1),
            default=0
        )
        text = text[start:]
        return json.loads(text)

    # ── ATS Analysis ─────────────────────────────────────────────────────────

    def analyze_ats(self, resume_text: str, job_description: str) -> Dict:
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

Analyze the resume against the job description and return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "ats_score": <integer 0-100 representing current keyword match percentage>,
  "score_note": "<one sentence explaining the score>",
  "present_keywords": ["keyword1", "keyword2", ...],
  "missing_keywords": ["keyword1", "keyword2", ...],
  "key_requirements": [
    "<requirement 1>",
    "<requirement 2>",
    ...
  ]
}}

Rules:
- present_keywords: important skills/tools/terms from the JD that already appear in the resume
- missing_keywords: important skills/tools/terms from the JD that are ABSENT from the resume (these must be added)
- key_requirements: 5-8 bullet points of the most important things the job requires
- Be specific about technical skills, tools, frameworks, certifications, and action verbs
- ats_score should reflect what a real ATS would give based on keyword overlap
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

    # ── Suggestion Generation ─────────────────────────────────────────────────

    def generate_suggestions(
        self,
        lines: List[Dict],
        job_description: str,
        ats_analysis: Dict,
    ) -> List[Dict]:
        """
        Returns a list of suggestion objects:
        {
          "line_index": int,
          "original": str,
          "options": [str, str, str],
          "reason": str,
          "keywords_added": [str]
        }
        Only lines that should be changed are included.
        """
        missing_kw = ats_analysis.get("missing_keywords", [])
        key_reqs = ats_analysis.get("key_requirements", [])

        # Build a numbered list of lines for the prompt
        lines_block = "\n".join(
            f"[{l['index']}] ({l['char_count']} chars) {l['text']}"
            for l in lines
            if l["text"].strip()
        )

        prompt = f"""
You are a professional resume writer and ATS optimization expert.

MISSING KEYWORDS THAT MUST BE ADDED:
{json.dumps(missing_kw)}

KEY JOB REQUIREMENTS:
{json.dumps(key_reqs)}

JOB DESCRIPTION SUMMARY:
\"\"\"
{job_description[:2000]}
\"\"\"

RESUME LINES (format: [line_index] (char_count chars) text):
{lines_block}

TASK:
Select the 8-15 most impactful resume lines to rewrite in order to:
1. Naturally incorporate missing keywords
2. Better align with the job requirements
3. Strengthen action verbs and quantify impact where possible

For each selected line, provide EXACTLY 3 rewrite options.

STRICT RULES:
- Preserve the line's approximate length (stay within ±30 characters of original)
- Do NOT change dates, company names, job titles, or contact info
- Do NOT add false information — only rephrase/emphasize real experience
- Each option must sound natural and human
- Options should vary in tone/approach (e.g., one more technical, one more results-focused, one more concise)

Return ONLY a valid JSON array (no markdown fences) like this:
[
  {{
    "line_index": <int>,
    "original": "<exact original text>",
    "options": ["<option 1>", "<option 2>", "<option 3>"],
    "reason": "<one sentence why this line should be changed>",
    "keywords_added": ["<keyword1>", ...]
  }},
  ...
]
"""
        raw = self._call(prompt, temperature=0.6)
        try:
            suggestions = self._extract_json(raw)
            if not isinstance(suggestions, list):
                return []
            # Validate structure
            valid = []
            for s in suggestions:
                if (
                    isinstance(s, dict)
                    and "line_index" in s
                    and "original" in s
                    and "options" in s
                    and isinstance(s["options"], list)
                    and len(s["options"]) >= 1
                ):
                    # Ensure exactly 3 options
                    opts = s["options"][:3]
                    while len(opts) < 3:
                        opts.append(opts[-1])
                    s["options"] = opts
                    s.setdefault("reason", "")
                    s.setdefault("keywords_added", [])
                    valid.append(s)
            return valid
        except Exception:
            return []
