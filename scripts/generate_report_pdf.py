import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deliverables" / "system-design-report.md"
OUTPUT = ROOT / "deliverables" / "system-design-report.pdf"
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
BOLD_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
if FONT.exists():
    pdfmetrics.registerFont(TTFont("DejaVu", str(FONT)))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(BOLD_FONT)))
    BODY, BOLD = "DejaVu", "DejaVu-Bold"
else:
    BODY, BOLD = "Helvetica", "Helvetica-Bold"

NAVY = colors.HexColor("#0b1220")
TEAL = colors.HexColor("#087f8c")
INK = colors.HexColor("#1d2736")
MUTED = colors.HexColor("#5f6b7a")
LIGHT = colors.HexColor("#eef3f7")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="ReportTitle", fontName=BOLD, fontSize=22, leading=27,
    textColor=NAVY, spaceAfter=8))
styles.add(ParagraphStyle(name="H1x", fontName=BOLD, fontSize=16, leading=20,
    textColor=TEAL, spaceBefore=14, spaceAfter=6, keepWithNext=True))
styles.add(ParagraphStyle(name="H2x", fontName=BOLD, fontSize=12, leading=15,
    textColor=NAVY, spaceBefore=10, spaceAfter=4, keepWithNext=True))
styles.add(ParagraphStyle(name="Bodyx", fontName=BODY, fontSize=8.8, leading=12.2,
    textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name="Bulletx", fontName=BODY, fontSize=8.6, leading=11.5,
    textColor=INK, leftIndent=12, firstLineIndent=-7, spaceAfter=3))
styles.add(ParagraphStyle(name="Cellx", fontName=BODY, fontSize=7.2, leading=9,
    textColor=INK))
styles.add(ParagraphStyle(name="CellHeadx", fontName=BOLD, fontSize=7.2, leading=9,
    textColor=colors.white))
styles.add(ParagraphStyle(name="Footerx", fontName=BODY, fontSize=7,
    textColor=MUTED, alignment=TA_CENTER))


def inline_markup(value: str) -> str:
    value = html.escape(value, quote=False)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`(.+?)`", r'<font name="DejaVu" color="#087f8c">\1</font>', value)
    return value


def paragraph(value: str, style="Bodyx"):
    return Paragraph(inline_markup(value), styles[style])


def draw_page(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 5 * mm, width, 5 * mm, fill=1, stroke=0)
    canvas.setFont(BODY, 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "SIS SCALABILITY LAB  |  SYSTEM DESIGN")
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()

def main():
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    story = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            story.append(Spacer(1, 2 * mm))
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                table_lines.append(cells)
                i += 1
            table_lines = [row for row in table_lines if not all(
                re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in row
            )]
            if table_lines:
                col_count = max(map(len, table_lines))
                data = []
                for row_index, row in enumerate(table_lines):
                    row = row + [""] * (col_count - len(row))
                    style = "CellHeadx" if row_index == 0 else "Cellx"
                    data.append([Paragraph(inline_markup(cell), styles[style]) for cell in row])
                usable = A4[0] - 36 * mm
                widths = [usable / col_count] * col_count
                table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5df")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.extend([table, Spacer(1, 3 * mm)])
            continue

        if line.startswith("# "):
            story.append(Paragraph(inline_markup(line[2:]), styles["ReportTitle"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline_markup(line[3:]), styles["H1x"]))
        elif line.startswith("### "):
            story.append(Paragraph(inline_markup(line[4:]), styles["H2x"]))
        elif line.startswith("- "):
            story.append(Paragraph("• " + inline_markup(line[2:]), styles["Bulletx"]))
        elif re.match(r"^\d+\.\s", line):
            story.append(Paragraph(inline_markup(line), styles["Bulletx"]))
        else:
            story.append(paragraph(line))
        i += 1

    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm,
        leftMargin=18 * mm, topMargin=17 * mm, bottomMargin=17 * mm,
        title="Scalable Student Information System — System Design Report",
        author="SIS Scalability Lab")
    # Appendix: actual UI screenshots captured from the current production build.
    shots = [
        ("01-overview-desktop.png", "A1. Dashboard overview — desktop"),
        ("view-courses-desktop.png", "A2. Course catalogue — desktop"),
        ("view-enrollment-desktop.png", "A3. Enrollment workspace — desktop"),
        ("view-records-desktop.png", "A4. Academic records — desktop"),
        ("view-staff-desktop.png", "A5. Faculty workspace — desktop"),
        ("view-systems-desktop.png", "A6. System observability — desktop"),
        ("view-overview-mobile.png", "A7. Dashboard overview — mobile"),
        ("view-mobile-navigation.png", "A8. Mobile navigation — open drawer"),
    ]
    screenshot_dir = ROOT / "deliverables" / "screenshots"
    story.append(PageBreak())
    story.append(Paragraph("Appendix A — UI evidence", styles["ReportTitle"]))
    story.append(paragraph("Screenshots refreshed 20 October 2026 from the current React production build connected to an isolated PostgreSQL 17.11 verification database with synthetic data. They show interface states; automated database and concurrency claims are supported separately by the PostgreSQL test results."))
    for shot_index, (filename, caption) in enumerate(shots):
        path = screenshot_dir / filename
        if not path.is_file():
            continue
        if shot_index > 0:
            story.append(PageBreak())
        story.append(Paragraph(caption, styles["H1x"]))
        img = Image(str(path))
        img._restrictSize(A4[0] - 36 * mm, A4[1] - 58 * mm)
        story.append(img)
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("Source: local Playwright capture; UI source and CSS were not modified for this audit.", styles["Footerx"]))

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
