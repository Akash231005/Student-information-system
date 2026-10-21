from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parents[1] / "deliverables" / "SIS-System-Design-Poster.pdf"
PAGE = landscape(A3)
BG = colors.HexColor("#0b1220")
PANEL = colors.HexColor("#121d30")
LINE = colors.HexColor("#2a3a52")
TEXT = colors.HexColor("#e7edf7")
MUTED = colors.HexColor("#9aabc1")
TEAL = colors.HexColor("#77d4c5")
AMBER = colors.HexColor("#ffbe69")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="PosterTitle", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=27, leading=31, textColor=TEXT, alignment=TA_LEFT, spaceAfter=2))
styles.add(ParagraphStyle(name="PosterSub", parent=styles["Normal"], fontName="Helvetica",
    fontSize=12, leading=16, textColor=MUTED, spaceAfter=4))
styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=14, leading=17, textColor=TEAL, spaceBefore=4, spaceAfter=6))
styles.add(ParagraphStyle(name="BodyPoster", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=9.2, leading=12.3, textColor=TEXT, spaceAfter=4))
styles.add(ParagraphStyle(name="SmallPoster", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8.3, leading=10.8, textColor=MUTED, spaceAfter=3))
styles.add(ParagraphStyle(name="Metric", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=14, leading=17, textColor=TEAL, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="MetricLabel", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8, leading=10, textColor=MUTED, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=8.4, leading=10, textColor=TEAL))
styles.add(ParagraphStyle(name="TableBody", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8, leading=10, textColor=TEXT))


def P(text, style="BodyPoster"):
    return Paragraph(text, styles[style])


def panel_table(rows, widths, padd=8):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.8, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padd),
        ("RIGHTPADDING", (0, 0), (-1, -1), padd),
        ("TOPPADDING", (0, 0), (-1, -1), padd),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padd),
    ]))
    return t


def background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, PAGE[0], PAGE[1], fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, PAGE[1] - 6 * mm, PAGE[0], 6 * mm, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(PAGE[0] - 12 * mm, 7 * mm, "SIS SCALABILITY LAB  |  SYSTEM DESIGN")
    canvas.restoreState()

story = []
story.append(Spacer(1, 5 * mm))
story.append(P("SCALABLE STUDENT INFORMATION SYSTEM", "PosterTitle"))
story.append(P("Correctness-first academic workflows + measurable system-design trade-offs", "PosterSub"))

metric_data = [[
    P("23 / 23", "Metric"), P("5 of 20", "Metric"), P("8 components", "Metric"),
    P("0 oversold seats", "Metric")
], [
    P("Automated tests passing", "MetricLabel"), P("Concurrent requests accepted: exactly 5", "MetricLabel"),
    P("Mapped to observable endpoints", "MetricLabel"), P("Capacity invariant held in PostgreSQL test", "MetricLabel")
]]
metric = Table(metric_data, colWidths=[(PAGE[0] - 30 * mm) / 4] * 4, rowHeights=[9 * mm, 9 * mm])
metric.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), PANEL),
    ("BOX", (0, 0), (-1, -1), 0.8, LINE),
    ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 2),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
]))
story.append(metric)
story.append(Spacer(1, 4 * mm))

col_width = (PAGE[0] - 32 * mm) / 3
col1 = [
    P("01  PROBLEM & ARCHITECTURE", "Section"),
    P("<b>Requirements:</b> student profile and authentication, course search/registration, attendance, exams/grades, timetable and notifications under increasing concurrent load."),
    P("<b>Stack:</b> FastAPI + SQLAlchemy 2 + PostgreSQL; browser dashboard; Locust; Alembic migrations."),
    P("<b>Design thesis:</b> correctness before scale. Keep PostgreSQL authoritative; introduce caches and distributed mechanisms only with measurable evidence."),
    P("02  CORE DOMAIN", "Section"),
    P("<b>Student</b> → <b>Course</b> → <b>CourseOffering</b> → <b>Enrollment</b>. A catalog course is not the same thing as a term-specific section."),
    P("Supporting entities: user account, attendance record, assessment, grade, timetable event and academic notification."),
    P("<b>Invariant:</b> 0 ≤ enrolled_count ≤ capacity. A seat is reserved with one conditional database update, and the enrollment insert commits in the same transaction."),
]
col2 = [
    P("03  EIGHT SYSTEM-DESIGN COMPONENTS", "Section"),
    P("<b>Rate limiter:</b> process-local token bucket; track 429 responses."),
    P("<b>Sharding + consistent hashing:</b> in-memory shard map and virtual-node ring; observe shard distribution and key movement."),
    P("<b>Key-value store:</b> bounded TTL/LRU cache for autocomplete; compare cold/warm latency."),
    P("<b>Unique ID generator:</b> time/worker/sequence ID; check uniqueness and generation rate."),
    P("<b>URL shortener:</b> short code to HTTP redirect."),
    P("<b>Web crawler:</b> bounded public HTTPS crawler, same seed hostname, limited pages/depth/bytes."),
    P("<b>Autocomplete:</b> SQL prefix search plus TTL cache."),
    P("The ring does not migrate or replicate data. The crawler success path is mocked because live DNS was unavailable. These are experiments, not production-distributed services.", "SmallPoster"),
    P("04  VALIDATION", "Section"),
    P("Attendance requires an active enrollment; grades are bounded by assessment maximum; timetable room/time overlap is rejected; duplicate enrollment and repeated drop are guarded."),
]
col3 = [
    P("05  MEASURED LOCAL BASELINE", "Section"),
    P("10 simulated users · 20 seconds per workload · limiter disabled for baseline · synthetic dataset: 1,000 students, 100 courses, 200 offerings."),
]
table_rows = [
    [P("Workload", "TableHead"), P("Req/s", "TableHead"), P("p50 / p95", "TableHead")],
    [P("Course discovery", "TableBody"), P("35.82", "TableBody"), P("5 / 10 ms", "TableBody")],
    [P("Profile reads", "TableBody"), P("35.27", "TableBody"), P("5 / 12 ms", "TableBody")],
    [P("Account registration", "TableBody"), P("19.47", "TableBody"), P("60 / 83 ms", "TableBody")],
    [P("Autocomplete ON", "TableBody"), P("35.55", "TableBody"), P("2 / 5 ms", "TableBody")],
]
tbl = Table(table_rows, colWidths=[48 * mm, 23 * mm, 34 * mm])
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), PANEL),
    ("BOX", (0, 0), (-1, -1), 0.6, LINE),
    ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
col3.extend([tbl, Spacer(1, 3 * mm),
    P("Baseline/cache runs had 0 failures. Rate-limit overload rejected 243/676 (35.95%). Cache ON/OFF p50/p95 2/5 vs 5/10 ms (one 20 s run each).", "SmallPoster"),
    P("06  WHAT IS PROVED", "Section"),
    P("In the PostgreSQL concurrency test, 20 distinct students competed for 5 seats: exactly 5 succeeded, 15 were rejected and the counter matched active enrollment rows."),
    P("07  LIMITATIONS & NEXT STEPS", "Section"),
    P("Role checks protect staff writes and student record reads; token revocation is absent. Rate limiter/cache/shard demo state is process-local; short links persist in PostgreSQL. Sharding is simulated; continuous peak CPU/memory was not sampled; separate API-process CPU/RSS sampling is available. Next: repeat longer runs and add shared state.")
])

columns = Table([[col1, col2, col3]], colWidths=[col_width] * 3, hAlign="LEFT")
columns.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), BG),
    ("BOX", (0, 0), (-1, -1), 0.7, LINE),
    ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story.append(columns)
story.append(Spacer(1, 3 * mm))
story.append(P("Evidence artifacts: PostgreSQL test suite · Locust CSV runs · system-design report · runnable API at /docs", "SmallPoster"))

doc = SimpleDocTemplate(str(OUT), pagesize=PAGE, rightMargin=12 * mm, leftMargin=12 * mm,
                        topMargin=10 * mm, bottomMargin=12 * mm, title="SIS System Design Poster")
doc.build(story, onFirstPage=background, onLaterPages=background)
print(f"Created {OUT}")
