import json
import re
import requests
import time

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
                "maxOutputTokens": 3000,
                "responseMimeType": "application/json",
            },
        }

        response = requests.post(
            f"{GEMINI_URL}?key={self.api_key}",
            headers=headers,
            json=body,
            timeout=90,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Gemini API Error: {response.status_code} - {response.text}")

        data = response.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            raise RuntimeError(f"Unexpected Gemini response: {data}")

    def _clean_json_text(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"```json|```", "", cleaned).strip()

        # remove control chars except normal whitespace
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", cleaned)

        return cleaned

    def _balance_json(self, text: str) -> str:
        """
        Try to repair truncated JSON by balancing braces/brackets.
        This will not fix every case, but helps when Gemini cuts off near the end.
        """
        stack = []
        in_string = False
        escape = False

        for ch in text:
            if escape:
                escape = False
                continue

            if ch == "\\":
                escape = True
                continue

            if ch == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]":
                if stack and ch == stack[-1]:
                    stack.pop()

        if in_string:
            text += '"'

        while stack:
            text += stack.pop()

        return text

    def _extract_first_json_block(self, text: str) -> str:
        """
        Extract the first top-level JSON object or array from text.
        """
        start = None
        opener = None

        for i, ch in enumerate(text):
            if ch in "[{":
                start = i
                opener = ch
                break

        if start is None:
            raise ValueError(f"No JSON found in model response:\n{text}")

        closer = "]" if opener == "[" else "}"

        depth = 0
        in_string = False
        escape = False

        for i in range(start, len(text)):
            ch = text[i]

            if escape:
                escape = False
                continue

            if ch == "\\":
                escape = True
                continue

            if ch == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

        # if incomplete, return from start onward and let balancer try
        return text[start:]

    def _extract_json(self, text: str):
        if not text or not text.strip():
            raise ValueError("Empty model response.")

        cleaned = self._clean_json_text(text)

        # Attempt 1: direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Attempt 2: extract first block
        try:
            candidate = self._extract_first_json_block(cleaned)
            candidate = re.sub(r",\s*([\]}])", r"\1", candidate)
            return json.loads(candidate)
        except Exception:
            pass

        # Attempt 3: balance truncated JSON
        try:
            candidate = self._extract_first_json_block(cleaned)
            candidate = re.sub(r",\s*([\]}])", r"\1", candidate)
            candidate = self._balance_json(candidate)
            return json.loads(candidate)
        except Exception as e:
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

Rules:
- Analyze the resume against the job description
- Extract keywords directly from the job description
- Do not invent requirements not stated in the job description
- missing_keywords should contain important job-specific terms not clearly present in the resume
- present_keywords should contain terms clearly found in the resume
- key_requirements should contain short explicit requirements from the job description
- Keep arrays concise and relevant

RESUME:
{resume_text[:12000]}

JOB DESCRIPTION:
{job_description[:12000]}
"""
        raw = self._call(prompt, temperature=0.2)
        return self._extract_json(raw)

    def _build_lines_block(self, lines):
        return "\n".join(
            f"[{line['index']}] ({line['char_count']} chars) {line['text']}"
            for line in lines
            if line.get("text", "").strip()
        )

    def generate_suggestions(self, lines, job_description, ats_analysis, max_retries=3):
        missing_keywords = ats_analysis.get("missing_keywords", [])
        key_requirements = ats_analysis.get("key_requirements", [])

        lines_block = self._build_lines_block(lines)

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

Hard rules:
- Output MUST be complete valid JSON
- Do not stop mid-array
- Escape all quotes properly
- Select only lines that actually need improvement
- Return 4 to 8 items max
- options must contain exactly 3 strings
- Do not invent fake experience, metrics, tools, dates, roles, achievements, certifications, or technologies
- Keep each rewrite very close in length to the original
- Preserve the original meaning unless a small wording improvement is needed
- Keywords must be naturally integrated into the sentence
- Do NOT keyword stuff
- Do NOT force keywords where they sound unnatural
- Only add keywords if they genuinely fit the user's existing experience
- Keep the same line_index and do not change the order or position of any line
- Rewrite only the content of that specific line
- Each option should sound natural and human
- Maintain the same tone and style as the original resume
- If a keyword cannot fit naturally, leave it out
- line_index must exactly match one of the provided indices
- original must exactly match the provided line text for that line_index
- Do not merge lines
- Do not split lines
- Prefer concise output over many items

Missing keywords:
{json.dumps(missing_keywords[:15], ensure_ascii=False)}

Key requirements:
{json.dumps(key_requirements[:10], ensure_ascii=False)}

Resume lines:
{lines_block[:12000]}

Job description:
{job_description[:5000]}
"""

        last_error = None

        for attempt in range(max_retries):
            try:
                raw = self._call(prompt, temperature=0.3)
                parsed = self._extract_json(raw)

                if not isinstance(parsed, list):
                    raise ValueError(f"Expected a JSON array but got: {type(parsed).__name__}")

                line_map = {
                    line["index"]: {
                        "text": line["text"],
                        "char_count": line["char_count"]
                    }
                    for line in lines
                    if isinstance(line, dict)
                    and "index" in line
                    and "text" in line
                    and "char_count" in line
                }

                cleaned = []

                for item in parsed:
                    if not isinstance(item, dict):
                        continue

                    line_index = item.get("line_index")
                    original = item.get("original")
                    options = item.get("options")
                    reason = item.get("reason", "")
                    keywords_added = item.get("keywords_added", [])

                    if not isinstance(line_index, int) or line_index not in line_map:
                        continue

                    if not isinstance(original, str):
                        continue

                    actual_original = line_map[line_index]["text"]
                    original_len = len(actual_original)

                    if original.strip() != actual_original.strip():
                        continue

                    if not isinstance(options, list) or len(options) != 3:
                        continue

                    if not all(isinstance(opt, str) and opt.strip() for opt in options):
                        continue

                    valid_options = []
                    seen = set()

                    for opt in options:
                        opt_clean = opt.strip()

                        if opt_clean.lower() in seen:
                            continue
                        seen.add(opt_clean.lower())

                        if abs(len(opt_clean) - original_len) > max(12, int(original_len * 0.25)):
                            continue

                        if opt_clean == actual_original.strip():
                            continue

                        valid_options.append(opt_clean)

                    if len(valid_options) != 3:
                        continue

                    if not isinstance(reason, str):
                        reason = ""

                    if not isinstance(keywords_added, list):
                        keywords_added = []

                    keywords_added = [
                        k for k in keywords_added
                        if isinstance(k, str) and k.strip()
                    ]

                    cleaned.append({
                        "line_index": line_index,
                        "original": actual_original,
                        "options": valid_options,
                        "reason": reason.strip(),
                        "keywords_added": keywords_added,
                    })

                if cleaned:
                    return cleaned

                raise ValueError("Model returned JSON, but no valid suggestions survived validation.")

            except Exception as e:
                last_error = e
                time.sleep(1.2)

        raise ValueError(f"Suggestion generation failed after {max_retries} attempts: {last_error}")


def extract_lines_with_counts(resume_text: str):
    lines = []
    for idx, line in enumerate(resume_text.splitlines()):
        lines.append({
            "index": idx,
            "text": line,
            "char_count": len(line)
        })
    return lines
