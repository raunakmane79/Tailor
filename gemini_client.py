import json
import re
import time
from typing import Any, Dict, List, Optional

import requests
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"


class ATSUtils:
    @staticmethod
    def normalize_token(text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\-\+\#/\.& ]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def dedupe_keep_order(items: List[str]) -> List[str]:
        seen = set()
        output = []
        for item in items:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            norm = ATSUtils.normalize_token(cleaned)
            if cleaned and norm and norm not in seen:
                seen.add(norm)
                output.append(cleaned)
        return output

    @staticmethod
    def find_keyword_hits(text: str, keywords: List[str]) -> List[str]:
        text_n = ATSUtils.normalize_token(text)
        hits = []

        for kw in keywords:
            if not isinstance(kw, str) or not kw.strip():
                continue

            kw_clean = kw.strip()
            kw_n = ATSUtils.normalize_token(kw_clean)

            if not kw_n:
                continue

            if kw_n in text_n:
                hits.append(kw_clean)
                continue

            text_tokens = set(text_n.split())
            kw_tokens = set(kw_n.split())

            if kw_tokens and text_tokens.intersection(kw_tokens):
                hits.append(kw_clean)

        return ATSUtils.dedupe_keep_order(hits)


class GeminiClient:
    def __init__(self, api_key: str, resume_processor=None):
        self.api_key = api_key
        self.resume_processor = resume_processor
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def set_resume_processor(self, resume_processor) -> None:
        self.resume_processor = resume_processor

    def _call(self, prompt: str, temperature: float = 0.35, max_output_tokens: int = 3200) -> str:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
            },
        }

        response = self.session.post(
            f"{GEMINI_URL}?key={self.api_key}",
            json=body,
            timeout=90,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Gemini API Error: {response.status_code} - {response.text}")

        data = response.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            raise RuntimeError(f"Unexpected Gemini response: {data}") from exc

    def generate_content(self, prompt: str, temperature: float = 0.3) -> str:
        return self._call(prompt, temperature=temperature)

    def _clean_json_text(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"```json|```", "", cleaned).strip()
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", cleaned)
        cleaned = cleaned.replace("“", '"').replace("”", '"').replace("’", "'")
        return cleaned

    def _balance_json(self, text: str) -> str:
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

            if ch == "{":
                stack.append("}")
            elif ch == "[":
                stack.append("]")
            elif ch in "}]":
                if stack and ch == stack[-1]:
                    stack.pop()

        if in_string:
            text += '"'

        while stack:
            text += stack.pop()

        return text

    def _extract_first_json_block(self, text: str) -> str:
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

        return text[start:]

    def _extract_json(self, text: str):
        if not text or not text.strip():
            raise ValueError("Empty model response.")

        cleaned = self._clean_json_text(text)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        try:
            candidate = self._extract_first_json_block(cleaned)
            candidate = re.sub(r",\s*([\]}])", r"\1", candidate)
            return json.loads(candidate)
        except Exception:
            pass

        try:
            candidate = self._extract_first_json_block(cleaned)
            candidate = re.sub(r",\s*([\]}])", r"\1", candidate)
            candidate = self._balance_json(candidate)
            return json.loads(candidate)
        except Exception as exc:
            raise ValueError(f"JSON parse failed: {exc}\n\nRaw response:\n{cleaned}") from exc

    def _build_lines_block(self, lines: List[Dict[str, Any]]) -> str:
        return "\n".join(
            f"[{line['index']}] ({line['char_count']} chars) {line['text']}"
            for line in lines
            if isinstance(line, dict) and line.get("text", "").strip()
        )

    def _dedupe_keep_order(self, items: List[str]) -> List[str]:
        return ATSUtils.dedupe_keep_order(items)

    def _get_keyword_pool_for_ats(self, ats_analysis: Dict[str, Any]) -> List[str]:
        keyword_groups = [
            ats_analysis.get("high_priority_missing", []),
            ats_analysis.get("recommended_keyword_targets", []),
            ats_analysis.get("missing_keywords", []),
            ats_analysis.get("required_keywords", []),
            ats_analysis.get("preferred_keywords", []),
            ats_analysis.get("medium_priority_missing", []),
        ]

        pool: List[str] = []
        for group in keyword_groups:
            if not isinstance(group, list):
                continue
            for kw in group:
                if isinstance(kw, str) and kw.strip():
                    pool.append(kw.strip())

        return self._dedupe_keep_order(pool)

    def keyword_fits_line_truthfully(self, line_text: str, keyword: str) -> bool:
        line_text_n = ATSUtils.normalize_token(line_text)
        keyword_n = ATSUtils.normalize_token(keyword)

        if not line_text_n or not keyword_n:
            return False

        if keyword_n in line_text_n:
            return True

        line_tokens = set(line_text_n.split())
        keyword_tokens = set(keyword_n.split())
        return len(line_tokens.intersection(keyword_tokens)) > 0

    def analyze_ats(self, resume_text: str, job_description: str) -> Dict[str, Any]:
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
  "key_requirements": [],
  "required_keywords": [],
  "preferred_keywords": [],
  "high_priority_missing": [],
  "medium_priority_missing": [],
  "low_priority_missing": [],
  "recommended_keyword_targets": []
}}

Rules:
- Analyze the resume against the job description
- Extract keywords directly from the job description
- Do not invent requirements not stated in the job description
- present_keywords = terms clearly present in the resume
- missing_keywords = important job-specific terms not clearly present in the resume
- key_requirements = short explicit requirements taken from the job description
- required_keywords = strongest must-have ATS terms
- preferred_keywords = useful but non-essential terms
- high_priority_missing = highest-value missing truthful targets
- medium_priority_missing = useful but secondary missing targets
- low_priority_missing = lower-value missing targets
- recommended_keyword_targets = best missing keywords to prioritize first
- Keep arrays concise, relevant, and de-duplicated
- ats_score must be an integer from 0 to 100

RESUME:
{resume_text[:12000]}

JOB DESCRIPTION:
{job_description[:12000]}
""".strip()

        raw = self._call(prompt, temperature=0.2, max_output_tokens=2200)
        parsed = self._extract_json(raw)

        if not isinstance(parsed, dict):
            raise ValueError("ATS analysis must return a JSON object.")

        list_keys = [
            "present_keywords",
            "missing_keywords",
            "key_requirements",
            "required_keywords",
            "preferred_keywords",
            "high_priority_missing",
            "medium_priority_missing",
            "low_priority_missing",
            "recommended_keyword_targets",
        ]

        for key in list_keys:
            value = parsed.get(key, [])
            if not isinstance(value, list):
                parsed[key] = []
            else:
                parsed[key] = self._dedupe_keep_order(
                    [item for item in value if isinstance(item, str) and item.strip()]
                )

        ats_score = parsed.get("ats_score", 0)
        if not isinstance(ats_score, int):
            try:
                ats_score = int(ats_score)
            except Exception:
                ats_score = 0
        parsed["ats_score"] = max(0, min(100, ats_score))

        if not isinstance(parsed.get("score_note"), str):
            parsed["score_note"] = ""

        return parsed

    def _build_keyword_prompt_block(
        self,
        target_keywords: List[str],
        fallback_missing_keywords: List[str],
        key_requirements: List[str],
    ) -> str:
        return f"""
Target missing keywords:
{json.dumps(target_keywords[:15], ensure_ascii=False)}

Fallback missing keywords:
{json.dumps(fallback_missing_keywords[:15], ensure_ascii=False)}

Key requirements:
{json.dumps(key_requirements[:10], ensure_ascii=False)}
""".strip()

    def _build_suggestion_prompt(
        self,
        lines: List[Dict[str, Any]],
        job_description: str,
        ats_analysis: Dict[str, Any],
        target_keywords: List[str],
    ) -> str:
        missing_keywords = ats_analysis.get("missing_keywords", [])
        key_requirements = ats_analysis.get("key_requirements", [])
        lines_block = self._build_lines_block(lines)
        keyword_block = self._build_keyword_prompt_block(
            target_keywords=target_keywords,
            fallback_missing_keywords=missing_keywords,
            key_requirements=key_requirements,
        )

        return f"""
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
- Keep each rewrite close in length to the original
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
- Prioritize the target missing keywords when adding ATS language
- If no target keyword fits a line naturally, do not rewrite that line
- keywords_added must only include keywords actually present in the rewrite

{keyword_block}

Resume lines:
{lines_block[:12000]}

Job description:
{job_description[:5000]}
""".strip()

    def generate_suggestions(
        self,
        lines: List[Dict[str, Any]],
        job_description: str,
        ats_analysis: Dict[str, Any],
        selected_keywords: Optional[List[str]] = None,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        if not isinstance(lines, list) or not lines:
            raise ValueError("No resume lines were provided.")

        target_keywords = selected_keywords or self._get_keyword_pool_for_ats(ats_analysis)[:12]

        prompt = self._build_suggestion_prompt(
            lines=lines,
            job_description=job_description,
            ats_analysis=ats_analysis,
            target_keywords=target_keywords,
        )

        line_map = {
            line["index"]: {
                "text": line["text"],
                "char_count": line["char_count"],
            }
            for line in lines
            if isinstance(line, dict)
            and "index" in line
            and "text" in line
            and "char_count" in line
        }

        last_error = None

        for attempt in range(max_retries):
            try:
                raw = self._call(prompt, temperature=0.3, max_output_tokens=3200)
                parsed = self._extract_json(raw)

                if not isinstance(parsed, list):
                    raise ValueError(f"Expected a JSON array but got: {type(parsed).__name__}")

                cleaned: List[Dict[str, Any]] = []

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
                        opt_norm = ATSUtils.normalize_token(opt_clean)

                        if not opt_norm or opt_norm in seen:
                            continue
                        seen.add(opt_norm)

                        if opt_clean == actual_original.strip():
                            continue

                        max_len_delta = max(18, int(max(1, original_len) * 0.45))
                        if abs(len(opt_clean) - original_len) > max_len_delta:
                            continue

                        valid_options.append(opt_clean)

                    if len(valid_options) != 3:
                        continue

                    if not isinstance(reason, str):
                        reason = ""

                    if not isinstance(keywords_added, list):
                        keywords_added = []

                    keywords_added = [
                        kw.strip()
                        for kw in keywords_added
                        if isinstance(kw, str) and kw.strip()
                    ]
                    keywords_added = self._dedupe_keep_order(keywords_added)

                    option_keyword_hits = []
                    for opt in valid_options:
                        option_keyword_hits.extend(ATSUtils.find_keyword_hits(opt, target_keywords))

                    option_keyword_hits = self._dedupe_keep_order(option_keyword_hits)

                    if target_keywords and not option_keyword_hits and not keywords_added:
                        continue

                    if not keywords_added:
                        keywords_added = option_keyword_hits

                    cleaned.append(
                        {
                            "line_index": line_index,
                            "original": actual_original,
                            "options": valid_options,
                            "reason": reason.strip(),
                            "keywords_added": keywords_added,
                        }
                    )

                if cleaned:
                    cleaned = sorted(cleaned, key=lambda x: x["line_index"])
                    return cleaned

                raise ValueError("Model returned JSON, but no valid suggestions survived validation.")

            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    time.sleep(1.2)

        raise ValueError(f"Suggestion generation failed after {max_retries} attempts: {last_error}")


def extract_lines_with_counts(resume_text: str) -> List[Dict[str, Any]]:
    lines = []
    for idx, line in enumerate(resume_text.splitlines()):
        lines.append(
            {
                "index": idx,
                "text": line,
                "char_count": len(line),
            }
        )
    return lines
