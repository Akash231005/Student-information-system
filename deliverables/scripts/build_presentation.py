"""Generate the 9-slide presentation that matches deliverables/presentation-script.md.

Light theme, same palette as the report (ink / teal / muted / rule / paper), so the deck, the
report and the poster read as one submission. Re-run after editing: it overwrites its own output.

    uv run --project sis-app --extra deliverables python deliverables/scripts/build_presentation.py
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent.parent          # deliverables/
ARCH = HERE / "diagrams" / "architecture.png"
OUT = HERE / "SIS-System-Design-Presentation-2026-10-22.pptx"

W, H = 13.333, 7.5
INK = RGBColor(0x17, 0x2B, 0x36)
TEAL = RGBColor(0x08, 0x7E, 0x78)
MUTED = RGBColor(0x52, 0x68, 0x73)
RULE = RGBColor(0xD5, 0xDE, 0xE2)
PAPER = RGBColor(0xF3, 0xF6, 0xF6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PG = RGBColor(0xA9, 0x6A, 0x12)      # matches the figure's PostgreSQL amber
REDIS = RGBColor(0xA8, 0x35, 0x3F)   # matches the figure's Redis red
MONGO = RGBColor(0x3B, 0x4C, 0xA8)   # matches the figure's MongoDB blue
BODY = "Aptos"
MONO = "Consolas"
M = 0.95                              # page margin (inches)
TOTAL = 9


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def tb(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    return frame


def para(frame, text, size=14, color=INK, bold=False, font=BODY, tracking=None,
         align=PP_ALIGN.LEFT, space_before=0, space_after=0, line=None, first=False, caps=False):
    """One call per line: embedded newlines become paragraphs, so every line keeps its colour."""
    lines = text.split("\n")
    p = None
    for i, chunk in enumerate(lines):
        if i == 0:
            p = frame.paragraphs[0] if first else frame.add_paragraph()
        else:
            p = frame.add_paragraph()
        p.alignment = align
        p.space_before = Pt(space_before if i == 0 else 0)
        p.space_after = Pt(space_after)
        if line:
            p.line_spacing = line
        run = p.add_run()
        run.text = chunk.upper() if caps else chunk
        f = run.font
        f.name, f.size, f.bold = font, Pt(size), bold
        f.color.rgb = color
        if tracking is not None:                 # letter-spacing, in 1/100 pt
            run._r.get_or_add_rPr().set("spc", str(tracking))
    return p


def flat(shape):
    """Drop the theme shape style: no inherited shadow, no inherited outline."""
    style = shape._element.find(
        "{http://schemas.openxmlformats.org/presentationml/2006/main}style"
    )
    if style is not None:
        shape._element.remove(style)
    shape.shadow.inherit = False
    return shape



def chrome(slide, n, eyebrow, headline, kicker=None, headline_size=30):
    """Eyebrow + headline + optional kicker + footer, identical on every content slide."""
    frame = tb(slide, M, 0.62, W - 2 * M - 1.3, 0.3)
    para(frame, eyebrow, size=10.5, color=TEAL, bold=True, tracking=180, caps=True, first=True)
    frame = tb(slide, M, 0.95, W - 2 * M, 1.15)
    para(frame, headline, size=headline_size, color=INK, bold=True, line=1.06, first=True)
    if kicker:
        frame = tb(slide, M, 2.05, W - 2 * M - 0.6, 0.5)
        para(frame, kicker, size=14, color=MUTED, line=1.3, first=True)
    rule(slide, M, H - 0.78, W - 2 * M, 0.008, RULE)
    frame = tb(slide, M, H - 0.66, 8.0, 0.28)
    para(frame, "Orbit SIS  ·  system design  ·  22 October 2026", size=9, color=MUTED,
         tracking=40, first=True)
    frame = tb(slide, W - M - 1.2, H - 0.66, 1.2, 0.28)
    para(frame, f"{n:02d} / {TOTAL:02d}", size=9, color=MUTED, tracking=40, align=PP_ALIGN.RIGHT,
         first=True)


def rule(slide, x, y, w, h, color=RULE):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return flat(shape)


def panel(slide, x, y, w, h, fill=PAPER, border=RULE, accent=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if border is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = border
        shape.line.width = Pt(0.75)
    flat(shape)
    if accent:
        rule(slide, x, y, 0.045, h, accent)
    return shape


def terminal(slide, x, y, w, h, heading, lines):
    """A quiet code panel: heading in small caps, then monospace lines."""
    panel(slide, x, y, w, h)
    frame = tb(slide, x + 0.22, y + 0.17, w - 0.44, 0.25)
    para(frame, heading, size=9.5, color=MUTED, bold=True, tracking=140, caps=True, first=True)
    frame = tb(slide, x + 0.22, y + 0.52, w - 0.44, h - 0.7)
    for i, (text, color) in enumerate(lines):
        para(frame, text, size=11, color=color, font=MONO, line=1.34, first=(i == 0))


def stat(slide, x, y, w, h, value, label, detail=None):
    panel(slide, x, y, w, h, fill=WHITE)
    rule(slide, x, y, w, 0.035, TEAL)
    frame = tb(slide, x + 0.26, y + 0.24, w - 0.5, 0.62)
    para(frame, value, size=25, color=TEAL, bold=True, first=True)
    frame = tb(slide, x + 0.26, y + 0.86, w - 0.5, 0.5)
    para(frame, label, size=12, color=INK, bold=True, line=1.2, first=True)
    if detail:
        frame = tb(slide, x + 0.26, y + 1.45, w - 0.5, h - 1.6)
        para(frame, detail, size=10.5, color=MUTED, line=1.28, first=True)


def dump(prs):
    prs.save(OUT)
    print(f"wrote {OUT.relative_to(HERE.parent)}  ({len(prs.slides)} slides)")


prs = Presentation()
prs.slide_width, prs.slide_height = Emu(int(W * 914400)), Emu(int(H * 914400))

# ---------------------------------------------------------------- 1 · title
s = blank(prs)
rule(s, M, 1.55, 1.5, 0.045, TEAL)
frame = tb(s, M, 1.95, 10.4, 2.4)
para(frame, "A Student Information System\nthat refuses to lie", size=42, color=INK, bold=True,
     line=1.1, first=True)
frame = tb(s, M, 4.28, 9.6, 0.9)
para(frame, "Every claim in this talk is a measurement, or it is not in the talk.",
     size=17, color=MUTED, line=1.3, first=True)
frame = tb(s, M, 5.55, 9.6, 0.9)
para(frame, "Sujith  ·  UCS3513 System Design Laboratory", size=13, color=INK, bold=True, first=True)
para(frame, "github.com/sujith0613/sis-system-design", size=11.5, color=MUTED, space_before=4)
frame = tb(s, W - M - 3.1, 6.55, 3.1, 0.3)
para(frame, "10 minutes  ·  live demo", size=10.5, color=MUTED, tracking=60,
     align=PP_ALIGN.RIGHT, first=True)

# ---------------------------------------------------------------- 2 · hook
s = blank(prs)
frame = tb(s, M, 0.62, W - 2 * M, 0.3)
para(frame, "the point", size=10.5, color=TEAL, bold=True, tracking=180, caps=True, first=True)
frame = tb(s, M, 1.55, 11.4, 1.0)
para(frame, "Everyone demos the happy path.", size=34, color=INK, bold=True, line=1.1, first=True)
frame = tb(s, M, 2.6, 11.4, 1.1)
para(frame, "Ours demos the failure path.", size=44, color=TEAL, bold=True, line=1.1, first=True)
frame = tb(s, M, 4.35, 9.6, 1.2)
para(frame, "Redis. MongoDB. Rate limits. Every project in this room has that diagram.\n"
            "This one can prove it — so it can also show you what happens when it breaks.",
     size=15.5, color=MUTED, line=1.45, first=True)
rule(s, M, H - 0.78, W - 2 * M, 0.008, RULE)
frame = tb(s, M, H - 0.66, 8.0, 0.28)
para(frame, "Orbit SIS  ·  system design  ·  22 October 2026", size=9, color=MUTED,
     tracking=40, first=True)
frame = tb(s, W - M - 1.2, H - 0.66, 1.2, 0.28)
para(frame, "02 / 09", size=9, color=MUTED, tracking=40, align=PP_ALIGN.RIGHT, first=True)

# ---------------------------------------------------------------- 3 · three lies
s = blank(prs)
chrome(s, 3, "the starting position", "Three claims, and how each one dies",
       "Each of these is true of a prototype that never has to fail in public.")
cards = [
    ("\u201cRate limited\u201d", "Two replicas.\nTwo counters.\nDouble the limit."),
    ("\u201cSharded\u201d", "One process.\nOne dictionary.\nhash(key) % 3."),
    ("\u201cCached\u201d", "Cache and truth share\na lifetime, so\nneither is real."),
]
x = M
for claim, how in cards:
    panel(s, x, 2.75, 3.62, 2.35, fill=WHITE)
    frame = tb(s, x + 0.3, 3.0, 3.0, 0.5)
    para(frame, claim, size=19, color=INK, bold=True, first=True)
    frame = tb(s, x + 0.3, 3.62, 3.0, 1.3)
    para(frame, how, size=13.5, color=MUTED, line=1.35, first=True)
    x += 3.9
frame = tb(s, M, 5.55, 11.4, 0.9)
para(frame, "We deleted all three. No flag, no fallback: if a store is down, the system refuses "
            "to answer.", size=15, color=INK, bold=True, line=1.35, first=True)

# ---------------------------------------------------------------- 4 · architecture
s = blank(prs)
frame = tb(s, M, 0.5, 9.0, 0.3)
para(frame, "architecture", size=10.5, color=TEAL, bold=True, tracking=180, caps=True, first=True)
frame = tb(s, M, 0.78, 11.0, 0.5)
para(frame, "Three real stores, one startup guard", size=23, color=INK, bold=True, first=True)

# The figure carries its own title and footnote, so crop them (112 px top, 78 px bottom) instead
# of keeping a second, slide-only copy of the asset in sync.
TOP, BOTTOM = 250, 78          # px of the figure's own title and footnote, measured from the PNG
visible_ar = 2920 / (2040 - TOP - BOTTOM)
width = 9.4
pic = s.shapes.add_picture(str(ARCH), Inches((W - width) / 2), Inches(1.28), width=Inches(width))
pic.crop_top, pic.crop_bottom = TOP / 2040, BOTTOM / 2040
pic.height = Inches(width / visible_ar)

frame = tb(s, M, 6.9, 9.4, 0.5)
para(frame, "Six containers on one host: PostgreSQL, Redis, config server, two shards, mongos. "
            "Nothing is emulated in-process.", size=10.5, color=MUTED, line=1.3, first=True)
frame = tb(s, W - M - 1.2, 6.9, 1.2, 0.3)
para(frame, "04 / 09", size=9, color=MUTED, tracking=40, align=PP_ALIGN.RIGHT, first=True)

# ---------------------------------------------------------------- 5 · eight components (unit requirement)
s = blank(prs)
chrome(s, 5, "the unit's checklist", "Eight components, each with a job you can observe")
rows = [
    ("Cache", "autocomplete results with server-side expiry", "Redis · TTL 20 s, allkeys-lru"),
    ("Unique IDs", "time-sortable 64-bit identifiers", "Redis worker slots"),
    ("Rate limiter", "one quota shared by every process", "Redis · atomic Lua"),
    ("URL shortener", "create and redirect (307)", "PostgreSQL"),
    ("Web crawler", "robots-aware frontier, resumable", "MongoDB collections"),
    ("Autocomplete", "prefix search over the catalogue", "Redis in front of PostgreSQL"),
    ("Consistent hashing", "100 virtual nodes, routing shown", "application ring"),
    ("Sharding", "hashed shard key, real chunk moves", "MongoDB · 2 shards + mongos"),
]
x0, y0, widths = M, 2.28, (2.05, 4.15, 4.05)
table_shape = s.shapes.add_table(len(rows) + 1, 3, Inches(x0), Inches(y0),
                                 Inches(sum(widths)), Inches(0.42 * (len(rows) + 1)))
table = table_shape.table
table.first_row = False
table.horz_banding = False
# "No Style, No Grid" so the fills below are the only styling
table._tbl.tblPr.find(
    "{http://schemas.openxmlformats.org/drawingml/2006/main}tableStyleId"
).text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
for i, width in enumerate(widths):
    table.columns[i].width = Inches(width)
header = ("Component", "What it does here", "Where that state actually lives")
for c, text in enumerate(header):
    cell = table.cell(0, c)
    cell.fill.solid()
    cell.fill.fore_color.rgb = PAPER
    frame = cell.text_frame
    frame.margin_left = frame.margin_right = Inches(0.12)
    para(frame, text, size=10, color=MUTED, bold=True, tracking=120, caps=True, first=True)
for r, (component, job, home) in enumerate(rows, start=1):
    for c, text in enumerate((component, job, home)):
        cell = table.cell(r, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = WHITE if r % 2 else PAPER
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        frame = cell.text_frame
        frame.margin_left = frame.margin_right = Inches(0.12)
        para(frame, text, size=11.5, color=INK if c == 0 else MUTED,
             bold=(c == 0), first=True)
frame = tb(s, M, 6.25, 11.2, 0.5)
para(frame, "Each one answers on a live endpoint under /system-design/ — not on a slide.",
     size=12.5, color=TEAL, bold=True, first=True)

# ---------------------------------------------------------------- 6 · claim 1
s = blank(prs)
chrome(s, 6, "claim 1", "It refuses to run on a lie")
frame = tb(s, M, 2.35, 4.5, 2.6)
para(frame, "Take Redis away and the honest answer is 503 with the store named.",
     size=17, color=INK, bold=True, line=1.35, first=True)
para(frame, "A per-process fallback would have answered 200 — and silently doubled every "
            "client's quota. Availability loses to honesty here, on purpose.",
     size=12.5, color=MUTED, line=1.4, space_before=12)
terminal(s, 5.75, 2.25, 6.6, 2.05, "at boot", [
    ("$ uvicorn app.main:app", MUTED),
    ("RuntimeError: Required state stores", INK),
    ("  are not available:", INK),
    ("  - Redis unreachable at :6399", REDIS),
    ("ERROR: Application startup failed.", INK),
])
terminal(s, 5.75, 4.5, 6.6, 1.85, "at runtime, with Redis killed", [
    ("$ podman stop sis-redis   $ curl /courses", MUTED),
    ("[503]  {\"status\": \"degraded\",", INK),
    ("        \"store\": \"redis\",", INK),
    ("        \"detail\": \"…cannot decide…\"}", INK),
])
rule(s, M, 4.72, 0.9, 0.03, TEAL)
frame = tb(s, M, 4.92, 4.4, 0.9)
para(frame, "Recovery is the store coming back — not a restart.",
     size=12.5, color=TEAL, bold=True, line=1.35, first=True)

# ---------------------------------------------------------------- 7 · claim 2
s = blank(prs)
chrome(s, 7, "claim 2", "Our hash ring disagrees with the database — in public")
terminal(s, M, 2.35, 5.75, 2.05, "the routing disagreement, as served", [
    ("$ curl /system-design/route/DEMO-KEY-1", MUTED),
    ("{ \"ring_prediction\": \"sis-shard-b\",", INK),
    ("  \"actual_owner\":    \"sis-shard-a\",", INK),
    ("  \"agrees\": false }", TEAL),
])
terminal(s, M, 4.6, 5.75, 1.7, "the movement is real", [
    ("$ curl -X POST …/move-chunk", MUTED),
    ("{ \"from_shard\": \"sis-shard-a\",", INK),
    ("  \"to_shard\":   \"sis-shard-b\" }", INK),
])
frame = tb(s, 7.1, 2.35, 5.25, 3.9)
para(frame, "Two answers, one endpoint.", size=17, color=INK, bold=True, line=1.3, first=True)
para(frame, "The left number is the consistent-hashing ring from the lecture. The right is what "
            "mongos actually does with a hashed shard key. They disagree, and the API says so "
            "with a boolean.",
     size=12.5, color=MUTED, line=1.45, space_before=12)
para(frame, "The ring routes. moveChunk moves. One of those is a drawing; the other changed "
            "129 documents between two replica sets on this machine.",
     size=12.5, color=MUTED, line=1.45, space_before=14)

# ---------------------------------------------------------------- 8 · claim 3
s = blank(prs)
chrome(s, 8, "claim 3", "The invariants hold when things go wrong")
tiles = [
    ("5 / 20", "seats under concurrency",
     "One 5-seat offering, 20 simultaneous\nenrolments: 5 x 201, 15 x 409,\nenrolled_count = 5."),
    ("3 → 0", "one bucket, two workers",
     "Worker A spends all three tokens;\nworker B is refused."),
    ("1,000", "IDs from two slots",
     "Two processes never mint the\nsame number: 1,000 generated,\n0 collisions."),
    ("0", "pages refetched",
     "A second crawl took 5 URLs off\nthe persisted frontier and\nfetched none twice."),
]
x = M
for value, label, detail in tiles:
    stat(s, x, 2.3, 2.69, 3.05, value, label, detail)
    x += 2.9
frame = tb(s, M, 5.62, 11.4, 0.4)
para(frame, "The shared thing lives in the store, not in the process.",
     size=16, color=TEAL, bold=True, first=True)
frame = tb(s, M, 6.05, 11.4, 0.4)
para(frame, "Every number here came out of the running stack, and the suite asserts the counts, "
            "not the vibe.", size=11.5, color=MUTED, first=True)

# ---------------------------------------------------------------- 9 · limits + close
s = blank(prs)
frame = tb(s, M, 0.55, 9.0, 0.3)
para(frame, "honest limits  ·  and the close", size=10.5, color=TEAL, bold=True, tracking=180,
     caps=True, first=True)
frame = tb(s, M, 0.9, 5.6, 0.5)
para(frame, "What this is not", size=26, color=INK, bold=True, first=True)
limits = [
    "One host. No failover, no backup, no replication test.",
    "Redis is volatile on purpose: a restart resets the buckets.",
    "Crawler is polite: 3 pages in 7.1 s at 0.5 s delay.",
    "Load numbers predate the migration, so they are not quoted.",
    "One cache flag was deleted, never defaulted to off.",
    "The suite wipes the dev database — a rough edge, not a secret.",
]
frame = tb(s, M, 1.85, 5.5, 3.6)
for i, item in enumerate(limits):
    para(frame, "—  " + item, size=12, color=MUTED, line=1.35, first=(i == 0), space_after=9)
panel(s, 6.9, 1.5, 5.5, 4.6, fill=PAPER, border=None, accent=TEAL)
frame = tb(s, 7.25, 1.85, 4.9, 1.5)
para(frame, "A demo you cannot re-run\nis a story.", size=25, color=INK, bold=True, line=1.18,
     first=True)
frame = tb(s, 7.25, 3.5, 4.9, 1.1)
para(frame, "./run.sh", size=13, color=TEAL, bold=True, font=MONO, first=True)
para(frame, "checks the machine, starts six containers, seeds the data, polls /health",
     size=10.5, color=MUTED, line=1.3, space_before=3)
para(frame, "./stop.sh", size=13, color=TEAL, bold=True, font=MONO, space_before=12)
para(frame, "stops it, then proves every port is closed", size=10.5, color=MUTED,
     space_before=3)
frame = tb(s, 7.25, 5.35, 4.9, 0.5)
para(frame, "github.com/sujith0613/sis-system-design", size=11, color=INK, bold=True, first=True)

dump(prs)
