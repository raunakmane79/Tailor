from __future__ import annotations

import copy
import io
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


@dataclass
class ResumeLine:
    index: int
    text: str
    char_count: int
    source: str  # paragraph | table
    para_index: int = -1
    table_ref: Optional[Tuple[int, int, int]] = None
    is_empty: bool = False


class ResumeProcessor:
    """Line-level DOCX parser with layout-safe replacement helpers."""

    def __init__(self, docx_bytes: bytes):
        self._original_bytes = docx_bytes
        self.doc = Document(io.BytesIO(docx_bytes))
        self._lines: List[ResumeLine] = []
        self._line_lookup: Dict[int, Dict[str, Any]] = {}
        self._parse()

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        text = text.replace("\xa0", " ")
        text = text.replace("•", "• ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\s*\n\s*", "\n", text)
        text = re.sub(r"\n+", "\n", text)
        return text.strip()

    @staticmethod
    def _looks_like_heading(text: str) -> bool:
        if not text:
            return False
        bare = re.sub(r"[^A-Za-z ]+", "", text).strip()
        if not bare:
            return False
        words = bare.split()
        return len(words) <= 4 and bare.upper() == bare and len(bare) <= 40

    @staticmethod
    def _looks_like_contact_line(text: str) -> bool:
        return bool(re.search(r"@|linkedin|github|\+\d|\bTX\b|\bCA\b|\bNY\b|www\.", text, re.I))

    @staticmethod
    def _looks_like_date_or_location(text: str) -> bool:
        return bool(
            re.search(
                r"\b(20\d{2}|19\d{2}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Present|Remote)\b",
                text,
                re.I,
            )
        )

    @staticmethod
    def _is_probably_editable_content(text: str) -> bool:
        if not text:
            return False
        if len(text) < 18:
            return False
        if ResumeProcessor._looks_like_heading(text):
            return False
        if ResumeProcessor._looks_like_contact_line(text):
            return False
        if text.count("|") >= 2 and len(text) < 120:
            return False
        return True

    def _add_line(self, line: ResumeLine) -> None:
        self._lines.append(line)
        entry: Dict[str, Any] = {"source": line.source}
        if line.source == "paragraph":
            entry["para_index"] = line.para_index
        else:
            entry["table_ref"] = line.table_ref
        self._line_lookup[line.index] = entry

    def _parse(self) -> None:
        self._lines = []
        self._line_lookup = {}
        idx = 0

        for para_index, para in enumerate(self.doc.paragraphs):
            text = self._clean_text(para.text)
            self._add_line(
                ResumeLine(
                    index=idx,
                    text=text,
                    char_count=len(text),
                    source="paragraph",
                    para_index=para_index,
                    is_empty=(text == ""),
                )
            )
            idx += 1

        for table_index, table in enumerate(self.doc.tables):
            for row_index, row in enumerate(table.rows):
                for cell_index, cell in enumerate(row.cells):
                    cell_text = "\n".join(
                        self._clean_text(p.text)
                        for p in cell.paragraphs
                        if self._clean_text(p.text)
                    )
                    cell_text = self._clean_text(cell_text)
                    self._add_line(
                        ResumeLine(
                            index=idx,
                            text=cell_text,
                            char_count=len(cell_text),
                            source="table",
                            table_ref=(table_index, row_index, cell_index),
                            is_empty=(cell_text == ""),
                        )
                    )
                    idx += 1

    def get_all_lines(self, include_empty: bool = True) -> List[Dict[str, Any]]:
        lines = self._lines if include_empty else [line for line in self._lines if not line.is_empty]
        payload = []
        for line in lines:
            payload.append(
                {
                    "index": line.index,
                    "text": line.text,
                    "char_count": line.char_count,
                    "source": line.source,
                    "editable": self._is_probably_editable_content(line.text),
                    "likely_date_line": self._looks_like_date_or_location(line.text),
                }
            )
        return payload

    def get_editable_lines(self) -> List[Dict[str, Any]]:
        return [line for line in self.get_all_lines(include_empty=False) if line["editable"]]

    def get_line(self, line_index: int) -> Optional[ResumeLine]:
        if 0 <= line_index < len(self._lines):
            return self._lines[line_index]
        return None

    def get_context_window(self, line_index: int, window: int = 1) -> Dict[str, Any]:
        if not (0 <= line_index < len(self._lines)):
            return {"target": "", "before": [], "after": []}

        start = max(0, line_index - window)
        end = min(len(self._lines), line_index + window + 1)
        return {
            "target": self._lines[line_index].text,
            "before": [self._lines[i].text for i in range(start, line_index) if self._lines[i].text],
            "after": [self._lines[i].text for i in range(line_index + 1, end) if self._lines[i].text],
        }

    def replace_line(self, line_index: int, new_text: str) -> bool:
        if not (0 <= line_index < len(self._lines)):
            return False

        line = self._lines[line_index]
        new_text = self._clean_text(new_text)
        lookup = self._line_lookup[line_index]

        if lookup["source"] == "paragraph":
            para = self.doc.paragraphs[lookup["para_index"]]
            self._replace_paragraph_text(para, new_text)
        else:
            table_index, row_index, cell_index = lookup["table_ref"]
            cell = self.doc.tables[table_index].rows[row_index].cells[cell_index]
            self._replace_cell_text(cell, new_text)

        line.text = new_text
        line.char_count = len(new_text)
        line.is_empty = (new_text == "")
        return True

    def apply_rewrites(self, rewrites: List[Dict[str, Any]]) -> None:
        for item in rewrites:
            if not isinstance(item, dict):
                continue
            line_index = item.get("line_index")
            replacement = item.get("selected_text") or item.get("rewrite") or item.get("new_text")
            if isinstance(line_index, int) and isinstance(replacement, str) and replacement.strip():
                self.replace_line(line_index, replacement)

    def _replace_cell_text(self, cell, new_text: str) -> None:
        if not cell.paragraphs:
            cell.text = new_text
            return

        first_para = cell.paragraphs[0]
        self._replace_paragraph_text(first_para, new_text)
        for extra in cell.paragraphs[1:]:
            self._replace_paragraph_text(extra, "")

    @staticmethod
    def _replace_paragraph_text(para, new_text: str) -> None:
        template_run = None
        for run in para.runs:
            if run.text and run.text.strip():
                template_run = run
                break
        if template_run is None and para.runs:
            template_run = para.runs[0]

        rpr_clone = None
        if template_run is not None:
            rpr = template_run._r.find(qn("w:rPr"))
            if rpr is not None:
                rpr_clone = copy.deepcopy(rpr)

        p_elem = para._p
        for child in list(p_elem):
            if child.tag == qn("w:r"):
                p_elem.remove(child)

        new_run = OxmlElement("w:r")
        if rpr_clone is not None:
            new_run.append(rpr_clone)

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
