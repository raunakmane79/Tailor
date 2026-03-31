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

        # remove trailing commas before ] or }
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

Rules:
- Analyze the resume against the job description
- Extract keywords directly from the job description
- Do not invent requirements not stated in the job description
- missing_keywords should contain important job-specific terms not clearly present in the resume
- present_keywords should contain terms clearly found in the resume
- key_requirements should summarize the most important explicit requirements from the job description

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
- Do not invent fake experience, metrics, tools, dates, roles, achievements, certifications, or technologies
- Keep each rewrite very close in length to the original
- Preserve the original meaning unless a small wording improvement is needed
- Keywords must be naturally integrated into the sentence
- Do NOT keyword stuff
- Do NOT force keywords where they sound unnatural
- Only add keywords if they genuinely fit the user's existing experience
- Keep the same line_index and do not change the order or position of any line
- Rewrite only the content of that specific line, not surrounding lines
- Each option should sound like a real human resume bullet, not AI-generated text
- Maintain the same tone and style as the original resume
- Prefer subtle wording improvements over aggressive rewriting
- If a keyword cannot fit naturally, leave it out
- line_index must exactly match one of the provided indices
- original must exactly match the provided line text for that line_index
- Do not merge lines
- Do not split lines
- Do not rewrite headings unless needed
- Focus on improving ATS match without making the resume sound unnatural

Missing keywords:
{json.dumps(missing_keywords, ensure_ascii=False)}

Key requirements:
{json.dumps(key_requirements, ensure_ascii=False)}

Resume lines:
{lines_block}

Job description:
{job_description[:4000]}
"""
        raw = self._call(prompt, temperature=0.35)
        parsed = self._extract_json(raw)

        if not isinstance(parsed, list):
            raise ValueError(f"Expected a JSON array but got: {type(parsed).__name__}")

        line_map = {
            line["index"]: {
                "text": line["text"],
                "char_count": line["char_count"]
            }
            for line in lines
            if isinstance(line, dict) and "index" in line and "text" in line and "char_count" in line
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

            if not isinstance(line_index, int):
                continue

            if line_index not in line_map:
                continue

            if not isinstance(original, str):
                continue

            actual_original = line_map[line_index]["text"]
            original_len = len(actual_original)

            # original returned by model must match actual line closely
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

                # avoid duplicate options
                if opt_clean.lower() in seen:
                    continue
                seen.add(opt_clean.lower())

                # keep length close to original
                if abs(len(opt_clean) - original_len) > max(12, int(original_len * 0.25)):
                    continue

                # prevent exact same line repeated as "suggestion"
                if opt_clean == actual_original.strip():
                    continue

                valid_options.append(opt_clean)

            if len(valid_options) != 3:
                continue

            if not isinstance(reason, str):
                reason = ""

            if not isinstance(keywords_added, list):
                keywords_added = []

            keywords_added = [k for k in keywords_added if isinstance(k, str) and k.strip()]

            cleaned.append({
                "line_index": line_index,
                "original": actual_original,
                "options": valid_options,
                "reason": reason.strip(),
                "keywords_added": keywords_added,
            })

        if not cleaned:
            raise ValueError(f"No valid suggestions could be parsed.\n\nRaw model output:\n{raw}")

        return cleaned
