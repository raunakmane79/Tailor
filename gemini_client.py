import json
import re
import time
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"


STRICT_SINGLE_LINE_THRESHOLD = 100
STRICT_SINGLE_LINE_MAX = 90
STRICT_DOUBLE_LINE_MAX = 180


class ATSUtils:
    @staticmethod
    def normalize_token(text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\-\+#/\.& ]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def normalize_compare_text(text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.strip().lower()
        text = text.replace("–", "-").replace("—", "-")
        text = text.replace("“", '"').replace("”", '"').replace("’", "'")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

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
                    return text[start : i + 1]

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

    def _compute_char_budget(self, original_len: int, line_char_limit: int = STRICT_SINGLE_LINE_MAX) -> int:
        if original_len <= STRICT_SINGLE_LINE_THRESHOLD:
            return STRICT_SINGLE_LINE_MAX
        return STRICT_DOUBLE_LINE_MAX

    def _build_lines_block(self, lines: List[Dict[str, Any]], line_char_limit: int) -> str:
        output = []
        for line in lines:
            if not isinstance(line, dict) or not line.get("text", "").strip():
                continue

            char_count = int(line.get("char_count", len(line.get("text", ""))))
            char_budget = self._compute_char_budget(char_count, line_char_limit)
            section_hint = line.get("section_hint", "general")

            output.append(
                f"[{line['index']}] [section={section_hint}] ({char_count} chars, max {char_budget}) {line['text']}"
            )
        return "\n".join(output)

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

    def _similarity_ratio(self, a: str, b: str) -> float:
        return SequenceMatcher(
            None,
            ATSUtils.normalize_compare_text(a),
            ATSUtils.normalize_compare_text(b),
        ).ratio()

    def _is_heading_like(self, text: str) -> bool:
        t = (text or "").strip()
        if not t:
            return True

        t_low = t.lower().strip(":").strip()
        heading_words = {
            "education",
            "experience",
            "work experience",
            "projects",
            "skills",
            "technical skills",
            "leadership",
            "activities",
            "summary",
            "profile",
            "certifications",
            "awards",
            "contact",
            "professional experience",
        }

        if t_low in heading_words:
            return True
        if len(t) <= 4:
            return True
        if len(t.split()) <= 5 and t.upper() == t:
            return True
        return False

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
        line_char_limit: int,
    ) -> str:
        missing_keywords = ats_analysis.get("missing_keywords", [])
        key_requirements = ats_analysis.get("key_requirements", [])
        lines_block = self._build_lines_block(lines, line_char_limit)
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
    "options": ["option 1", "option 2", "option 3", "option 4"],
    "reason": "short reason",
    "keywords_added": ["keyword1", "keyword2"]
  }}
]

Hard rules:
- Output MUST be complete valid JSON
- Select only lines that actually need improvement
- Return as many useful line suggestions as possible
- Prefer covering more strong candidate lines
- Each line may contain 2 to 8 options
- Do NOT force a fixed number of options if the line does not support them truthfully
- Do not invent fake experience, metrics, tools, dates, roles, achievements, certifications, or technologies
- Preserve the original meaning unless a small wording improvement is needed
- Keywords must be naturally integrated into the sentence
- Do NOT keyword stuff
- Do NOT force keywords where they sound unnatural
- Only add keywords if they genuinely fit the user's existing experience
- Do NOT add niche company-specific, plant-specific, or industry-specific systems, standards, certifications, audits, or compliance frameworks unless they are clearly supported by the original resume line
- Do NOT add material-specific, product-specific, or directly process-input keywords unless they are clearly supported by the original resume line
- If the job description mentions a specific material, component, ingredient, or manufactured item, do NOT force it into the resume unless the original line already clearly supports it
- If a business term is highly domain-specific and unlikely from the original line, leave it out
- Keep the same line_index and do not change the order or position of any line
- Rewrite only the content of that specific line
- Each option should sound natural and human
- Maintain the same tone and style as the original resume
- The sentence must read smoothly and logically, not like disconnected keywords were inserted
- Every rewrite must flow naturally from start to finish
- Do not produce awkward phrasing just to match keywords
- If a keyword makes the sentence sound forced, unnatural, or illogical, do not use it
- If a keyword cannot fit naturally, leave it out
- line_index must exactly match one of the provided indices
- original must exactly match the provided line text for that line_index
- Do not merge lines
- Do not split lines
- Prioritize the target missing keywords when adding ATS language
- Prefer broader transferable keywords over narrow material-specific or product-specific keywords
- If no target keyword fits a line naturally, do not rewrite that line
- keywords_added must only include keywords actually present in the rewrites
- Character rule: if original line length is 100 characters or less, max rewrite length is 90 characters
- Character rule: if original line length is more than 100 characters, max rewrite length is 180 characters
- One original line must be replaced by exactly one rewritten line
- Do not exceed the max character budget shown beside each line
- For each line, options must be materially different from one another
- Do not produce near-duplicate paraphrases
- Do NOT change the candidate's name
- Do NOT rewrite or alter project titles
- Do NOT rewrite or alter position titles / job titles
- If a line appears to be a project title, skip it
- If a line appears to be a position title, skip it
- If a line is in the Skills section, only add relevant missing skills
- For Skills lines, preserve the original formatting, separators, and order as much as possible
- For Skills lines, append or lightly extend skills instead of rewriting the full line
- Use different truthful strategies where possible:
  1. ATS keyword-focused
  2. concise professional
  3. metrics-first
  4. operations/process
  5. logistics/distribution
  6. collaboration/communication
- Prefer variety and usefulness over repetitive paraphrasing

{keyword_block}

Resume lines:
{lines_block[:12000]}

Job description:
{job_description[:5000]}
""".strip()

    def _build_single_line_prompt(
        self,
        line: Dict[str, Any],
        job_description: str,
        ats_analysis: Dict[str, Any],
        target_keywords: List[str],
        line_char_limit: int,
        existing_options: Optional[List[str]] = None,
    ) -> str:
        existing_options = existing_options or []
        char_budget = self._compute_char_budget(line["char_count"], line_char_limit)
        missing_keywords = ats_analysis.get("missing_keywords", [])
        key_requirements = ats_analysis.get("key_requirements", [])

        existing_options_block = json.dumps(existing_options[:8], ensure_ascii=False)

        return f"""
You are a resume tailoring engine.

Return ONLY valid JSON.
No markdown.
No comments.
No intro text.

Required output schema:
{{
  "line_index": {line['index']},
  "original": {json.dumps(line['text'], ensure_ascii=False)},
  "options": [
    "rewrite 1",
    "rewrite 2",
    "rewrite 3"
  ],
  "reason": "short reason",
  "keywords_added": ["keyword1", "keyword2"]
}}

Hard rules:
- Rewrite ONLY this one resume line
- Return as many strong options as possible, ideally 4 to 8
- Every option must be materially different from the others
- Do NOT generate paraphrases that say the same thing
- Do not invent fake experience, tools, metrics, dates, roles, certifications, or achievements
- Do NOT add niche company-specific, plant-specific, or industry-specific systems, standards, certifications, audits, or compliance frameworks unless they are clearly supported by the original line
- Do NOT add material-specific, product-specific, or directly process-input keywords unless they are clearly supported by the original line
- If the job description mentions a specific material, component, ingredient, or manufactured item, do NOT force it into the resume unless the original line already clearly supports it
- Preserve original meaning and tone
- Sound natural and human
- Avoid keyword stuffing
- If a keyword does not fit naturally, leave it out
- Do not merge lines
- Do not split lines
- One original line must be replaced by one rewritten line only
- Character rule: if original line length is 100 characters or less, max rewrite length is 90 characters
- Character rule: if original line length is more than 100 characters, max rewrite length is 180 characters
- Do not exceed max {char_budget} characters for any option
- Keep the same job title / project title / name if present; do not rewrite those titles
- keywords_added must only include keywords actually used in the returned options
- If existing options are provided, avoid near-duplicates of them

Target keywords:
{json.dumps(target_keywords[:15], ensure_ascii=False)}

Fallback missing keywords:
{json.dumps(missing_keywords[:15], ensure_ascii=False)}

Key requirements:
{json.dumps(key_requirements[:10], ensure_ascii=False)}

Existing options to avoid duplicating:
{existing_options_block}

Resume line:
[{line['index']}] ({line['char_count']} chars, max {char_budget}) {line['text']}

Job description:
{job_description[:5000]}
""".strip()

    def _normalize_suggestion_item(
        self,
        item: Dict[str, Any],
        line_lookup: Dict[int, Dict[str, Any]],
        line_char_limit: int,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(item, dict):
            return None

        line_index = item.get("line_index")
        if not isinstance(line_index, int):
            try:
                line_index = int(line_index)
            except Exception:
                return None

        if line_index not in line_lookup:
            return None

        line = line_lookup[line_index]
        original = item.get("original", "")
        if not isinstance(original, str) or not original.strip():
            original = line["text"]

        if self._similarity_ratio(original, line["text"]) < 0.9:
            original = line["text"]

        raw_options = item.get("options", [])
        if not isinstance(raw_options, list):
            raw_options = []

        budget = self._compute_char_budget(line["char_count"], line_char_limit)
        valid_options: List[str] = []

        for opt in raw_options:
            if not isinstance(opt, str):
                continue
            cleaned = re.sub(r"\s+", " ", opt).strip()
            if not cleaned:
                continue
            if len(cleaned) > budget:
                continue
            if ATSUtils.normalize_compare_text(cleaned) == ATSUtils.normalize_compare_text(line["text"]):
                continue
            if self._is_heading_like(cleaned):
                continue
            if any(self._similarity_ratio(cleaned, existing) > 0.96 for existing in valid_options):
                continue
            valid_options.append(cleaned)

        if len(valid_options) < 2:
            return None

        reason = item.get("reason", "")
        if not isinstance(reason, str):
            reason = ""

        keywords_added = item.get("keywords_added", [])
        if not isinstance(keywords_added, list):
            keywords_added = []
        keywords_added = self._dedupe_keep_order(
            [kw for kw in keywords_added if isinstance(kw, str) and kw.strip()]
        )

        actual_hits = ATSUtils.find_keyword_hits(" ".join(valid_options), keywords_added)

        return {
            "line_index": line_index,
            "original": line["text"],
            "options": valid_options,
            "reason": reason.strip(),
            "keywords_added": actual_hits,
            "char_budget": budget,
        }

    def _repair_suggestions_if_needed(
        self,
        suggestions: List[Dict[str, Any]],
        lines: List[Dict[str, Any]],
        job_description: str,
        ats_analysis: Dict[str, Any],
        target_keywords: List[str],
        line_char_limit: int,
    ) -> List[Dict[str, Any]]:
        line_lookup = {int(line["index"]): line for line in lines if isinstance(line.get("index"), int)}
        repaired = suggestions[:]
        covered_indices = {item["line_index"] for item in repaired}

        for line in lines:
            idx = line["index"]
            if idx in covered_indices:
                continue
            prompt = self._build_single_line_prompt(
                line=line,
                job_description=job_description,
                ats_analysis=ats_analysis,
                target_keywords=target_keywords,
                line_char_limit=line_char_limit,
                existing_options=[],
            )
            try:
                raw = self._call(prompt, temperature=0.45, max_output_tokens=1400)
                parsed = self._extract_json(raw)
                repaired_item = self._normalize_suggestion_item(parsed, line_lookup, line_char_limit)
                if repaired_item is not None:
                    repaired.append(repaired_item)
            except Exception:
                continue

        repaired.sort(key=lambda x: x["line_index"])
        return repaired

    def generate_suggestions(
        self,
        lines: List[Dict[str, Any]],
        job_description: str,
        ats_analysis: Dict[str, Any],
        selected_keywords: Optional[List[str]] = None,
        line_char_limit: int = STRICT_SINGLE_LINE_MAX,
    ) -> List[Dict[str, Any]]:
        if not isinstance(lines, list) or not lines:
            return []

        target_keywords = self._dedupe_keep_order(
            selected_keywords or self._get_keyword_pool_for_ats(ats_analysis)
        )

        line_lookup = {
            int(line["index"]): line
            for line in lines
            if isinstance(line, dict) and isinstance(line.get("index"), int)
        }

        prompt = self._build_suggestion_prompt(
            lines=lines,
            job_description=job_description,
            ats_analysis=ats_analysis,
            target_keywords=target_keywords,
            line_char_limit=line_char_limit,
        )

        raw = self._call(prompt, temperature=0.4, max_output_tokens=4000)
        parsed = self._extract_json(raw)

        if not isinstance(parsed, list):
            raise ValueError("Suggestions response must be a JSON array.")

        normalized: List[Dict[str, Any]] = []
        seen_line_indices = set()

        for item in parsed:
            fixed = self._normalize_suggestion_item(item, line_lookup, line_char_limit)
            if fixed is None:
                continue
            if fixed["line_index"] in seen_line_indices:
                continue
            seen_line_indices.add(fixed["line_index"])
            normalized.append(fixed)

        if normalized:
            normalized = self._repair_suggestions_if_needed(
                suggestions=normalized,
                lines=[line for line in lines if line["index"] not in seen_line_indices],
                job_description=job_description,
                ats_analysis=ats_analysis,
                target_keywords=target_keywords,
                line_char_limit=line_char_limit,
            )
        else:
            normalized = self._repair_suggestions_if_needed(
                suggestions=[],
                lines=lines,
                job_description=job_description,
                ats_analysis=ats_analysis,
                target_keywords=target_keywords,
                line_char_limit=line_char_limit,
            )

        normalized.sort(key=lambda x: x["line_index"])
        return normalized
