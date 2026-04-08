"""
resume_processor.py  —  Rizzume v2
Parses DOCX into line-level units and performs precise, format-safe replacement.
"""
from __future__ import annotations

import copy
import io
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


@dataclass
class ResumeLine:
    index: int
    text: str
    char_count: int
    source: str          # "paragraph" | "table"
    para_index: int = -1
    table_ref: Optional[Tuple[int, int, int]] = None
    is_empty: bool = False


class ResumeProcessor:
    """
    Parses a DOCX resume into line-level units and supports precise replacement
    while preserving all formatting (bold, italic, font size, color, etc.).
    """

    def __init__(self, docx_bytes: bytes):
        self._original_bytes = docx_bytes
        self.doc = Document(io.BytesIO(docx_bytes))
        self._lines: List[ResumeLine] = []
        self._line_lookup: Dict[int, Dict[str, Any]] = {}
        self._parse()

    # ── Text cleaning ──────────────────────────────────────────────────────────
    @staticmethod
    def _clean(text: str) -> str:
        if not text:
            return ""
        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n+", "\n", text)
        return text.strip()

    # ── Parsing ────────────────────────────────────────────────────────────────
    def _add_line(self, line: ResumeLine) -> None:
        self._lines.append(line)
        lookup: Dict[str, Any] = {"source": line.source}
        if line.source == "paragraph":
            lookup["para_index"] = line.para_index
        else:
            lookup["table_ref"] = line.table_ref
        self._line_lookup[line.index] = lookup

    def _parse(self) -> None:
        self._lines = []
        self._line_lookup = {}
        idx = 0

        for pi, para in enumerate(self.doc.paragraphs):
            text = self._clean(para.text)
            self._add_line(ResumeLine(
                index=idx, text=text, char_count=len(text),
                source="paragraph", para_index=pi, is_empty=(text == ""),
            ))
            idx += 1

        for ti, table in enumerate(self.doc.tables):
            for ri, row in enumerate(table.rows):
                for ci, cell in enumerate(row.cells):
                    cell_text = "\n".join(
                        self._clean(p.text) for p in cell.paragraphs
                        if self._clean(p.text)
                    )
                    cell_text = self._clean(cell_text)
                    self._add_line(ResumeLine(
                        index=idx, text=cell_text, char_count=len(cell_text),
                        source="table", table_ref=(ti, ri, ci),
                        is_empty=(cell_text == ""),
                    ))
                    idx += 1

    # ── Public accessors ───────────────────────────────────────────────────────
    def get_all_lines(self, include_empty: bool = True) -> List[Dict[str, Any]]:
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

    def get_context_window(self, line_index: int, window: int = 2) -> Dict[str, Any]:
        if not (0 <= line_index < len(self._lines)):
            return {"target": "", "before": [], "after": []}
        start = max(0, line_index - window)
        end = min(len(self._lines), line_index + window + 1)
        return {
            "target": self._lines[line_index].text,
            "before": [self._lines[i].text for i in range(start, line_index)],
            "after": [self._lines[i].text for i in range(line_index + 1, end)],
        }

    # ── Replacement ────────────────────────────────────────────────────────────
    def replace_line(self, line_index: int, new_text: str) -> bool:
        if not (0 <= line_index < len(self._lines)):
            return False

        new_text = self._clean(new_text)
        line = self._lines[line_index]
        lookup = self._line_lookup[line_index]

        if lookup["source"] == "paragraph":
            para = self.doc.paragraphs[lookup["para_index"]]
            self._replace_para_text(para, new_text)
        elif lookup["source"] == "table":
            ti, ri, ci = lookup["table_ref"]
            cell = self.doc.tables[ti].rows[ri].cells[ci]
            self._replace_cell_text(cell, new_text)

        line.text = new_text
        line.char_count = len(new_text)
        line.is_empty = (new_text == "")
        return True

    def _replace_cell_text(self, cell, new_text: str) -> None:
        if cell.paragraphs:
            self._replace_para_text(cell.paragraphs[0], new_text)
            for extra in cell.paragraphs[1:]:
                self._replace_para_text(extra, "")
        else:
            cell.text = new_text

    @staticmethod
    def _replace_para_text(para, new_text: str) -> None:
        """Replace paragraph text, preserving the first meaningful run's formatting."""
        # Find best template run (first non-empty run)
        template_run = None
        for run in para.runs:
            if run.text and run.text.strip():
                template_run = run
                break
        if template_run is None and para.runs:
            template_run = para.runs[0]

        # Clone run properties
        rpr_clone = None
        if template_run is not None:
            rpr = template_run._r.find(qn("w:rPr"))
            if rpr is not None:
                rpr_clone = copy.deepcopy(rpr)

        p_elem = para._p

        # Remove all existing runs
        for child in list(p_elem):
            if child.tag == qn("w:r"):
                p_elem.remove(child)

        # Build new run
        new_run = OxmlElement("w:r")
        if rpr_clone is not None:
            new_run.append(rpr_clone)

        text_elem = OxmlElement("w:t")
        if new_text.startswith(" ") or new_text.endswith(" "):
            text_elem.set(qn("xml:space"), "preserve")
        text_elem.text = new_text
        new_run.append(text_elem)
        p_elem.append(new_run)

    # ── Export ─────────────────────────────────────────────────────────────────
    def export(self) -> bytes:
        buf = io.BytesIO()
        self.doc.save(buf)
        buf.seek(0)
        return buf.getvalue()

    def export_original(self) -> bytes:
        """Return unmodified original bytes."""
        return self._original_bytes
