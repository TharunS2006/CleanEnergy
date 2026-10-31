"""Replaces the four per-student bonafide pages of the Decidable Language Analyzer report with ONE certificate
that lists all names and register numbers together, without the underlined blanks. Every other page is kept as it is;
printed page numbers and the table of contents are shifted by the three pages that were removed."""
import io, sys
sys.path.insert(0, "/tmp/claude-0/s/dla")
from pdfops import PdfReader, ContentStream, blocks, strip
from pypdf import PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

SRC = sys.argv[1]; OUT = sys.argv[2]
FD = "/usr/share/fonts/truetype/liberation/"
pdfmetrics.registerFont(TTFont("Serif", FD + "LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Serif-B", FD + "LiberationSerif-Bold.ttf"))
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-B", italic="Serif", boldItalic="Serif-B")
W, H = 594.96, 841.92
STUDENTS = [("SURENDAR HARIPRASAD", "111624102215"), ("E THAMILNIDHI", "111624102219"),
            ("TAMIL MANI B", "111624102217"), ("THARUN", "111624102222")]
REMOVED = 3                       # pages 3, 4, 5 (the other three per-student certificates)

def overlay(draw):
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(W, H)); draw(c); c.save(); buf.seek(0)
    return PdfReader(buf).pages[0]

def white(c, x0, top, x1, bottom):
    c.setFillColorRGB(1, 1, 1); c.setStrokeColorRGB(1, 1, 1); c.rect(x0, H - bottom, x1 - x0, bottom - top, fill=1, stroke=0)

def ytop(top):                    # top-based point -> PDF y
    return H - top

# ------------------------------------------------------------------ certificate page
def cert(c):
    names = [n for n, _ in STUDENTS]; regs = [r for _, r in STUDENTS]
    names_txt = ", ".join(names[:-1]) + " and " + names[-1]
    regs_txt = ", ".join(regs[:-1]) + " and " + regs[-1]
    body = ParagraphStyle("b", fontName="Serif", fontSize=12, leading=21, alignment=TA_JUSTIFY)
    p1 = Paragraph(f"This is to certify that <b>{names_txt}</b>, bearing <b>Register Numbers {regs_txt}</b> respectively, of "
                   f"<b>3rd Year, 5th Semester, Department of Computer Science and Engineering</b>, have successfully completed "
                   f"the mini project entitled <b>“Decidable Language Analyzer”</b> during the academic year <b>2026–2027</b> "
                   f"under my guidance and supervision.", body)
    p2 = Paragraph("The work submitted in this report is a bonafide record of the work carried out by the student/team as part "
                   "of the academic requirements of the course.", body)
    width = 454
    _, h1 = p1.wrap(width, 400); p1.drawOn(c, 72, ytop(290) - h1 - 0)
    _, h2 = p2.wrap(width, 400); p2.drawOn(c, 72, ytop(290) - h1 - h2)
    base = 514.3
    c.setFont("Serif-B", 12); c.drawString(77, ytop(base + 10.3), "Name of the Student")
    c.setFont("Serif-B", 11); c.drawString(393, ytop(base + 10.3), "Project Guide")
    c.setFont("Serif", 12)
    for k, n in enumerate(names):
        c.drawString(77, ytop(535.3 + 21 * k + 10.3), n)

def page_no(n):
    def d(c):
        c.setFont("Serif", 11); c.drawRightString(523.0, ytop(792.9), str(n))
    return d

TOC_NEW = {}
def toc(c):
    c.setFont("Serif", 12)
    rows = [(204.6, 8), (245.8, 10), (287.1, 11), (327.6, 12), (368.8, 14), (410.1, 18), (450.6, 26), (491.8, 27)]
    for top, old in rows:
        c.drawCentredString(419.8, ytop(top + 10.4), str(old - REMOVED))

r = PdfReader(SRC); w = PdfWriter()
assert len(r.pages) == 27
w.add_page(r.pages[0])
p = r.pages[1]; strip(p, r, lambda x, y: y < 280); p.merge_page(overlay(cert)); w.add_page(p)
for idx in range(5, 27):
    p = r.pages[idx]
    if idx == 6:
        strip(p, r, lambda x, y: not (x > 405 and 200 < y < 520)); p.merge_page(overlay(toc))
    if idx >= 7:                                   # printed page number = last text block on the page
        cs = ContentStream(p.get_contents(), r); bl = blocks(cs.operations); s, e, _, _ = bl[-1]
        a, b = s, e
        if a > 0 and cs.operations[a - 1][1] == b"BDC" and b + 1 < len(cs.operations) and cs.operations[b + 1][1] == b"EMC": a, b = a - 1, b + 1
        cs.operations = [o for k, o in enumerate(cs.operations) if not (a <= k <= b)]; p.replace_contents(cs)
        p.merge_page(overlay(page_no(idx + 1 - REMOVED)))
    w.add_page(p)
w.add_metadata({"/Title": "Decidable Language Analyzer - Project Report"})
w.write(OUT)
print("pages", len(w.pages))
