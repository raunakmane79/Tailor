import json
import re
import time
from difflib import SequenceMatcher
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

    def _compute_char_budget(self, original_len: int, line_char_limit: int) -> int:
        if original_len <= line_char_limit:
            return line_char_limit
        return line_char_limit * 2

    def _build_lines_block(self, lines: List[Dict[str, Any]], line_char_limit: int) -> str:
        output = []
        for line in lines:
            if not isinstance(line, dict) or not line.get("text", "").strip():
                continue

            char_count = int(line["char_count"])
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
- Keep the same line_index and do not change the order or position of any line
- Rewrite only the content of that specific line
- Each option should sound natural and human
- Maintain the same tone and style as the original resume
- If a keyword cannot fit naturally, leave it out
- line_index must exactly match one of the provided indices
- original must exactly match the provided line text for that line_index
- Do not merge lines
- Do not split lines
- Prioritize the target missing keywords when adding ATS language
- If no target keyword fits a line naturally, do not rewrite that line
- keywords_added must only include keywords actually present in the rewrites
- Each line has a maximum allowed character budget
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

        return f"""
You are a resume tailoring engine.

Return ONLY valid JSON.
No markdown.
No comments.
No intro text.

Required output schema:
{{
  "line_index": {line["index"]},
  "original": {json.dumps(line["text"], ensure_ascii=False)},
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
- Preserve the original meaning
- Add keywords only if they fit truthfully and naturally
- Do not keyword stuff
- Keep each option within {char_budget} characters
- Do not repeat the original line
- keywords_added must only include keywords actually present in at least one returned option
- If a keyword does not fit naturally, leave it out
- If only 2 or 3 truthful options are possible, return only those
- Prefer strong variety over quantity
- Do NOT change the candidate's name
- Do NOT rewrite or alter project titles
- Do NOT rewrite or alter position titles / job titles
- If this line is a project title, return no rewrite
- If this line is a position title, return no rewrite
- If this line is in the Skills section, only add relevant missing skills
- For Skills lines, preserve the original formatting and only extend skill content
- Use different truthful strategies where possible:
  1. ATS-keyword version
  2. concise professional version
  3. metrics-first version
  4. operations/process version
  5. logistics/distribution version
  6. collaboration/leadership version

Target missing keywords:
{json.dumps(target_keywords[:20], ensure_ascii=False)}

Fallback missing keywords:
{json.dumps(missing_keywords[:20], ensure_ascii=False)}

Key requirements:
{json.dumps(key_requirements[:12], ensure_ascii=False)}

Already generated options to avoid repeating:
{json.dumps(existing_options[:12], ensure_ascii=False)}

Resume line:
[{line["index"]}] [section={line.get("section_hint", "general")}] ({line["char_count"]} chars, max {char_budget}) {line["text"]}

Job description:
{job_description[:5000]}
""".strip()

    def _clean_options_for_line(
        self,
        actual_original: str,
        options: List[str],
        char_budget: int,
        target_keywords: List[str],
        original_len: int,
    ) -> List[str]:
        valid_options: List[str] = []

        for opt in options:
            if not isinstance(opt, str):
                continue

            opt_clean = opt.strip()
            if not opt_clean:
                continue

            if ATSUtils.normalize_compare_text(opt_clean) == ATSUtils.normalize_compare_text(actual_original):
                continue

            if len(opt_clean) > char_budget:
                continue

            min_reasonable_len = max(20, int(original_len * 0.45))
            if len(opt_clean) < min_reasonable_len:
                continue

            too_similar = False
            for existing in valid_options:
                if self._similarity_ratio(opt_clean, existing) >= 0.88:
                    too_similar = True
                    break
            if too_similar:
                continue

            valid_options.append(opt_clean)

        scored = []
        for opt in valid_options:
            hits = ATSUtils.find_keyword_hits(opt, target_keywords)
            score = (len(hits), -abs(len(opt) - original_len))
            scored.append((score, opt))

        scored.sort(reverse=True)
        ranked = [opt for _, opt in scored]

        final_ranked: List[str] = []
        for opt in ranked:
            if any(self._similarity_ratio(opt, kept) >= 0.86 for kept in final_ranked):
                continue
            final_ranked.append(opt)

        return final_ranked[:8]

    def generate_suggestions(
        self,
        lines: List[Dict[str, Any]],
        job_description: str,
        ats_analysis: Dict[str, Any],
        selected_keywords: Optional[List[str]] = None,
        line_char_limit: int = 90,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        if not isinstance(lines, list) or not lines:
            raise ValueError("No resume lines were provided.")

        target_keywords = selected_keywords or self._get_keyword_pool_for_ats(ats_analysis)[:15]

        candidate_lines: List[Dict[str, Any]] = []
        for line in lines:
            if not isinstance(line, dict):
                continue
            text = (line.get("text") or "").strip()
            if not text:
                continue
            if self._is_heading_like(text):
                continue
            if len(text) < 8:
                continue
            if "index" not in line or "char_count" not in line:
                continue
            candidate_lines.append(line)

        if not candidate_lines:
            raise ValueError("No valid resume lines available for suggestion generation.")

        line_map = {
            line["index"]: {
                "text": line["text"],
                "char_count": line["char_count"],
                "char_budget": self._compute_char_budget(line["char_count"], line_char_limit),
                "section_hint": line.get("section_hint", "general"),
            }
            for line in candidate_lines
        }

        all_cleaned: List[Dict[str, Any]] = []

        batched_lines = [candidate_lines[i:i + 8] for i in range(0, len(candidate_lines), 8)]

        for batch in batched_lines:
            prompt = self._build_suggestion_prompt(
                lines=batch,
                job_description=job_description,
                ats_analysis=ats_analysis,
                target_keywords=target_keywords,
                line_char_limit=line_char_limit,
            )

            parsed = None

            for attempt in range(max_retries):
                try:
                    raw = self._call(prompt, temperature=0.45, max_output_tokens=4200)
                    parsed = self._extract_json(raw)
                    if not isinstance(parsed, list):
                        raise ValueError(f"Expected a JSON array but got: {type(parsed).__name__}")
                    break
                except Exception:
                    if attempt < max_retries - 1:
                        time.sleep(1.2)

            if parsed is None:
                continue

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

                if not isinstance(options, list) or len(options) < 2:
                    continue

                actual_original = line_map[line_index]["text"]
                original_len = len(actual_original)
                char_budget = line_map[line_index]["char_budget"]

                if ATSUtils.normalize_compare_text(original) != ATSUtils.normalize_compare_text(actual_original):
                    continue

                cleaned_options = self._clean_options_for_line(
                    actual_original=actual_original,
                    options=options,
                    char_budget=char_budget,
                    target_keywords=target_keywords,
                    original_len=original_len,
                )

                if len(cleaned_options) < 2:
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

                option_keyword_hits: List[str] = []
                for opt in cleaned_options:
                    option_keyword_hits.extend(ATSUtils.find_keyword_hits(opt, target_keywords))
                option_keyword_hits = self._dedupe_keep_order(option_keyword_hits)

                if not keywords_added:
                    keywords_added = option_keyword_hits

                all_cleaned.append(
                    {
                        "line_index": line_index,
                        "original": actual_original,
                        "options": cleaned_options,
                        "reason": reason.strip(),
                        "keywords_added": keywords_added,
                        "char_budget": char_budget,
                    }
                )

        merged_by_line: Dict[int, Dict[str, Any]] = {}
        for item in all_cleaned:
            li = item["line_index"]
            if li not in merged_by_line:
                merged_by_line[li] = item
                continue

            existing = merged_by_line[li]
            combined_options = existing["options"] + item["options"]

            deduped_options: List[str] = []
            for opt in combined_options:
                if any(self._similarity_ratio(opt, kept) >= 0.86 for kept in deduped_options):
                    continue
                deduped_options.append(opt)

            existing["options"] = deduped_options[:8]

            merged_keywords = existing.get("keywords_added", []) + item.get("keywords_added", [])
            existing["keywords_added"] = self._dedupe_keep_order(merged_keywords)

            if len(item.get("reason", "")) > len(existing.get("reason", "")):
                existing["reason"] = item["reason"]

        retry_candidates = []
        for line in candidate_lines:
            li = line["index"]
            current = merged_by_line.get(li)
            if current is None or len(current.get("options", [])) < 4:
                retry_candidates.append(line)

        for line in retry_candidates[:12]:
            existing_options = merged_by_line.get(line["index"], {}).get("options", [])

            prompt = self._build_single_line_prompt(
                line=line,
                job_description=job_description,
                ats_analysis=ats_analysis,
                target_keywords=target_keywords,
                line_char_limit=line_char_limit,
                existing_options=existing_options,
            )

            parsed = None
            for attempt in range(2):
                try:
                    raw = self._call(prompt, temperature=0.55, max_output_tokens=1800)
                    parsed = self._extract_json(raw)
                    if not isinstance(parsed, dict):
                        raise ValueError("Expected single-line retry JSON object.")
                    break
                except Exception:
                    if attempt < 1:
                        time.sleep(1.0)

            if not parsed:
                continue

            if parsed.get("line_index") != line["index"]:
                continue

            actual_original = line["text"]
            if ATSUtils.normalize_compare_text(parsed.get("original", "")) != ATSUtils.normalize_compare_text(actual_original):
                continue

            new_options = parsed.get("options", [])
            if not isinstance(new_options, list):
                continue

            char_budget = self._compute_char_budget(line["char_count"], line_char_limit)
            cleaned_retry_options = self._clean_options_for_line(
                actual_original=actual_original,
                options=new_options,
                char_budget=char_budget,
                target_keywords=target_keywords,
                original_len=len(actual_original),
            )

            if len(cleaned_retry_options) < 2:
                continue

            reason = parsed.get("reason", "")
            if not isinstance(reason, str):
                reason = ""

            keywords_added = parsed.get("keywords_added", [])
            if not isinstance(keywords_added, list):
                keywords_added = []
            keywords_added = self._dedupe_keep_order(
                [kw.strip() for kw in keywords_added if isinstance(kw, str) and kw.strip()]
            )

            if line["index"] not in merged_by_line:
                merged_by_line[line["index"]] = {
                    "line_index": line["index"],
                    "original": actual_original,
                    "options": cleaned_retry_options[:8],
                    "reason": reason.strip(),
                    "keywords_added": keywords_added,
                    "char_budget": char_budget,
                }
            else:
                existing = merged_by_line[line["index"]]
                combined = existing["options"] + cleaned_retry_options
                deduped: List[str] = []
                for opt in combined:
                    if any(self._similarity_ratio(opt, kept) >= 0.86 for kept in deduped):
                        continue
                    deduped.append(opt)
                existing["options"] = deduped[:8]
                existing["keywords_added"] = self._dedupe_keep_order(
                    existing.get("keywords_added", []) + keywords_added
                )
                if len(reason.strip()) > len(existing.get("reason", "")):
                    existing["reason"] = reason.strip()

        final_results = list(merged_by_line.values())

        def line_score(item: Dict[str, Any]):
            kw_score = len(item.get("keywords_added", []))
            opt_score = len(item.get("options", []))
            return (-kw_score, -opt_score, item["line_index"])

        final_results = [x for x in final_results if len(x.get("options", [])) >= 2]
        final_results.sort(key=line_score)

        if not final_results:
            raise ValueError("Model returned responses, but no valid suggestions survived validation.")

        return final_results


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
