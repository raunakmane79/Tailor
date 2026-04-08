"""
gemini_client.py  —  Rizzume AI Engine v2
Aggressive keyword placement · 5 real suggestions per line · Layout-safe
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

class ATSUtils:
    STOPWORDS = {
        "the", "and", "for", "with", "from", "that", "this", "will", "your", "you", "our", "are", "but",
        "have", "has", "had", "into", "than", "then", "them", "their", "his", "her", "its", "who", "able",
        "ability", "skills", "skill", "knowledge", "experience", "preferred", "required", "strong", "good",
        "using", "use", "used", "work", "working", "works", "can", "capable", "perform", "performs",
        "across", "various", "within", "basic", "some", "many", "more", "most", "other", "such", "shows",
        "learning", "understanding", "identify", "identifying", "understand", "problem", "problems", "solution",
        "concept", "concepts", "year", "years", "degree", "discipline", "related", "meaningful", "levels",
    }

    @staticmethod
    def normalize_token(text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.lower().strip()
        text = text.replace("–", "-").replace("—", "-")
        text = re.sub(r"[^a-z0-9\-\+\#/\.&, ]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def normalize_compare_text(text: str) -> str:
        return ATSUtils.normalize_token(text).replace(" ,", ",").strip()

    @staticmethod
    def dedupe_keep_order(items: List[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for item in items:
            if not isinstance(item, str):
                continue
            clean = re.sub(r"\s+", " ", item).strip(" ,.;:-")
            norm = ATSUtils.normalize_token(clean)
            if clean and norm and norm not in seen:
                seen.add(norm)
                out.append(clean)
        return out

    @staticmethod
    def split_keyword_tokens(keyword: str) -> List[str]:
        norm = ATSUtils.normalize_token(keyword)
        return [tok for tok in re.split(r"[ /,&]+", norm) if tok]

    @staticmethod
    def keyword_in_text(text: str, keyword: str) -> bool:
        text_n = ATSUtils.normalize_token(text)
        kw_n = ATSUtils.normalize_token(keyword)
        if not text_n or not kw_n:
            return False
        if kw_n in text_n:
            return True
        text_tokens = set(text_n.split())
        kw_tokens = [t for t in ATSUtils.split_keyword_tokens(keyword) if t not in ATSUtils.STOPWORDS]
        if not kw_tokens:
            return False
        overlap = sum(1 for tok in kw_tokens if tok in text_tokens)
        if len(kw_tokens) == 1:
            return overlap == 1
        return overlap >= max(1, len(kw_tokens) - 1)

    @staticmethod
    def find_keyword_hits(text: str, keywords: List[str]) -> List[str]:
        return ATSUtils.dedupe_keep_order([kw for kw in keywords if ATSUtils.keyword_in_text(text, kw)])

    @staticmethod
    def extract_keywords_rule_based(job_description: str, max_keywords: int = 40) -> List[str]:
        text = job_description.replace("•", "\n")
        lines = [re.sub(r"\s+", " ", line).strip(" -•\t") for line in text.splitlines() if line.strip()]
        candidates: List[str] = [
            "AutoCAD", "GEMBA", "time study", "flowcharting software", "project management",
            "Industrial Engineering", "continuous improvement", "warehouse operation", "distribution",
            "logistics", "inbound", "put away", "pick", "pack", "ship", "vendors", "suppliers",
            "operators", "layout changes", "process steps", "problem solving",
        ]

        removable_patterns = [
            r"\brequired\b", r"\bpreferred\b", r"\bcapable of using\b", r"\bcan use\b",
            r"\bcan perform\b", r"\bperforms\b", r"\blearning to\b", r"\bfamiliar with\b",
            r"\bsome knowledge of\b", r"\bable to\b", r"\bstrengthen\b",
            r"\b\d+\s*-\s*\d+ years of experience in\b", r"\bbachelor'?s degree in\b",
        ]

        for line in lines:
            for pattern in removable_patterns:
                line = re.sub(pattern, "", line, flags=re.I)
            line = re.sub(r"\s+", " ", line).strip(" ,.;:-")
            for part in re.split(r",|;|\(|\)|/", line):
                part = re.sub(r"\s+", " ", part).strip(" ,.;:-")
                if not part:
                    continue
                norm = ATSUtils.normalize_token(part)
                tokens = [t for t in norm.split() if t not in ATSUtils.STOPWORDS]
                if not tokens or len(tokens) > 5:
                    continue
                phrase = " ".join(tokens)
                if len(phrase) < 4:
                    continue
                candidates.append(phrase)

        ranked_seed = ATSUtils.dedupe_keep_order(candidates)
        freq = Counter(ATSUtils.normalize_token(x) for x in ranked_seed)
        ranked = sorted(ranked_seed, key=lambda x: (-freq[ATSUtils.normalize_token(x)], 0 if " " in x else 1, len(x)))
        banned = {
            "team", "data", "equivalent", "operation", "operations team", "low hanging fruit opportunities",
            "various levels", "outside organizations", "routine approaches", "obvious solutions",
        }
        cleaned = [item for item in ranked if ATSUtils.normalize_token(item) not in banned]
        return cleaned[:max_keywords]


class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _call_json(self, prompt: str, temperature: float = 0.2, max_output_tokens: int = 3000) -> Any:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
        response = self.session.post(f"{GEMINI_URL}?key={self.api_key}", json=body, timeout=120)
        if response.status_code != 200:
            raise RuntimeError(f"Gemini API Error: {response.status_code} - {response.text}")
        payload = response.json()
        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            raise RuntimeError(f"Unexpected Gemini response: {payload}") from exc
        return self._extract_json(text)

    def _extract_json(self, text: str) -> Any:
        cleaned = text.strip()
        cleaned = re.sub(r"```json|```", "", cleaned).strip()
        cleaned = cleaned.replace("“", '"').replace("”", '"').replace("’", "'")
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        start_candidates = [i for i in (cleaned.find("{"), cleaned.find("[")) if i != -1]
        if not start_candidates:
            raise ValueError(f"No JSON found in model response: {cleaned[:500]}")
        start = min(start_candidates)
        candidate = cleaned[start:]
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        stack = []
        in_string = False
        escape = False
        end_pos = None
        for idx, ch in enumerate(candidate):
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
            if ch in "[{":
                stack.append("}" if ch == "{" else "]")
            elif ch in "]}":
                if stack and ch == stack[-1]:
                    stack.pop()
                    if not stack:
                        end_pos = idx + 1
                        break
        if end_pos is None:
            raise ValueError(f"Could not parse JSON response: {cleaned[:800]}")
        return json.loads(candidate[:end_pos])

    def analyze_ats(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        rule_keywords = ATSUtils.extract_keywords_rule_based(job_description, max_keywords=50)
        prompt = f"""
You are an ATS analysis engine for resume tailoring.
Return ONLY valid JSON.

Schema:
{{
  "required_keywords": [],
  "preferred_keywords": [],
  "key_requirements": [],
  "priority_keywords": [],
  "hard_requirements": [],
  "resume_strengths": [],
  "resume_gaps": []
}}

Rules:
- Use only job-description language.
- required_keywords = must-have ATS terms, tools, methods, domain phrases, or responsibilities.
- preferred_keywords = useful but secondary terms.
- priority_keywords = the best terms to place first in the resume.
- hard_requirements = direct must-haves from the JD.
- key_requirements = concise requirement statements from the JD.
- Keep arrays de-duplicated and concise.
- Avoid generic filler unless explicitly emphasized.

Seed keywords from rule-based extraction:
{json.dumps(rule_keywords[:40], ensure_ascii=False)}

RESUME:
{resume_text[:14000]}

JOB DESCRIPTION:
{job_description[:14000]}
""".strip()
        parsed = self._call_json(prompt, temperature=0.15, max_output_tokens=2200)
        if not isinstance(parsed, dict):
            raise ValueError("ATS analysis response was not a JSON object.")

        required_keywords = ATSUtils.dedupe_keep_order(parsed.get("required_keywords", []) + parsed.get("priority_keywords", []))
        preferred_keywords = ATSUtils.dedupe_keep_order(parsed.get("preferred_keywords", []))
        all_keywords = ATSUtils.dedupe_keep_order(required_keywords + preferred_keywords + rule_keywords)

        present = ATSUtils.find_keyword_hits(resume_text, all_keywords)
        missing = [kw for kw in all_keywords if kw not in present]
        high_priority_missing = [kw for kw in required_keywords if kw in missing]
        medium_priority_missing = [kw for kw in preferred_keywords if kw in missing and kw not in high_priority_missing]
        low_priority_missing = [kw for kw in rule_keywords if kw in missing and kw not in high_priority_missing and kw not in medium_priority_missing]

        keyword_score = round((len(present) / max(1, len(all_keywords))) * 100) if all_keywords else 0
        required_score = round((len([kw for kw in required_keywords if kw in present]) / max(1, len(required_keywords))) * 100) if required_keywords else keyword_score
        ats_score = round((required_score * 0.7) + (keyword_score * 0.3))

        return {
            "ats_score": max(0, min(100, ats_score)),
            "score_note": f"{len(present)} of {len(all_keywords)} tracked keywords are already present.",
            "present_keywords": present,
            "missing_keywords": missing,
            "required_keywords": required_keywords,
            "preferred_keywords": preferred_keywords,
            "high_priority_missing": high_priority_missing,
            "medium_priority_missing": medium_priority_missing,
            "low_priority_missing": low_priority_missing,
            "recommended_keyword_targets": high_priority_missing[:20] + medium_priority_missing[:12],
            "key_requirements": ATSUtils.dedupe_keep_order(parsed.get("key_requirements", [])),
            "hard_requirements": ATSUtils.dedupe_keep_order(parsed.get("hard_requirements", [])),
            "resume_strengths": ATSUtils.dedupe_keep_order(parsed.get("resume_strengths", [])),
            "resume_gaps": ATSUtils.dedupe_keep_order(parsed.get("resume_gaps", [])),
        }

    def build_keyword_coverage_plan(
        self,
        lines: List[Dict[str, Any]],
        job_description: str,
        ats_analysis: Dict[str, Any],
        line_char_limit: int = 95,
        max_rewrites: int = 14,
        options_per_line: int = 2,
    ) -> List[Dict[str, Any]]:
        editable_lines = [line for line in lines if line.get("editable") and line.get("text")]
        if not editable_lines:
            raise ValueError("No editable resume lines found.")

        target_keywords = ATSUtils.dedupe_keep_order(
            ats_analysis.get("high_priority_missing", []) + ats_analysis.get("medium_priority_missing", [])
        )[:30]
        if not target_keywords:
            return []

        condensed_lines = []
        for line in editable_lines[:120]:
            char_budget = line_char_limit if line["char_count"] <= line_char_limit else line_char_limit * 2
            condensed_lines.append(
                {
                    "index": line["index"],
                    "text": line["text"],
                    "char_budget": char_budget,
                    "char_count": line["char_count"],
                    "likely_date_line": line.get("likely_date_line", False),
                }
            )

        prompt = f"""
You are a professional resume tailoring engine.
Return ONLY valid JSON array.

Goal:
- Maximize truthful ATS keyword coverage.
- Cover as many target keywords as possible.
- Assign multiple keywords to the same line when natural.
- Rewrite only lines where the keyword fit is believable.
- Preserve the resume's layout by respecting per-line char budgets.
- Do NOT rewrite dates, employer names, school names, or lines that are mostly locations/timelines.

Output schema:
[
  {{
    "line_index": 0,
    "original": "",
    "rewrite_options": ["", ""],
    "keywords_targeted": [""],
    "keywords_covered_by_best_option": [""],
    "reason": ""
  }}
]

Rules:
- Return at most {max_rewrites} items.
- rewrite_options must contain 1 or 2 strong options only.
- Each rewrite must be truthful and natural.
- Each rewrite must stay within the listed char_budget for its line.
- Use action-oriented resume language.
- Prioritize missing required keywords first.
- Prefer packing 2 to 5 relevant keywords into one line if natural.
- original must exactly match the provided line text.
- line_index must match the provided line.
- keywords_covered_by_best_option must only list keywords actually present in the first rewrite option.

Target keywords to cover:
{json.dumps(target_keywords, ensure_ascii=False)}

Key job requirements:
{json.dumps(ats_analysis.get('key_requirements', [])[:15], ensure_ascii=False)}

Editable resume lines:
{json.dumps(condensed_lines[:80], ensure_ascii=False)}

Job description:
{job_description[:12000]}
""".strip()
        parsed = self._call_json(prompt, temperature=0.25, max_output_tokens=5000)
        if not isinstance(parsed, list):
            raise ValueError("Coverage plan response was not a JSON array.")

        line_lookup = {line["index"]: line for line in condensed_lines}
        cleaned: List[Dict[str, Any]] = []
        used_lines = set()

        for item in parsed:
            if not isinstance(item, dict):
                continue
            line_index = item.get("line_index")
            if not isinstance(line_index, int) or line_index not in line_lookup or line_index in used_lines:
                continue
            original = item.get("original", "")
            actual = line_lookup[line_index]["text"]
            if ATSUtils.normalize_compare_text(original) != ATSUtils.normalize_compare_text(actual):
                continue
            options = item.get("rewrite_options", [])
            if not isinstance(options, list) or not options:
                continue
            normalized_options = []
            seen = set()
            char_budget = line_lookup[line_index]["char_budget"]
            for option in options[:options_per_line]:
                if not isinstance(option, str) or not option.strip():
                    continue
                clean = option.strip()
                norm = ATSUtils.normalize_compare_text(clean)
                if norm in seen or clean == actual or len(clean) > char_budget:
                    continue
                seen.add(norm)
                normalized_options.append(clean)
            if not normalized_options:
                continue
            hits = ATSUtils.find_keyword_hits(normalized_options[0], target_keywords)
            reason = item.get("reason", "") if isinstance(item.get("reason"), str) else ""
            targeted = ATSUtils.dedupe_keep_order(item.get("keywords_targeted", []))
            cleaned.append(
                {
                    "line_index": line_index,
                    "original": actual,
                    "options": normalized_options,
                    "selected_text": normalized_options[0],
                    "reason": reason,
                    "keywords_targeted": targeted or hits,
                    "keywords_added": hits,
                    "char_budget": char_budget,
                }
            )
            used_lines.add(line_index)

        return cleaned
