from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from pypdf import PdfReader
import io

buffer = io.BytesIO()
doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
styles = getSampleStyleSheet()

story = []
for page_num in range(1, 41):
    story.append(Paragraph(f"Page Header {page_num}", styles['Heading1']))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"This is content on page {page_num} of 40.", styles['Normal']))
    if page_num < 40:
        story.append(PageBreak())

doc.build(story)
buffer.seek(0)

reader = PdfReader(buffer)
print(f"Total pages generated: {len(reader.pages)}")
assert len(reader.pages) == 40, f"Expected 40, got {len(reader.pages)}"
print("Exact 40-page verification successful!")
