"""
resume_processor.py
────────────────────
Parses a .docx resume into a flat list of "lines" (each paragraph + each
table cell is a line).  Tracks character counts.  Replaces text in-place
while preserving ALL formatting (fonts, bold/italic, sizes, spacing, etc.)
by operating at the Run level rather than overwriting the whole paragraph.
"""

from __future__ import annotations
import io
import copy
from dataclasses import dataclass, field
from typing import List, Optional

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
# lxml is used internally by python-docx; no direct import needed


@dataclass
class ResumeLine:
    index: int           # global sequential index
    text: str            # full text of the line
    char_count: int      # len(text)
    source: str          # "paragraph" | "table"
    para_index: int      # index in doc.paragraphs (for paragraphs)
    table_ref: Optional[tuple] = None   # (table_idx, row_idx, cell_idx) for table cells


class ResumeProcessor:
    def __init__(self, docx_bytes: bytes):
        self._original_bytes = docx_bytes
        self.doc = Document(io.BytesIO(docx_bytes))
        self._lines: List[ResumeLine] = []
        self._para_map: dict[int, int] = {}   # line_index → doc.paragraphs index
        self._table_map: dict[int, tuple] = {}  # line_index → (t, r, c)
        self._parse()

    # ── Parsing ──────────────────────────────────────────────────────────────

    def _parse(self):
        idx = 0

        # 1. All body paragraphs
        for pi, para in enumerate(self.doc.paragraphs):
            text = para.text
            self._lines.append(ResumeLine(
                index=idx,
                text=text,
                char_count=len(text),
                source="paragraph",
                para_index=pi,
            ))
            self._para_map[idx] = pi
            idx += 1

        # 2. All table cells (in document order)
        for ti, table in enumerate(self.doc.tables):
            for ri, row in enumerate(table.rows):
                for ci, cell in enumerate(row.cells):
                    text = cell.text.strip()
                    self._lines.append(ResumeLine(
                        index=idx,
                        text=text,
                        char_count=len(text),
                        source="table",
                        para_index=-1,
                        table_ref=(ti, ri, ci),
                    ))
                    self._table_map[idx] = (ti, ri, ci)
                    idx += 1

    def get_all_lines(self) -> List[dict]:
        return [
            {"index": l.index, "text": l.text, "char_count": l.char_count, "source": l.source}
            for l in self._lines
        ]

    # ── Format-safe replacement ───────────────────────────────────────────────

    def replace_line(self, line_index: int, new_text: str):
        """
        Replace the text of a line while preserving all formatting.

        Strategy:
        - For paragraphs: find the paragraph, clone the formatting of the
          first non-empty run, clear all runs, then write new_text into a
          single new run with that formatting.
        - For table cells: same approach on the first paragraph of the cell.
        """
        if line_index >= len(self._lines):
            return

        line = self._lines[line_index]

        if line.source == "paragraph":
            pi = self._para_map[line_index]
            para = self.doc.paragraphs[pi]
            self._replace_para_text(para, new_text)

        elif line.source == "table":
            ti, ri, ci = self._table_map[line_index]
            cell = self.doc.tables[ti].rows[ri].cells[ci]
            if cell.paragraphs:
                self._replace_para_text(cell.paragraphs[0], new_text)

        # Update internal state
        self._lines[line_index].text = new_text
        self._lines[line_index].char_count = len(new_text)

    @staticmethod
    def _replace_para_text(para, new_text: str):
        """
        Replace all runs in `para` with a single run containing `new_text`,
        preserving the run formatting of the first non-empty run (or the
        paragraph's default style if no runs exist).
        """
        # Capture formatting from first non-empty run
        template_run = None
        for run in para.runs:
            if run.text.strip():
                template_run = run
                break
        if template_run is None and para.runs:
            template_run = para.runs[0]

        # Clone the run XML element so we can restore it
        if template_run is not None:
            rPr_clone = None
            rPr = template_run._r.find(qn("w:rPr"))
            if rPr is not None:
                rPr_clone = copy.deepcopy(rPr)
        else:
            rPr_clone = None

        # Remove all existing runs from the paragraph XML
        p_elem = para._p
        for r in p_elem.findall(qn("w:r")):
            p_elem.remove(r)

        # Create a new run element
        new_r = OxmlElement("w:r")

        # Re-attach formatting
        if rPr_clone is not None:
            new_r.append(rPr_clone)

        # Add text element (preserve leading/trailing spaces)
        new_t = OxmlElement("w:t")
        new_t.text = new_text
        if new_text and (new_text[0] == " " or new_text[-1] == " "):
            new_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        new_r.append(new_t)

        p_elem.append(new_r)

    # ── Export ────────────────────────────────────────────────────────────────

    def save_to_bytes(self) -> bytes:
        buf = io.BytesIO()
        self.doc.save(buf)
        buf.seek(0)
        return buf.read()
