from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from pypdf import PdfReader
import io

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

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
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        # Running header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 800, "MULTIGALAXIAL LIFE: A 40-VOLUME RESEARCH PROGRAMME")
            self.drawRightString(541, 800, f"VOLUME 1 • SCIENTIFIC MANUSCRIPT")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 792, 541, 792)
        
        # Running footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 50, 541, 50)
        self.drawString(54, 38, "NASA / ESA Astrobiological Frameworks • Reproducible Computational Research")
        self.drawRightString(541, 38, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

buf = io.BytesIO()
doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=54, rightMargin=54, topMargin=60, bottomMargin=60)
styles = getSampleStyleSheet()
story = [Paragraph("Page 1 Content", styles['Normal']), PageBreak(), Paragraph("Page 2 Content", styles['Normal'])]
doc.build(story, canvasmaker=NumberedCanvas)
buf.seek(0)
reader = PdfReader(buf)
print(f"Verified pages: {len(reader.pages)}")
print("NumberedCanvas works perfectly!")
