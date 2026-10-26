"""
volume_builder.py - High-precision scientific PDF and DOCX volume builder
for MULTIGALAXIAL LIFE 40-Volume Research Programme.
Enforces the exact 40-page blueprint and validates with pypdf.
"""

import os
import io
import datetime
from pypdf import PdfReader

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, PageBreak, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT


class NumberedCanvas(canvas.Canvas):
    """Dynamic two-pass canvas providing accurate running headers and footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.volume_number = 1
        self.volume_title = "Scientific Manuscript"

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Running header on page 2+
        if self._pageNumber > 1:
            self.drawString(54, 802, "MULTIGALAXIAL LIFE • 40-VOLUME SCIENTIFIC RESEARCH PROGRAMME")
            self.drawRightString(541, 802, f"VOL. {self.volume_number}: {self.volume_title.upper()[:35]}")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.6)
            self.line(54, 794, 541, 794)

        # Running footer on all pages
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(54, 48, 541, 48)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(54, 36, "Astrobiological Computational Discovery Platform • Interdisciplinary Research")
        self.drawRightString(541, 36, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def get_scientific_styles():
    """Construct refined scientific typography styles."""
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=18, leading=22,
        textColor=colors.HexColor("#0F172A"), alignment=1, spaceAfter=8
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10, leading=14,
        textColor=colors.HexColor("#334155"), alignment=1, spaceAfter=14
    )
    h1_style = ParagraphStyle(
        'ScientificH1', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=12, leading=16,
        textColor=colors.HexColor("#1E293B"), spaceBefore=10, spaceAfter=6
    )
    h2_style = ParagraphStyle(
        'ScientificH2', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=10, leading=13,
        textColor=colors.HexColor("#334155"), spaceBefore=6, spaceAfter=4
    )
    body_style = ParagraphStyle(
        'ScientificBody', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11.8,
        textColor=colors.HexColor("#1E293B"), alignment=4, spaceAfter=5
    )
    bullet_style = ParagraphStyle(
        'ScientificBullet', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11.5,
        textColor=colors.HexColor("#1E293B"), spaceAfter=3, leftIndent=12
    )
    equation_style = ParagraphStyle(
        'EquationBox', parent=styles['Normal'],
        fontName='Courier', fontSize=8.2, leading=11,
        textColor=colors.HexColor("#0F172A"), alignment=1, spaceBefore=4, spaceAfter=4
    )
    callout_style = ParagraphStyle(
        'CalloutText', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=8, leading=11,
        textColor=colors.HexColor("#312E81")
    )
    table_cell_style = ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7.5, leading=9.5,
        textColor=colors.HexColor("#0F172A")
    )
    table_head_style = ParagraphStyle(
        'TableHead', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=7.5, leading=9.5,
        textColor=colors.white
    )

    return {
        "title": title_style, "subtitle": subtitle_style,
        "h1": h1_style, "h2": h2_style,
        "body": body_style, "bullet": bullet_style,
        "equation": equation_style, "callout": callout_style,
        "cell": table_cell_style, "cell_head": table_head_style
    }


def build_scientific_volume(vol_data: dict, out_pdf_path: str, out_docx_path: str) -> int:
    """
    Builds a scientific volume adhering to the exact 40-page allocation blueprint.
    Verifies page count with pypdf and generates matching Word docx.
    """
    vol_num = vol_data["volume_number"]
    vol_title = vol_data["volume_title"]
    pages_content = vol_data["pages_content"]  # List of 40 page specifications
    assert len(pages_content) == 40, f"Expected exactly 40 page specifications, got {len(pages_content)}"

    styles = get_scientific_styles()

    # --------------------------------------------------------------------------
    # 1. BUILD PDF VIA REPORTLAB
    # --------------------------------------------------------------------------
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer, pagesize=A4,
        leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54
    )

    def canvas_factory(*args, **kwargs):
        c = NumberedCanvas(*args, **kwargs)
        c.volume_number = vol_num
        c.volume_title = vol_title
        return c

    story = []

    for p_idx, p_data in enumerate(pages_content, 1):
        # Page header block
        if p_idx == 1:
            # Volume Title on Page 1
            story.append(Paragraph(f"MULTIGALAXIAL LIFE • VOLUME {vol_num}", styles["subtitle"]))
            story.append(Paragraph(vol_title.upper(), styles["title"]))
            story.append(Paragraph(f"<b>Research Team:</b> {vol_data.get('authors', 'Interdisciplinary Consortium on Multigalaxial Astrobiology')}", styles["subtitle"]))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#4F46E5"), spaceAfter=10))

        # Header for the specific page
        p_section_title = p_data.get("section_title", f"Section {p_idx}")
        p_sub_title = p_data.get("sub_title", "")
        story.append(Paragraph(f"<b>{p_section_title}</b>", styles["h1"]))
        if p_sub_title:
            story.append(Paragraph(f"<i>{p_sub_title}</i>", styles["h2"]))

        # Paragraphs for this page
        for para in p_data.get("paragraphs", []):
            if isinstance(para, str):
                story.append(Paragraph(para, styles["body"]))
            elif isinstance(para, tuple) and para[0] == "eq":
                # Mathematical equation block
                eq_box = [
                    [Paragraph(f"<b>Equation ({para[1]}):</b> {para[2]}", styles["equation"])]
                ]
                eq_table = Table(eq_box, colWidths=[485])
                eq_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
                    ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor("#CBD5E1")),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(Spacer(1, 3))
                story.append(eq_table)
                story.append(Spacer(1, 4))
            elif isinstance(para, tuple) and para[0] == "table":
                # Table flowable
                t_headers, t_rows = para[1], para[2]
                table_matrix = [[Paragraph(f"<b>{h}</b>", styles["cell_head"]) for h in t_headers]]
                for r in t_rows:
                    table_matrix.append([Paragraph(str(c), styles["cell"]) for c in r])
                n_cols = len(t_headers)
                col_width = 485 / n_cols
                sci_table = Table(table_matrix, colWidths=[col_width] * n_cols)
                sci_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E293B")),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
                    ('TOPPADDING', (0,0), (-1,-1), 3),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ]))
                story.append(Spacer(1, 4))
                story.append(sci_table)
                story.append(Spacer(1, 4))
            elif isinstance(para, tuple) and para[0] == "callout":
                call_table = Table([[Paragraph(f"<b>Scientific Classification:</b> {para[1]}", styles["callout"])]], colWidths=[485])
                call_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EEF2FF")),
                    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#C7D2FE")),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ]))
                story.append(Spacer(1, 3))
                story.append(call_table)
                story.append(Spacer(1, 4))
            elif isinstance(para, tuple) and para[0] == "bullet":
                story.append(Paragraph(f"• {para[1]}", styles["bullet"]))

        # Force exact page break to guarantee 1-to-1 page correspondence
        if p_idx < 40:
            story.append(PageBreak())

    doc.build(story, canvasmaker=canvas_factory)
    pdf_buffer.seek(0)
    pdf_bytes = pdf_buffer.getvalue()

    # Validate with pypdf
    reader = PdfReader(io.BytesIO(pdf_bytes))
    actual_pages = len(reader.pages)
    print(f"Volume {vol_num} generated. Target: 40 pages | Actual: {actual_pages} pages")

    with open(out_pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # --------------------------------------------------------------------------
    # 2. BUILD COMPANION DOCX
    # --------------------------------------------------------------------------
    doc_word = Document()
    for section in doc_word.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Title
    p_t = doc_word.add_paragraph()
    p_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t = p_t.add_run(f"MULTIGALAXIAL LIFE • VOLUME {vol_num}\n{vol_title.upper()}")
    r_t.bold = True
    r_t.font.size = Pt(16)
    r_t.font.name = "Arial"

    for p_idx, p_data in enumerate(pages_content, 1):
        doc_word.add_heading(f"Page {p_idx}: {p_data.get('section_title', '')}", level=2)
        if p_data.get("sub_title"):
            doc_word.add_paragraph(f"{p_data['sub_title']}")

        for para in p_data.get("paragraphs", []):
            if isinstance(para, str):
                doc_word.add_paragraph(para)
            elif isinstance(para, tuple) and para[0] == "eq":
                doc_word.add_paragraph(f"Equation ({para[1]}): {para[2]}")
            elif isinstance(para, tuple) and para[0] == "bullet":
                doc_word.add_paragraph(f"• {para[1]}")
            elif isinstance(para, tuple) and para[0] == "table":
                t_headers, t_rows = para[1], para[2]
                t_word = doc_word.add_table(rows=len(t_rows) + 1, cols=len(t_headers))
                for c_idx, h in enumerate(t_headers):
                    t_word.cell(0, c_idx).text = h
                for r_idx, r in enumerate(t_rows):
                    for c_idx, val in enumerate(r):
                        t_word.cell(r_idx + 1, c_idx).text = str(val)

        if p_idx < 40:
            doc_word.add_page_break()

    doc_word.save(out_docx_path)
    print(f"Companion DOCX saved to {out_docx_path}")

    return actual_pages
