from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables' / 'SIS-System-Design-Poster-Verified-2026-10-20.pdf'
SHOT = ROOT / 'deliverables' / 'screenshots' / '00-overview-poster-crop.png'
W, H = landscape(A3)
PAPER = colors.HexColor('#F5F0E5')
INK = colors.HexColor('#202620')
MUTED = colors.HexColor('#59635A')
CORAL = colors.HexColor('#F06452')
BLUE = colors.HexColor('#3C55E8')
YELLOW = colors.HexColor('#F4CF58')
MINT = colors.HexColor('#B9D8C1')
WHITE = colors.HexColor('#FFFCF4')
LINE = colors.HexColor('#202620')

c = canvas.Canvas(str(OUT), pagesize=(W, H), pageCompression=1)
c.setTitle('Orbit SIS | System Design Poster | Verification Snapshot 20 Oct 2026')
c.setAuthor('SIS Scalability Lab')

# Editorial grid: warm paper, bold ink, one clear accent hierarchy.
c.setFillColor(PAPER); c.rect(0, 0, W, H, fill=1, stroke=0)
c.setFillColor(INK); c.rect(0, H-8*mm, W, 8*mm, fill=1, stroke=0)
c.setFillColor(YELLOW); c.rect(0, H-8*mm, 58*mm, 8*mm, fill=1, stroke=0)
margin = 13*mm

def label(x, y, txt, size=8, color=MUTED, font='Helvetica-Bold', tracking=0):
    c.setFillColor(color); c.setFont(font, size)
    if tracking:
        obj=c.beginText(x,y); obj.setCharSpace(tracking); obj.textLine(txt); c.drawText(obj)
    else: c.drawString(x,y,txt)

def paragraph(x, top, width, text, size=9, leading=12, color=INK, font='Helvetica', max_h=1000):
    style=ParagraphStyle('p',fontName=font,fontSize=size,leading=leading,textColor=color,spaceAfter=0,spaceBefore=0)
    p=Paragraph(text,style); _,h=p.wrap(width,max_h); p.drawOn(c,x,top-h); return h

def card(x,y,w,h,fill=WHITE,stroke=LINE,sw=1.1):
    c.setFillColor(fill); c.setStrokeColor(stroke); c.setLineWidth(sw); c.rect(x,y,w,h,fill=1,stroke=1)

def rule(x1,y1,x2,y2,color=LINE,width=1):
    c.setStrokeColor(color); c.setLineWidth(width); c.line(x1,y1,x2,y2)

# Header
label(margin, H-23*mm, 'SYSTEM DESIGN LAB     /     2026', 9, BLUE, tracking=1.2)
c.setFillColor(INK); c.setFont('Helvetica-Bold', 31)
c.drawString(margin, H-39*mm, 'ORBIT SIS')
c.setFillColor(INK); c.setFont('Helvetica', 17)
c.drawString(margin+60*mm, H-38.4*mm, 'A correctness-first student information system')
paragraph(margin, H-45*mm, 220*mm,
          'Academic workflows with explicit invariants, observable system-design experiments, and measured trade-offs.',
          10, 14, MUTED, 'Helvetica')
# Snapshot tag
card(W-88*mm,H-48*mm,75*mm,18*mm,YELLOW)
label(W-84*mm,H-37*mm,'VERIFICATION SNAPSHOT',8,INK,tracking=.7)
label(W-84*mm,H-43*mm,'20 OCT 2026  ·  LOCAL TEST RUN',7.5,INK,'Helvetica')
rule(margin,H-54*mm,W-margin,H-54*mm,INK,1.4)

# Main row: UI proof and test status
left_x=margin; left_w=194*mm; right_x=left_x+left_w+7*mm; right_w=W-margin-right_x
main_top=H-61*mm; main_h=100*mm; main_y=main_top-main_h
card(left_x,main_y,left_w,main_h,WHITE)
label(left_x+5*mm,main_top-7*mm,'01  /  PRODUCT INTERFACE',8,BLUE,tracking=.7)
# Actual screenshot contained within card; preserve aspect ratio and avoid synthetic UI.
img_x=left_x+4*mm; img_y=main_y+4*mm; img_w=left_w-8*mm; img_h=main_h-15*mm
if SHOT.exists():
    c.drawImage(ImageReader(str(SHOT)),img_x,img_y,width=img_w,height=img_h,preserveAspectRatio=True,anchor='c',mask='auto')
else:
    label(img_x,img_y+img_h/2,'Screenshot unavailable',10,CORAL)
label(left_x+5*mm,main_y+1.5*mm,'Captured from the current React production build · synthetic/local data context',6.5,MUTED,'Helvetica')

card(right_x,main_y,right_w,main_h,INK,INK)
label(right_x+5*mm,main_top-7*mm,'02  /  CURRENT TEST EVIDENCE',8,YELLOW,tracking=.7)
# Four metrics in a two-by-two grid
metrics=[('23 / 23','PostgreSQL test suite'),('2 / 2','Concurrency invariants'),('7 / 7','UI sections captured'),('0','Browser JS errors observed')]
cell_w=(right_w-12*mm)/2; cell_h=25*mm
for i,(value,desc) in enumerate(metrics):
    col=i%2; row=i//2; xx=right_x+5*mm+col*(cell_w+2*mm); yy=main_top-14*mm-(row+1)*cell_h
    c.setFillColor(YELLOW if i in (0,1) else MINT); c.setFont('Helvetica-Bold',21); c.drawString(xx,yy+10*mm,value)
    paragraph(xx,yy+7*mm,cell_w,desc,8,10,WHITE,'Helvetica')
# caveat strip
c.setFillColor(MINT); c.rect(right_x,main_y,right_w,13*mm,fill=1,stroke=0)
paragraph(right_x+4*mm,main_y+9*mm,right_w-8*mm,
          '<b>POSTGRESQL VERIFIED</b> — PostgreSQL 17.11, isolated verification database, migrations and concurrency suite passed.',
          7.2,9,INK,'Helvetica')

# Lower row with architecture and benchmark
lower_top=main_y-7*mm; lower_h=100*mm; lower_y=lower_top-lower_h
col_gap=6*mm; col1_w=128*mm; col2_w=116*mm; col3_w=W-2*margin-col1_w-col2_w-2*col_gap
x1=margin; x2=x1+col1_w+col_gap; x3=x2+col2_w+col_gap
card(x1,lower_y,col1_w,lower_h,WHITE)
label(x1+5*mm,lower_top-7*mm,'03  /  ARCHITECTURE & INVARIANT',8,BLUE,tracking=.7)
# simple system flow
nodes=[('BROWSER',BLUE),('FASTAPI',CORAL),('POSTGRESQL',INK)]
node_y=lower_top-24*mm; node_w=31*mm; node_h=12*mm
for i,(name,col) in enumerate(nodes):
    xx=x1+6*mm+i*39*mm
    c.setFillColor(col);c.setStrokeColor(INK);c.setLineWidth(1);c.rect(xx,node_y,node_w,node_h,fill=1,stroke=1)
    c.setFillColor(WHITE);c.setFont('Helvetica-Bold',8);c.drawCentredString(xx+node_w/2,node_y+4.4*mm,name)
    if i<2:
        rule(xx+node_w,node_y+node_h/2,xx+39*mm-2*mm,node_y+node_h/2,INK,1.4)
        c.setFillColor(INK); c.setFont('Helvetica-Bold',10); c.drawCentredString(xx+35*mm,node_y+node_h/2-2,'›')
paragraph(x1+6*mm,node_y-5*mm,col1_w-12*mm,
          '<b>Source of truth:</b> PostgreSQL owns academic records and registrations. Cache speeds up suggestions; it never decides seat availability.',
          7.5,9.5,MUTED,'Helvetica')
# invariant badge
card(x1+6*mm,lower_y+7*mm,col1_w-12*mm,15*mm,YELLOW)
label(x1+10*mm,lower_y+16*mm,'ENROLLMENT INVARIANT',7,INK,tracking=.7)
c.setFillColor(INK);c.setFont('Helvetica-Bold',15);c.drawString(x1+10*mm,lower_y+9.5*mm,'0  ≤  enrolled_count  ≤  capacity')

card(x2,lower_y,col2_w,lower_h,WHITE)
label(x2+5*mm,lower_top-7*mm,'04  /  SYSTEM-DESIGN COMPONENTS',8,BLUE,tracking=.4)
components=[('Rate limiting','Token bucket; HTTP 429 metrics'),('Key-value store','Bounded TTL/LRU autocomplete cache'),('Consistent hashing','Virtual-node routing experiment'),('Sharding','Synthetic in-memory records'),('Unique IDs','Time-sortable 64-bit generator'),('URL shortener','Persistent code → redirect'),('Crawler','Bounded same-host HTTPS crawler'),('Autocomplete','Course code/title prefix search')]
for i,(name,desc) in enumerate(components):
    yy=lower_top-15*mm-i*7.2*mm
    c.setFillColor(CORAL if i%2==0 else BLUE);c.circle(x2+6*mm,yy+1.1*mm,1.1*mm,fill=1,stroke=0)
    label(x2+9*mm,yy,name,7.6,INK,'Helvetica-Bold')
    label(x2+43*mm,yy,desc,6.6,MUTED,'Helvetica')

card(x3,lower_y,col3_w,lower_h,WHITE)
label(x3+5*mm,lower_top-7*mm,'05  /  PRIOR BENCHMARK CONTEXT',8,BLUE,tracking=.3)
paragraph(x3+5*mm,lower_top-13*mm,col3_w-10*mm,
          'Prior local baseline: 19 Oct, PostgreSQL 17, synthetic data, 10 users. Historical figures below were not rerun on 20 Oct.',
          7.3,9.3,MUTED,'Helvetica')
bench=[('Course search','35.82 req/s','p95 10 ms'),('Profile reads','35.27 req/s','p95 12 ms'),('Registration writes','19.47 req/s','p95 83 ms'),('Autocomplete cache ON','35.55 req/s','p95 5 ms')]
for i,(name,rps,p95) in enumerate(bench):
    yy=lower_top-32*mm-i*9.5*mm
    rule(x3+5*mm,yy+4*mm,x3+col3_w-5*mm,yy+4*mm,colors.HexColor('#D8D5CA'),.5)
    label(x3+5*mm,yy,name,7.3,INK,'Helvetica-Bold')
    label(x3+5*mm,yy-4*mm,rps,7.2,BLUE,'Helvetica-Bold')
    label(x3+col3_w-5*mm-stringWidth(p95,'Helvetica',7),yy-4*mm,p95,7,MUTED,'Helvetica')

# Footer: limitations and primary design references
footer_y=8*mm
rule(margin,footer_y+10*mm,W-margin,footer_y+10*mm,INK,1.2)
paragraph(margin,footer_y+7*mm,W-2*margin,
          '<b>Interpretation.</b> Full PostgreSQL suite and concurrent enrollment invariants passed on an isolated local database. Cache/rate limiting are process-local; shard routing does not migrate data. Live crawling is unverified. Benchmarks are not production capacity claims.',
          7.2,9.3,MUTED,'Helvetica')
label(margin,footer_y-1*mm,'DESIGN BASIS',6.5,BLUE,tracking=.8)
label(margin+25*mm,footer_y-1*mm,'NN/G visual hierarchy  ·  GOV.UK type scale & button guidance  ·  Home Office accessible layout/typography',6.5,MUTED,'Helvetica')
label(W-margin-38*mm,footer_y-1*mm,'ORBIT SIS / 2026',6.5,INK,'Helvetica-Bold')

c.showPage(); c.save()
print(f'Created {OUT}')
