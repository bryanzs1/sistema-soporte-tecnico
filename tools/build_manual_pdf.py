from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.enums import TA_LEFT

ROOT = Path(__file__).resolve().parents[1]
md_path = ROOT / "docs" / "MANUAL_USO_SISTEMA.md"
pdf_path = ROOT / "docs" / "MANUAL_USO_SISTEMA.pdf"

text = md_path.read_text(encoding="utf-8", errors="replace")

# Basic markdown-to-flowables conversion
styles = getSampleStyleSheet()
normal = ParagraphStyle(
    "ManualNormal",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=10,
    leading=14,
    alignment=TA_LEFT,
    spaceAfter=6,
)
h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=10)
h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, spaceAfter=8)
h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=12, leading=16, spaceAfter=6)

story = []
bullet_buffer = []


def flush_bullets():
    global bullet_buffer
    if not bullet_buffer:
        return
    items = [ListItem(Paragraph(b, normal), leftIndent=8) for b in bullet_buffer]
    story.append(ListFlowable(items, bulletType="bullet", start="*", leftIndent=12))
    story.append(Spacer(1, 6))
    bullet_buffer = []


for raw_line in text.splitlines():
    line = raw_line.strip()

    if not line:
        flush_bullets()
        story.append(Spacer(1, 6))
        continue

    if line.startswith("# "):
        flush_bullets()
        story.append(Paragraph(line[2:].replace("&", "&amp;"), h1))
        continue

    if line.startswith("## "):
        flush_bullets()
        story.append(Paragraph(line[3:].replace("&", "&amp;"), h2))
        continue

    if line.startswith("### "):
        flush_bullets()
        story.append(Paragraph(line[4:].replace("&", "&amp;"), h3))
        continue

    if line.startswith("- "):
        bullet_buffer.append(line[2:].replace("&", "&amp;"))
        continue

    if line.startswith("---"):
        flush_bullets()
        story.append(Spacer(1, 8))
        continue

    flush_bullets()
    safe = line.replace("&", "&amp;")
    story.append(Paragraph(safe, normal))

flush_bullets()

doc = SimpleDocTemplate(
    str(pdf_path),
    pagesize=A4,
    leftMargin=36,
    rightMargin=36,
    topMargin=36,
    bottomMargin=36,
    title="Manual de Uso del Sistema",
    author="Sistema Soporte Tecnico",
)
doc.build(story)

print(f"PDF generated: {pdf_path}")
