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

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


# ─────────────────────────────────────────────────────────────────────────────
class ATSUtils:
    @staticmethod
    def normalize_token(text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\-\+\#/\.& ]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def normalize_compare(text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.strip().lower()
        text = text.replace("\u2013", "-").replace("\u2014", "-")
        text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def dedupe(items: List[str]) -> List[str]:
        seen: set = set()
        out: List[str] = []
        for item in items:
            if not isinstance(item, str):
                continue
            c = item.strip()
            n = ATSUtils.normalize_token(c)
            if c and n and n not in seen:
                seen.add(n)
                out.append(c)
        return out

    @staticmethod
    def keyword_in_text(text: str, keyword: str) -> bool:
        tn = ATSUtils.normalize_token(text)
        kn = ATSUtils.normalize_token(keyword)
        if not tn or not kn:
            return False
        if kn in tn:
            return True
        return bool(set(tn.split()).intersection(set(kn.split())))

    @staticmethod
    def keywords_in_text(text: str, keywords: List[str]) -> List[str]:
        return [kw for kw in keywords if ATSUtils.keyword_in_text(text, kw)]


# ─────────────────────────────────────────────────────────────────────────────
class GeminiClient:
    def __init__(self, api_key: str, resume_processor=None):
        self.api_key = api_key
        self.resume_processor = resume_processor
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def set_resume_processor(self, rp) -> None:
        self.resume_processor = rp

    # ── Raw API call ──────────────────────────────────────────────────────────
    def _call(self, prompt: str, temperature: float = 0.4,
              max_output_tokens: int = 8192) -> str:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
        resp = self.session.post(
            f"{GEMINI_URL}?key={self.api_key}", json=body, timeout=120
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API {resp.status_code}: {resp.text[:600]}")
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            raise RuntimeError(f"Unexpected Gemini response: {data}") from exc

    # ── JSON parsing ──────────────────────────────────────────────────────────
    def _clean_json(self, text: str) -> str:
        t = text.strip()
        t = re.sub(r"```json|```", "", t).strip()
        t = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", t)
        t = t.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
        return t

    def _extract_json(self, text: str) -> Any:
        cleaned = self._clean_json(text)
        # Try direct parse
        for candidate in [cleaned, re.sub(r",\s*([\]}])", r"\1", cleaned)]:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        # Try extracting first JSON block
        m = re.search(r"[{\[]", cleaned)
        if m:
            frag = cleaned[m.start():]
            frag = re.sub(r",\s*([\]}])", r"\1", frag)
            try:
                return json.loads(frag)
            except Exception:
                pass
        raise ValueError(f"JSON parse failed. Raw (first 600 chars):\n{cleaned[:600]}")

    # ── ATS Analysis ──────────────────────────────────────────────────────────
    def analyze_ats(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        prompt = f"""You are a professional ATS (Applicant Tracking System) analyst.
Analyze the resume against the job description and return ONLY valid JSON. No markdown, no explanation.

Required schema — fill EVERY field:
{{
  "ats_score": 42,
  "score_note": "brief explanation",
  "present_keywords": ["keyword already clearly in resume"],
  "missing_keywords": ["every important keyword NOT in the resume"],
  "key_requirements": ["explicit requirements from job description"],
  "required_keywords": ["must-have ATS terms from JD"],
  "preferred_keywords": ["nice-to-have terms from JD"],
  "high_priority_missing": ["8-15 highest-value missing keywords"],
  "medium_priority_missing": ["secondary missing keywords"],
  "low_priority_missing": ["minor missing keywords"],
  "recommended_keyword_targets": ["top 15-20 keywords to add for maximum ATS impact"]
}}

Rules:
- Be COMPREHENSIVE — extract every important keyword from the JD
- high_priority_missing must have 8-15 items minimum
- recommended_keyword_targets must have 15-20 items — these drive the rewrites
- ats_score: honest integer 0-100 based on keyword match
- Do NOT invent requirements not stated in the JD
- De-duplicate all arrays
- Include both exact terms and close variants

RESUME:
{resume_text[:14000]}

JOB DESCRIPTION:
{job_description[:8000]}
""".strip()

        raw = self._call(prompt, temperature=0.15, max_output_tokens=3500)
        parsed = self._extract_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("ATS analysis must return a JSON object.")

        list_keys = [
            "present_keywords", "missing_keywords", "key_requirements",
            "required_keywords", "preferred_keywords", "high_priority_missing",
            "medium_priority_missing", "low_priority_missing", "recommended_keyword_targets",
        ]
        for k in list_keys:
            v = parsed.get(k, [])
            parsed[k] = ATSUtils.dedupe(
                [x for x in (v if isinstance(v, list) else []) if isinstance(x, str) and x.strip()]
            )

        score = parsed.get("ats_score", 0)
        try:
            score = int(score)
        except Exception:
            score = 0
        parsed["ats_score"] = max(0, min(100, score))
        if not isinstance(parsed.get("score_note"), str):
            parsed["score_note"] = ""
        return parsed

    # ── Suggestion Generation ─────────────────────────────────────────────────
    def generate_suggestions(
        self,
        lines: List[Dict[str, Any]],
        job_description: str,
        ats_analysis: Dict[str, Any],
        selected_keywords: Optional[List[str]] = None,
        line_char_limit: int = 90,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        if not lines:
            raise ValueError("No resume lines provided.")

        # Build complete keyword list to place
        all_missing = ATSUtils.dedupe(
            (selected_keywords or [])
            + ats_analysis.get("recommended_keyword_targets", [])
            + ats_analysis.get("high_priority_missing", [])
            + ats_analysis.get("missing_keywords", [])
        )

        # Index lines
        line_map = {
            l["index"]: {
                "text": l["text"],
                "char_count": l.get("char_count", len(l["text"])),
            }
            for l in lines if isinstance(l, dict) and l.get("text", "").strip()
        }

        # Filter candidates: non-trivial lines only
        candidate_lines = [
            l for l in lines
            if isinstance(l, dict)
            and l.get("text", "").strip()
            and len(l.get("text", "").strip()) >= 15
        ]

        # Build prompt and call
        prompt = self._build_suggestion_prompt(
            candidate_lines, all_missing, ats_analysis, job_description, line_char_limit
        )

        raw_suggestions: List[Dict[str, Any]] = []
        last_err = None

        for attempt in range(max_retries):
            try:
                raw = self._call(prompt, temperature=0.35, max_output_tokens=8192)
                parsed = self._extract_json(raw)
                if isinstance(parsed, list):
                    raw_suggestions = parsed
                    break
                elif isinstance(parsed, dict):
                    # Try common wrapper keys
                    for key in ("suggestions", "results", "items", "rewrites"):
                        if isinstance(parsed.get(key), list):
                            raw_suggestions = parsed[key]
                            break
                    if raw_suggestions:
                        break
            except Exception as exc:
                last_err = exc
                if attempt < max_retries - 1:
                    time.sleep(1.5)

        if not raw_suggestions:
            raise ValueError(f"Suggestion generation failed after {max_retries} attempts: {last_err}")

        # Validate and clean
        results: List[Dict[str, Any]] = []
        seen_indices: set = set()

        for item in raw_suggestions:
            if not isinstance(item, dict):
                continue

            li = item.get("line_index")
            if not isinstance(li, int) or li not in line_map or li in seen_indices:
                continue

            actual_text = line_map[li]["text"]
            char_count = line_map[li]["char_count"]

            # Generous budget: allow up to 50% longer than original, min 120
            char_budget = max(int(char_count * 1.5), 120)

            raw_opts = item.get("options", [])
            if not isinstance(raw_opts, list) or not raw_opts:
                continue

            valid_opts: List[str] = []
            seen_opt_norms: set = set()

            for opt in raw_opts:
                if not isinstance(opt, str) or not opt.strip():
                    continue
                opt = opt.strip()
                opt_n = ATSUtils.normalize_compare(opt)

                # Skip identical to original
                if opt_n == ATSUtils.normalize_compare(actual_text):
                    continue
                # Skip duplicates
                if opt_n in seen_opt_norms:
                    continue
                # Skip if way too short (< 35% of original, min 15 chars)
                if len(opt) < max(15, int(char_count * 0.35)):
                    continue
                # Skip if absurdly long (> 300% of original or > 300 chars)
                if len(opt) > max(char_budget, 300):
                    continue

                seen_opt_norms.add(opt_n)
                valid_opts.append(opt)

                if len(valid_opts) == 5:
                    break

            if not valid_opts:
                continue

            # Detect keywords present in options
            all_opts_text = " ".join(valid_opts)
            detected_kws = ATSUtils.keywords_in_text(all_opts_text, all_missing)
            declared_kws = item.get("keywords_added", [])
            if not isinstance(declared_kws, list):
                declared_kws = []
            final_kws = ATSUtils.dedupe(
                [k for k in declared_kws if isinstance(k, str)] + detected_kws
            )

            seen_indices.add(li)
            results.append({
                "line_index": li,
                "original": actual_text,
                "options": valid_opts,
                "reason": str(item.get("reason", "")).strip(),
                "keywords_added": final_kws,
                "char_budget": char_budget,
            })

        results.sort(key=lambda x: x["line_index"])
        return results

    # ── Prompt ────────────────────────────────────────────────────────────────
    def _build_suggestion_prompt(
        self,
        lines: List[Dict[str, Any]],
        keywords: List[str],
        ats_analysis: Dict[str, Any],
        job_description: str,
        line_char_limit: int,
    ) -> str:
        lines_block = "\n".join(
            f'[{l["index"]}] ({len(l.get("text", ""))} chars) {l.get("text", "")}'
            for l in lines if l.get("text", "").strip()
        )
        present = ats_analysis.get("present_keywords", [])
        requirements = ats_analysis.get("key_requirements", [])

        return f"""You are an elite resume tailoring expert and ATS optimization specialist.

YOUR MISSION: Maximize ATS keyword coverage by rewriting resume lines to naturally include as many missing keywords as possible, while keeping every claim 100% truthful.

OUTPUT FORMAT: Return ONLY a valid JSON array. No markdown. No explanation. No trailing commas.

Each array element:
{{
  "line_index": <integer — exact index from the lines below>,
  "original": "<exact copy of the original line text>",
  "options": [
    "rewrite option 1 — vary phrasing",
    "rewrite option 2 — vary structure",
    "rewrite option 3 — vary emphasis",
    "rewrite option 4 — vary active/passive",
    "rewrite option 5 — most keyword-dense natural version"
  ],
  "reason": "which keywords were added and why this line was chosen",
  "keywords_added": ["keyword1", "keyword2"]
}}

═══════════════════════════════════════════════════════
CRITICAL RULES — NEVER VIOLATE THESE:
═══════════════════════════════════════════════════════
1. TRUTHFULNESS: Only add keywords that genuinely apply to the experience described in that line. NEVER add fake tools, certifications, metrics, or technologies.
2. NATURAL LANGUAGE: Keywords must sound like they belong — not forced or stuffed.
3. COVERAGE GOAL: Rewrite as many lines as needed to place ALL missing keywords. Cover 10-20+ lines for a typical resume. Don't stop at 5 or 8.
4. 5 OPTIONS: Each line must have exactly 5 distinct rewrite options (different wording, structure, emphasis).
5. NO FABRICATION: Do not invent numbers, achievements, or technologies not implied by the original.
6. PRESERVE IDENTITY: Keep the same job, company, role, and time period. Only improve phrasing.
7. LINE INTEGRITY: Never merge or split lines. One line in, one rewritten line out.
8. CHARACTER LENGTH: Keep rewrites within 150% of original length. Don't pad unnecessarily.

═══════════════════════════════════════════════════════
KEYWORD STRATEGY:
═══════════════════════════════════════════════════════
Missing keywords to place (priority order):
{json.dumps(keywords[:30], ensure_ascii=False)}

Already in resume (no need to add): {json.dumps(present[:15], ensure_ascii=False)}
Key job requirements: {json.dumps(requirements[:10], ensure_ascii=False)}

For each keyword, find the BEST lines where it could naturally fit and rewrite those lines.
Spread keywords across many different lines — do not put all keywords in one line.

═══════════════════════════════════════════════════════
RESUME LINES (index | char count | text):
═══════════════════════════════════════════════════════
{lines_block[:15000]}

═══════════════════════════════════════════════════════
JOB DESCRIPTION (for context):
═══════════════════════════════════════════════════════
{job_description[:5000]}

Now return the JSON array covering as many lines as possible. Aim to achieve near-100% keyword coverage.
""".strip()
