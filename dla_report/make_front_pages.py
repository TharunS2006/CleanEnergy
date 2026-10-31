"""Cover page + single bonafide certificate for another project, in the same format as the Decidable Language Analyzer report.
usage: make_front_pages.py <source report pdf> <out pdf>   (title and members are set below)"""
import io, sys
sys.path.insert(0, "/tmp/claude-0/s/dla")
from pdfops import PdfReader, strip
from pypdf import PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

TITLE = "Automata-Based URL Validator"
STUDENTS = [("A.VISHNU VARDHAN", "111624102241"), ("VISHWAJITH R", "111624102242"),
            ("YOGESH S", "111624102246"), ("YUVARAJ U", "111624102247")]
SRC, OUT = sys.argv[1], sys.argv[2]
FD = "/usr/share/fonts/truetype/liberation/"
pdfmetrics.registerFont(TTFont("Serif", FD + "LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Serif-B", FD + "LiberationSerif-Bold.ttf"))
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-B", italic="Serif", boldItalic="Serif-B")
W, H = 594.96, 841.92
ytop = lambda t: H - t

def overlay(draw):
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(W, H)); draw(c); c.save(); buf.seek(0)
    return PdfReader(buf).pages[0]

def cover(c):
    c.setFont("Serif-B", 18); c.drawCentredString(297.6, ytop(95), TITLE.upper())
    c.setFont("Serif-B", 14)
    for k, (n, reg) in enumerate(STUDENTS):
        base = 260 + 22 * k
        c.drawCentredString(149.0, ytop(base), reg); c.drawCentredString(400.0, ytop(base), n)

def cert(c):
    names = [n for n, _ in STUDENTS]; regs = [r for _, r in STUDENTS]
    nt = ", ".join(names[:-1]) + " and " + names[-1]; rt = ", ".join(regs[:-1]) + " and " + regs[-1]
    st = ParagraphStyle("b", fontName="Serif", fontSize=12, leading=21, alignment=TA_JUSTIFY)
    p1 = Paragraph(f"This is to certify that <b>{nt}</b>, bearing <b>Register Numbers {rt}</b> respectively, of "
                   f"<b>3rd Year, 5th Semester, Department of Computer Science and Engineering</b>, have successfully completed "
                   f"the mini project entitled <b>“{TITLE}”</b> during the academic year <b>2026–2027</b> under my guidance and supervision.", st)
    p2 = Paragraph("The work submitted in this report is a bonafide record of the work carried out by the student/team as part "
                   "of the academic requirements of the course.", st)
    _, h1 = p1.wrap(454, 400); p1.drawOn(c, 72, ytop(290) - h1)
    _, h2 = p2.wrap(454, 400); p2.drawOn(c, 72, ytop(290) - h1 - h2)
    c.setFont("Serif-B", 12); c.drawString(77, ytop(524.6), "Name of the Student")
    c.setFont("Serif-B", 11); c.drawString(393, ytop(524.6), "Project Guide")
    c.setFont("Serif", 12)
    for k, n in enumerate(names): c.drawString(77, ytop(545.6 + 21 * k), n)

r = PdfReader(SRC); w = PdfWriter()
p = r.pages[0]; strip(p, r, lambda x, y: not (y < 100 or 250 < y < 335)); p.merge_page(overlay(cover)); w.add_page(p)
p = r.pages[1]; strip(p, r, lambda x, y: y < 280); p.merge_page(overlay(cert)); w.add_page(p)
w.add_metadata({"/Title": TITLE + " - Project Report (cover and bonafide)"})
w.write(OUT); print("ok", len(w.pages))
