from __future__ import annotations

import copy
import io
from dataclasses import dataclass
from typing import List, Optional

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


@dataclass
class ResumeLine:
    index: int
    text: str
    char_count: int
    source: str
    para_index: int
    table_ref: Optional[tuple] = None


class ResumeProcessor:
    def __init__(self, docx_bytes: bytes):
        self._original_bytes = docx_bytes
        self.doc = Document(io.BytesIO(docx_bytes))
        self._lines: List[ResumeLine] = []
        self._para_map: dict[int, int] = {}
        self._table_map: dict[int, tuple] = {}
        self._parse()

    def _parse(self):
        idx = 0

        for pi, para in enumerate(self.doc.paragraphs):
            text = para.text
            self._lines.append(
                ResumeLine(
                    index=idx,
                    text=text,
                    char_count=len(text),
                    source="paragraph",
                    para_index=pi,
                )
            )
            self._para_map[idx] = pi
            idx += 1

        for ti, table in enumerate(self.doc.tables):
            for ri, row in enumerate(table.rows):
                for ci, cell in enumerate(row.cells):
                    text = cell.text.strip()
                    self._lines.append(
                        ResumeLine(
                            index=idx,
                            text=text,
                            char_count=len(text),
                            source="table",
                            para_index=-1,
                            table_ref=(ti, ri, ci),
                        )
                    )
                    self._table_map[idx] = (ti, ri, ci)
                    idx += 1

    def get_all_lines(self) -> List[dict]:
        return [
            {
                "index": l.index,
                "text": l.text,
                "char_count": l.char_count,
                "source": l.source,
            }
            for l in self._lines
        ]

    def replace_line(self, line_index: int, new_text: str):
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

        self._lines[line_index].text = new_text
        self._lines[line_index].char_count = len(new_text)

    @staticmethod
    def _replace_para_text(para, new_text: str):
        template_run = None
        for run in para.runs:
            if run.text.strip():
                template_run = run
                break

        if template_run is None and para.runs:
            template_run = para.runs[0]

        if template_run is not None:
            rPr_clone = None
            rPr = template_run._r.find(qn("w:rPr"))
            if rPr is not None:
                rPr_clone = copy.deepcopy(rPr)
        else:
            rPr_clone = None

        p_elem = para._p
        for r in p_elem.findall(qn("w:r")):
            p_elem.remove(r)

        new_run = OxmlElement("w:r")
        if rPr_clone is not None:
            new_run.append(rPr_clone)

        text_elem = OxmlElement("w:t")
        text_elem.text = new_text
        new_run.append(text_elem)
        p_elem.append(new_run)

    def export(self) -> bytes:
        output = io.BytesIO()
        self.doc.save(output)
        output.seek(0)
        return output.getvalue()
