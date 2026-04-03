
from __future__ import annotations

import io
import copy
import json
import re
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# =========================
# Existing resume processor
# =========================

@dataclass
class ResumeLine:
    index: int
    text: str
    char_count: int
    source: str                  # "paragraph" | "table"
    para_index: int             # paragraph index if source == paragraph
    table_ref: Optional[tuple] = None
    is_empty: bool = False


class ResumeProcessor:
    """
    Parses a DOCX resume into line-level units and supports precise replacement
    while preserving formatting as much as possible.
    """

    def __init__(self, docx_bytes: bytes):
        self._original_bytes = docx_bytes
        self.doc = Document(io.BytesIO(docx_bytes))
        self._lines: List[ResumeLine] = []
        self._line_lookup: Dict[int, Dict[str, Any]] = {}
        self._parse()

    def _parse(self) -> None:
        idx = 0

        for pi, para in enumerate(self.doc.paragraphs):
            text = self._clean_text(para.text)
            self._lines.append(
                ResumeLine(
                    index=idx,
                    text=text,
                    char_count=len(text),
                    source="paragraph",
                    para_index=pi,
                    is_empty=(text == ""),
                )
            )
            self._line_lookup[idx] = {"source": "paragraph", "para_index": pi}
            idx += 1

        for ti, table in enumerate(self.doc.tables):
            for ri, row in enumerate(table.rows):
                for ci, cell in enumerate(row.cells):
                    text = self._clean_text(cell.text)
                    self._lines.append(
                        ResumeLine(
                            index=idx,
                            text=text,
                            char_count=len(text),
                            source="table",
                            para_index=-1,
                            table_ref=(ti, ri, ci),
                            is_empty=(text == ""),
                        )
                    )
                    self._line_lookup[idx] = {
                        "source": "table",
                        "table_ref": (ti, ri, ci),
                    }
                    idx += 1

    method
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def get_all_lines(self, include_empty: bool = True) -> List[dict]:
        lines = self._lines if include_empty else [l for l in self._lines if not l.is_empty]
        return [
            {
                "index": l.index,
                "text": l.text,
                "char_count": l.char_count,
                "source": l.source,
            }
            for l in lines
        ]

    def get_line(self, line_index: int) -> Optional[ResumeLine]:
        if 0 <= line_index < len(self._lines):
            return self._lines[line_index]
        return None

    def get_context_window(self, line_index: int, window: int = 1) -> dict:
        """
        Returns nearby lines so the LLM can match tone/vibe with minimal token use.
        """
        start = max(0, line_index - window)
        end = min(len(self._lines), line_index + window + 1)

        return {
            "target": self._lines[line_index].text if 0 <= line_index < len(self._lines) else "",
            "before": [self._lines[i].text for i in range(start, line_index)],
            "after": [self._lines[i].text for i in range(line_index + 1, end)],
        }

    def replace_line(self, line_index: int, new_text: str) -> bool:
        if not (0 <= line_index < len(self._lines)):
            return False

        new_text = self._clean_text(new_text)
        line = self._lines[line_index]
        lookup = self._line_lookup[line_index]

        if lookup["source"] == "paragraph":
            para = self.doc.paragraphs[lookup["para_index"]]
            self._replace_para_text(para, new_text)

        elif lookup["source"] == "table":
            ti, ri, ci = lookup["table_ref"]
            cell = self.doc.tables[ti].rows[ri].cells[ci]

            if cell.paragraphs:
                self._replace_para_text(cell.paragraphs[0], new_text)
            else:
                cell.text = new_text

        line.text = new_text
        line.char_count = len(new_text)
        line.is_empty = (new_text == "")
        return True

    @staticmethod
    def _replace_para_text(para, new_text: str) -> None:
        """
        Replace paragraph text while preserving the first meaningful run style.
        """
        template_run = None
        for run in para.runs:
            if run.text and run.text.strip():
                template_run = run
                break

        if template_run is None and para.runs:
            template_run = para.runs[0]

        rPr_clone = None
        if template_run is not None:
            rPr = template_run._r.find(qn("w:rPr"))
            if rPr is not None:
                rPr_clone = copy.deepcopy(rPr)

        p_elem = para._p

        # Remove all existing runs
        for child in list(p_elem):
            if child.tag == qn("w:r"):
                p_elem.remove(child)

        # Create one fresh run with preserved styling
        new_run = OxmlElement("w:r")
        if rPr_clone is not None:
            new_run.append(rPr_clone)

        text_elem = OxmlElement("w:t")
        if new_text.startswith(" ") or new_text.endswith(" "):
            text_elem.set(qn("xml:space"), "preserve")
        text_elem.text = new_text

        new_run.append(text_elem)
        p_elem.append(new_run)

    def export(self) -> bytes:
        output = io.BytesIO()
        self.doc.save(output)
        output.seek(0)
        return output.getvalue()


# =========================
# Production-ready ATS layer
# =========================

@dataclass
class JDAnalysis:
    core_role_function: str = ""
    primary_business_objective: str = ""
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    required_domain_terms: List[str] = field(default_factory=list)
    required_responsibilities: List[str] = field(default_factory=list)
    required_qualifications: List[str] = field(default_factory=list)
    preferred_qualifications: List[str] = field(default_factory=list)
    repeated_keywords: List[str] = field(default_factory=list)
    synonyms_and_variants: Dict[str, List[str]] = field(default_factory=dict)
    implied_screening_signals: List[str] = field(default_factory=list)
    metrics_kpi_language: List[str] = field(default_factory=list)
    ats_critical_terms: List[str] = field(default_factory=list)


@dataclass
class LineAssessment:
    relevance: str = "low"
    current_match_score: int = 0
    issues: List[str] = field(default_factory=list)


@dataclass
class RewriteOption:
    text: str
    keywords_added: List[str] = field(default_factory=list)
    score: int = 0
    why_it_works: str = ""


@dataclass
class LineSuggestion:
    line_index: int
    original: str
    assessment: LineAssessment
    options: List[RewriteOption] = field(default_factory=list)
    best_option_number: int = 1
    best_option_reason: str = ""
    risk_flags: List[str] = field(default_factory=list)


@dataclass
class GlobalResumeFeedback:
    rewrite_based_improvements: List[str] = field(default_factory=list)
    substantive_gaps: List[str] = field(default_factory=list)
    parser_risks: List[str] = field(default_factory=list)
    overall_estimated_match_score: int = 0
    what_prevents_true_100_percent_match: List[str] = field(default_factory=list)


@dataclass
class ATSReviewBundle:
    jd_analysis: JDAnalysis
    line_suggestions: List[LineSuggestion]
    global_resume_feedback: GlobalResumeFeedback


class ATSUtils:
    """Shared utilities for safe JSON parsing, token cleanup, and text normalization."""

    COMMON_PARSER_RISKS = [
        "text boxes and floating elements may not parse correctly",
        "graphics, icons, and image-based text are often ignored by ATS",
        "tables with complex merged cells can hurt parsing",
        "headers/footers may be skipped by some systems",
        "non-standard section names can weaken ATS extraction",
        "multi-column layouts can cause reading-order issues",
    ]

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    @staticmethod
    def normalize_token(token: str) -> str:
        token = ATSUtils.clean_text(token).lower()
        token = re.sub(r"[^a-z0-9+/&().# -]", "", token)
        return token.strip()

    @staticmethod
    def dedupe_keep_order(items: List[str]) -> List[str]:
        seen = set()
        output = []
        for item in items:
            key = ATSUtils.normalize_token(item)
            if key and key not in seen:
                seen.add(key)
                output.append(ATSUtils.clean_text(item))
        return output

    @staticmethod
    def safe_parse_json(raw: str) -> Any:
        """
        More forgiving JSON parser for model outputs.
        Handles:
        - code fences
        - trailing commas
        - smart quotes
        """
        if raw is None:
            raise ValueError("Empty model output")

        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = cleaned.replace("“", '"').replace("”", '"').replace("’", "'")
        cleaned = re.sub(r",(\s*[\]}])", r"\1", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON parse failed: {exc}") from exc

    @staticmethod
    def find_keyword_hits(text: str, keywords: List[str]) -> List[str]:
        normalized_text = ATSUtils.normalize_token(text)
        hits = []
        for kw in keywords:
            nkw = ATSUtils.normalize_token(kw)
            if nkw and nkw in normalized_text:
                hits.append(kw)
        return ATSUtils.dedupe_keep_order(hits)

    @staticmethod
    def pretty_json(data: Any) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False)


class ATSScorer:
    """
    Lightweight heuristic scorer. This does NOT replace an LLM's reasoning,
    but it gives you deterministic scoring and ranking on top of model outputs.
    """

    WEIGHTS = {
        "keyword_relevance": 30,
        "truthfulness": 20,
        "tool_alignment": 15,
        "readability": 10,
        "specificity": 10,
        "parser_friendliness": 10,
        "length_control": 5,
    }

    @staticmethod
    def assess_line_relevance(line_text: str, jd: JDAnalysis) -> LineAssessment:
        text = ATSUtils.clean_text(line_text)
        if not text:
            return LineAssessment(relevance="low", current_match_score=0, issues=["empty line"])

        critical = jd.ats_critical_terms or []
        tools = jd.required_tools or []
        skills = jd.required_skills or []
        responsibilities = jd.required_responsibilities or []

        all_terms = ATSUtils.dedupe_keep_order(critical + tools + skills + responsibilities)
        hits = ATSUtils.find_keyword_hits(text, all_terms)

        score = min(100, int((len(hits) / max(1, min(len(all_terms), 10))) * 100))
        if score >= 65:
            relevance = "high"
        elif score >= 30:
            relevance = "medium"
        else:
            relevance = "low"

        issues = []
        if not hits:
            issues.append("missing obvious JD-aligned terminology")
        if len(text) < 25:
            issues.append("line may be too short to communicate scope or impact")
        if not re.search(r"\d", text):
            issues.append("no measurable detail present")
        if len(text.split()) < 4:
            issues.append("low specificity")

        return LineAssessment(
            relevance=relevance,
            current_match_score=score,
            issues=ATSUtils.dedupe_keep_order(issues),
        )

@staticmethod
def score_rewrite_option(
    original: str,
    option: str,
    jd: JDAnalysis,
    max_chars: Optional[int] = None,
    selected_keywords: Optional[List[str]] = None,
) -> int:
    text = ATSUtils.clean_text(option)
    original_text = ATSUtils.clean_text(original)
    selected_keywords = selected_keywords or []

    critical_terms = ATSUtils.dedupe_keep_order(
        jd.ats_critical_terms + jd.required_tools + jd.required_skills + jd.required_domain_terms
    )
    critical_hits = ATSUtils.find_keyword_hits(text, critical_terms)
    keyword_score = min(20, len(critical_hits) * 3)

    selected_hits = ATSUtils.find_keyword_hits(text, selected_keywords)
    selected_keyword_score = min(25, len(selected_hits) * 5)

    truthfulness_score = ATSScorer.WEIGHTS["truthfulness"]
    if len(text) > max(40, len(original_text) * 2.2):
        truthfulness_score -= 4
    if text.count(";") > 1:
        truthfulness_score -= 2

    tool_hits = ATSUtils.find_keyword_hits(text, jd.required_tools)
    tool_score = min(ATSScorer.WEIGHTS["tool_alignment"], len(tool_hits) * 5)

    readability_score = ATSScorer.WEIGHTS["readability"]
    if len(text.split()) < 4 or len(text.split()) > 35:
        readability_score -= 3
    if re.search(r"\b(results-driven|dynamic|synergy|go-getter|hardworking)\b", text, flags=re.I):
        readability_score -= 3

    specificity_score = ATSScorer.WEIGHTS["specificity"]
    if not re.search(r"\d", text):
        specificity_score -= 4
    if len(text.split()) < 5:
        specificity_score -= 2

    parser_score = ATSScorer.WEIGHTS["parser_friendliness"]
    if re.search(r"[|¦•►◆■✔]", text):
        parser_score -= 4

    selected_norm = {ATSUtils.normalize_token(k) for k in selected_keywords}
    non_selected_hits = [
        kw for kw in ATSUtils.find_keyword_hits(text, jd.ats_critical_terms)
        if ATSUtils.normalize_token(kw) not in selected_norm
    ]
    if non_selected_hits:
        parser_score -= min(5, len(non_selected_hits))

    length_score = ATSScorer.WEIGHTS["length_control"]
    if max_chars is not None and len(text) > max_chars:
        length_score = max(0, length_score - 5)

    total = (
        keyword_score
        + selected_keyword_score
        + max(0, truthfulness_score)
        + tool_score
        + max(0, readability_score)
        + max(0, specificity_score)
        + max(0, parser_score)
        + max(0, length_score)
    )
    return max(0, min(100, int(total)))


class ResumeRewritePrompts:
    """
    Best-in-class ATS prompts:
    - deep JD parse
    - single-line rewrite
    - best option selector
    """

    @staticmethod
    def build_master_ats_prompt(
        resume_lines: List[Dict[str, Any]],
        job_description: str,
    ) -> str:
        return f"""
You are an elite resume-job description matching engine built to maximize ATS alignment while staying 100% truthful.

Your job is to analyze the full job description with extreme care, identify every assessable hiring signal, compare it against the candidate's resume line by line, and generate optimized resume suggestions that maximize ATS match quality.

PRIMARY GOAL
Produce the strongest possible ATS-aligned suggestions while preserving truth, clarity, formatting intent, and natural human resume language.

NON-NEGOTIABLE RULES
1. Never invent experience, tools, certifications, metrics, industries, leadership, scope, or outcomes not supported by the resume.
2. Never exaggerate beyond what the original line can reasonably support.
3. Keep suggestions natural, concise, recruiter-friendly, and resume-appropriate.
4. Optimize for both ATS parsing and recruiter readability.
5. Treat every word in the job description as potentially important.
6. Scan the ENTIRE job description carefully, including:
   - title
   - summary
   - responsibilities
   - required qualifications
   - preferred qualifications
   - must-have skills
   - nice-to-have skills
   - tools/platforms/systems
   - certifications
   - education requirements
   - industry/domain language
   - measurable expectations
   - hidden screening signals
   - repeated phrases
   - wording in the company description if relevant
7. Prioritize exact-match terminology when truthful and natural.
8. Preserve the candidate's original meaning unless a stronger truthful phrasing exists.
9. Keep bullet length close to original unless a stronger result requires a slight increase.
10. Avoid generic buzzwords unless they are explicitly valuable for ATS matching.

HOW ATS SYSTEMS TYPICALLY ASSESS CANDIDATES
You must account for all of the following:
- exact keyword match
- semantic keyword match
- job title alignment
- skill match
- hard tool match
- domain match
- industry match
- function match
- years/level alignment if inferable
- education alignment
- certification alignment
- action verb strength
- measurable outcomes
- scope/ownership
- recency/relevance of experience
- synonyms and alternate phrasing
- acronym + expanded form coverage
- location/work authorization signals if provided
- required vs preferred qualification coverage
- ATS parsing friendliness
- section labeling clarity
- chronology consistency
- spelling normalization
- formatting that avoids parser failure
- density of relevant terminology without keyword stuffing

Also identify:
A. Missing required qualifications that cannot be solved by rewriting
B. Missing preferred qualifications
C. Missing tools/systems
D. Missing domain experience
E. Potential screening blockers
F. Formatting/parser risks

IMPORTANT
Do NOT claim “100% ATS match” unless the resume genuinely covers the JD’s requirements.
Instead:
- maximize attainable match
- identify the real gaps
- suggest the best truthful improvements
- clearly separate “rewrite fixes” from “actual missing qualifications”

FINAL OUTPUT FORMAT
Return ONLY valid JSON in this structure:

{{
  "jd_analysis": {{
    "core_role_function": "",
    "primary_business_objective": "",
    "required_skills": [],
    "preferred_skills": [],
    "required_tools": [],
    "required_domain_terms": [],
    "required_responsibilities": [],
    "required_qualifications": [],
    "preferred_qualifications": [],
    "repeated_keywords": [],
    "synonyms_and_variants": {{}},
    "implied_screening_signals": [],
    "metrics_kpi_language": [],
    "ats_critical_terms": []
  }},
  "line_suggestions": [
    {{
      "line_index": 0,
      "original": "",
      "assessment": {{
        "relevance": "high|medium|low",
        "current_match_score": 0,
        "issues": []
      }},
      "options": [
        {{
          "text": "",
          "keywords_added": [],
          "score": 0,
          "why_it_works": ""
        }}
      ],
      "best_option_number": 1,
      "best_option_reason": "",
      "risk_flags": []
    }}
  ],
  "global_resume_feedback": {{
    "rewrite_based_improvements": [],
    "substantive_gaps": [],
    "parser_risks": [],
    "overall_estimated_match_score": 0,
    "what_prevents_true_100_percent_match": []
  }}
}}

Resume lines:
{json.dumps(resume_lines, ensure_ascii=False)}

Job description:
{job_description}
""".strip()

    @staticmethod
    def build_jd_deep_parse_prompt(job_description: str) -> str:
        return f"""
Extract ATS-critical hiring signals from this job description.

Analyze the full JD carefully and return structured output covering:
- exact hard skills
- tools/software/platforms
- certifications
- education requirements
- domain/industry phrases
- responsibilities
- metrics/KPI/process language
- repeated keywords
- synonyms and alternate keyword forms
- implied screening signals
- must-have vs nice-to-have distinction

Rules:
- prioritize hard skills, tools, systems, technical/business methods, domain terms, and repeated phrases
- include exact wording from the JD where important
- include acronyms and expanded forms when relevant
- avoid generic soft skills unless clearly repeated or used as a hiring filter
- merge duplicates but preserve important variants
- identify terms that are likely ATS-critical
- return ONLY valid JSON

Rank all extracted JD keywords by ATS importance and return:
- required_keywords
- preferred_keywords
- high_priority_missing
- medium_priority_missing
- low_priority_missing
- recommended_keyword_targets

Recommended keyword targets should be the best truthful terms to prioritize first in rewrites.
Format:
{
  "core_role_function": "",
  "primary_business_objective": "",
  "required_skills": [],
  "preferred_skills": [],
  "required_tools": [],
  "required_domain_terms": [],
  "required_responsibilities": [],
  "required_qualifications": [],
  "preferred_qualifications": [],
  "repeated_keywords": [],
  "synonyms_and_variants": {
    "keyword_from_jd": ["variant1", "variant2"]
  },
  "implied_screening_signals": [],
  "metrics_kpi_language": [],
  "ats_critical_terms": [],
  "required_keywords": [],
  "preferred_keywords": [],
  "high_priority_missing": [],
  "medium_priority_missing": [],
  "low_priority_missing": [],
  "recommended_keyword_targets": []
}

Job description:
{job_description}
""".strip()

@staticmethod
def build_line_rewrite_prompt(
    line_index: int,
    original_line: str,
    job_description: str,
    selected_keywords: Optional[List[str]] = None,
    surrounding_before: Optional[List[str]] = None,
    surrounding_after: Optional[List[str]] = None,
    max_chars: Optional[int] = None,
    n_options: int = 3,
) -> str:
    surrounding_before = surrounding_before or []
    surrounding_after = surrounding_after or []
    selected_keywords = selected_keywords or []

    char_rule = f"Keep length <= {max_chars} chars." if max_chars else "Keep length close to original."
    options_schema = ",\n".join([
        """    {
      "text": "",
      "keywords_added": [],
      "score": 0,
      "why_it_works": ""
    }""" for _ in range(n_options)
    ])

    return f"""
Rewrite this single resume line to maximize truthful ATS alignment.

CRITICAL RULES
1. Use ONLY keywords from the SELECTED KEYWORDS list when adding ATS language.
2. Do not add any keyword unless it fits truthfully.
3. Do not invent tools, certifications, metrics, industries, scope, or outcomes.
4. Prefer exact selected keyword phrases where natural.
5. If none of the selected keywords fit, return conservative rewrites and explain that.
6. Avoid keyword stuffing and AI-sounding phrasing.
7. Preserve original meaning and resume tone.
8. {char_rule}

Evaluate this line against:
- exact keyword match
- hard skill match
- tool/system match
- responsibility match
- domain match
- action/result strength
- ATS parser readability

Return ONLY valid JSON:
{{
  "line_index": {line_index},
  "original": {json.dumps(original_line, ensure_ascii=False)},
  "analysis": {{
    "selected_keywords_considered": {json.dumps(selected_keywords, ensure_ascii=False)},
    "selected_keywords_used": [],
    "selected_keywords_not_used": [],
    "main_gap": "",
    "risk_of_overclaiming": []
  }},
  "options": [
{options_schema}
  ]
}}

Context before: {json.dumps(surrounding_before, ensure_ascii=False)}
Target line: {json.dumps(original_line, ensure_ascii=False)}
Context after: {json.dumps(surrounding_after, ensure_ascii=False)}

SELECTED KEYWORDS:
{json.dumps(selected_keywords, ensure_ascii=False)}

Job description:
{job_description}
""".strip()

    @staticmethod
    def build_best_option_selector_prompt(
        original_line: str,
        options: List[str],
        max_chars: Optional[int] = None,
    ) -> str:
        options_block = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
        char_rule = f"Stay within {max_chars} characters if possible." if max_chars else "Keep the length close to the original."

        return f"""
Choose the best rewritten resume line.

Scoring criteria:
- truthful to original
- strongest ATS keyword alignment
- strongest hard skill/tool alignment
- best recruiter readability
- concise and natural
- no keyword stuffing
- best resume style fit
- best balance of precision and impact

Reject any option that:
- sounds robotic
- overclaims
- feels stuffed with keywords
- changes the meaning too much

{char_rule}

Return ONLY valid JSON:
{{
  "best_option_number": 1,
  "reason": "",
  "rejected_option_notes": {{
    "2": "",
    "3": ""
  }}
}}

Original:
{original_line}

Options:
{options_block}
""".strip()


class ATSReviewEngine:
    """
    Orchestrates a 5-pass pipeline:

    1. JD deep parse
    2. Resume line relevance scoring
    3. Line rewrite generation
    4. Best-option selection
    5. Global gap + parser-risk audit

    This class is LLM-provider agnostic. Pass your model outputs into the
    parse_* helpers, and use the scorer to rank options deterministically.
    """

    def __init__(self, processor: ResumeProcessor):
        self.processor = processor

    def build_jd_parse_prompt(self, job_description: str) -> str:
        return ResumeRewritePrompts.build_jd_deep_parse_prompt(job_description)

    def parse_jd_analysis(self, raw_model_output: str) -> JDAnalysis:
        data = ATSUtils.safe_parse_json(raw_model_output)
        return JDAnalysis(
            core_role_function=data.get("core_role_function", ""),
            primary_business_objective=data.get("primary_business_objective", ""),
            required_skills=ATSUtils.dedupe_keep_order(data.get("required_skills", [])),
            preferred_skills=ATSUtils.dedupe_keep_order(data.get("preferred_skills", [])),
            required_tools=ATSUtils.dedupe_keep_order(data.get("required_tools", [])),
            required_domain_terms=ATSUtils.dedupe_keep_order(data.get("required_domain_terms", [])),
            required_responsibilities=ATSUtils.dedupe_keep_order(data.get("required_responsibilities", [])),
            required_qualifications=ATSUtils.dedupe_keep_order(data.get("required_qualifications", [])),
            preferred_qualifications=ATSUtils.dedupe_keep_order(data.get("preferred_qualifications", [])),
            repeated_keywords=ATSUtils.dedupe_keep_order(data.get("repeated_keywords", [])),
            synonyms_and_variants=data.get("synonyms_and_variants", {}) or {},
            implied_screening_signals=ATSUtils.dedupe_keep_order(data.get("implied_screening_signals", [])),
            metrics_kpi_language=ATSUtils.dedupe_keep_order(data.get("metrics_kpi_language", [])),
            ats_critical_terms=ATSUtils.dedupe_keep_order(data.get("ats_critical_terms", [])),
        )

    def get_relevant_lines(self, jd: JDAnalysis, include_low: bool = False) -> List[LineSuggestion]:
        suggestions: List[LineSuggestion] = []
        for line in self.processor.get_all_lines(include_empty=False):
            assessment = ATSScorer.assess_line_relevance(line["text"], jd)
            if include_low or assessment.relevance in {"medium", "high"}:
                suggestions.append(
                    LineSuggestion(
                        line_index=line["index"],
                        original=line["text"],
                        assessment=assessment,
                    )
                )
        return suggestions

def build_line_prompt(
    self,
    line_index: int,
    job_description: str,
    jd: JDAnalysis,
    selected_keywords: Optional[List[str]] = None,
) -> str:
    line = self.processor.get_line(line_index)
    if line is None:
        raise IndexError(f"Invalid line_index: {line_index}")

    context = self.processor.get_context_window(line_index, window=1)
    return ResumeRewritePrompts.build_line_rewrite_prompt(
        line_index=line_index,
        original_line=line.text,
        job_description=job_description,
        selected_keywords=selected_keywords or [],
        surrounding_before=context.get("before", []),
        surrounding_after=context.get("after", []),
        max_chars=max(line.char_count + 20, int(line.char_count * 1.3)),
    )

def parse_line_options(
    self,
    raw_model_output: str,
    jd: JDAnalysis,
    original_line: str,
    max_chars: Optional[int] = None,
    selected_keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
        data = ATSUtils.safe_parse_json(raw_model_output)
        options = []
        for option in data.get("options", []):
            text = ATSUtils.clean_text(option.get("text", ""))
            if not text:
                continue
score = ATSScorer.score_rewrite_option(
    original=original_line,
    option=text,
    jd=jd,
    max_chars=max_chars,
    selected_keywords=selected_keywords or [],
)
            options.append(
                RewriteOption(
                    text=text,
                    keywords_added=ATSUtils.dedupe_keep_order(option.get("keywords_added", [])),
                    score=score,
                    why_it_works=option.get("why_it_works", ""),
                )
            )
        return {
            "line_index": data.get("line_index"),
            "original": data.get("original", original_line),
            "analysis": data.get("analysis", {}),
            "options": options,
        }

    def choose_best_option(self, original_line: str, options: List[RewriteOption]) -> Dict[str, Any]:
        if not options:
            return {
                "best_option_number": 1,
                "reason": "No valid options returned.",
                "rejected_option_notes": {},
            }

        ranked = sorted(enumerate(options, start=1), key=lambda x: x[1].score, reverse=True)
        best_num, best_obj = ranked[0]
        rejected = {}
        for idx, obj in ranked[1:]:
            rejected[str(idx)] = f"Lower score ({obj.score}) than best option ({best_obj.score})."

        return {
            "best_option_number": best_num,
            "reason": f"Best blend of ATS alignment, truthfulness, and readability with score {best_obj.score}.",
            "rejected_option_notes": rejected,
        }

    def build_master_prompt(self, job_description: str) -> str:
        return ResumeRewritePrompts.build_master_ats_prompt(
            resume_lines=self.processor.get_all_lines(include_empty=False),
            job_description=job_description,
        )

    def build_global_feedback(self, jd: JDAnalysis, reviewed_lines: List[LineSuggestion]) -> GlobalResumeFeedback:
        scores = [s.assessment.current_match_score for s in reviewed_lines]
        overall = int(sum(scores) / len(scores)) if scores else 0

        rewrite_based_improvements = [
            "Align summary section with the exact job family and function.",
            "Mirror required tools and process language in the skills section where truthful.",
            "Strengthen bullets using action + method + result structure.",
            "Add exact JD terminology where naturally supported by the experience.",
        ]

        substantive_gaps = []
        parser_risks = ATSUtils.COMMON_PARSER_RISKS.copy()

        if jd.required_tools:
            substantive_gaps.append(
                f"Verify actual experience with required tools: {', '.join(jd.required_tools[:8])}."
            )
        if jd.required_qualifications:
            substantive_gaps.append(
                f"Check coverage of required qualifications: {', '.join(jd.required_qualifications[:6])}."
            )

        blockers = []
        if jd.required_qualifications:
            blockers.append("missing required qualifications cannot be solved by rewriting alone")
        if jd.required_tools:
            blockers.append("missing required tools or systems cannot be claimed without real experience")
        blockers.append("ATS match varies by employer system and weighting logic")

        return GlobalResumeFeedback(
            rewrite_based_improvements=ATSUtils.dedupe_keep_order(rewrite_based_improvements),
            substantive_gaps=ATSUtils.dedupe_keep_order(substantive_gaps),
            parser_risks=ATSUtils.dedupe_keep_order(parser_risks),
            overall_estimated_match_score=overall,
            what_prevents_true_100_percent_match=ATSUtils.dedupe_keep_order(blockers),
        )

    def export_review_bundle(self, bundle: ATSReviewBundle) -> Dict[str, Any]:
        return {
            "jd_analysis": asdict(bundle.jd_analysis),
            "line_suggestions": [asdict(item) for item in bundle.line_suggestions],
            "global_resume_feedback": asdict(bundle.global_resume_feedback),
        }


# =========================
# Example usage
# =========================

EXAMPLE_USAGE = r"""
# 1) Load DOCX bytes into ResumeProcessor
with open("resume.docx", "rb") as f:
    processor = ResumeProcessor(f.read())

engine = ATSReviewEngine(processor)

# 2) Build JD parse prompt and send to your LLM
jd_prompt = engine.build_jd_parse_prompt(job_description)

# 3) Parse the model's JSON response
jd = engine.parse_jd_analysis(jd_model_output)

# 4) Find relevant lines
relevant_lines = engine.get_relevant_lines(jd)

# 5) For each relevant line, ask the model for rewrites
for suggestion in relevant_lines:
    prompt = engine.build_line_prompt(suggestion.line_index, job_description, jd)
    # send prompt to model...
    parsed = engine.parse_line_options(
        raw_model_output=line_model_output,
        jd=jd,
        original_line=suggestion.original,
        max_chars=max(len(suggestion.original) + 20, int(len(suggestion.original) * 1.3)),
    )
    suggestion.options = parsed["options"]

    best = engine.choose_best_option(suggestion.original, suggestion.options)
    suggestion.best_option_number = best["best_option_number"]
    suggestion.best_option_reason = best["reason"]

# 6) Build global feedback and export JSON
feedback = engine.build_global_feedback(jd, relevant_lines)
bundle = ATSReviewBundle(
    jd_analysis=jd,
    line_suggestions=relevant_lines,
    global_resume_feedback=feedback,
)

result_json = engine.export_review_bundle(bundle)
print(json.dumps(result_json, indent=2))
"""

if __name__ == "__main__":
    print("Enhanced ATS resume processor loaded.")
