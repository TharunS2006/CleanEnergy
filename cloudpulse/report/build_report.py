"""Build the CloudPulse mini-project report (DOCX) and convert it to PDF.
Two passes: the first lays the document out, the second writes the real page numbers
into the table of contents and the list of figures and tables."""
import re, subprocess, sys, pathlib
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from docbuilder import Report, _set_font, _shade
import content_ch1_3 as c13, content_ch4_5 as c45, content_ch6_8 as c68

HERE = pathlib.Path(__file__).parent
TITLE = "CLOUDPULSE: A CLOUD COST MONITORING AND OPTIMISATION PLATFORM WITH OWNERSHIP ATTRIBUTION AND VERIFIED SAVINGS"
TITLE_TC = "CloudPulse: A Cloud Cost Monitoring and Optimisation Platform with Ownership Attribution and Verified Savings"
CHAPTERS = ["Introduction", "Objectives", "Tools and Technologies", "Architecture Diagram", "Methodology", "Results", "Conclusion", "Reference"]

ABSTRACT = (
    "Cloud spending is easy to start and hard to control. Organisations running workloads on Microsoft Azure and Amazon Web "
    "Services routinely pay for resources that nobody uses: virtual machines shut down the wrong way that still bill for "
    "compute, disks and snapshots left behind when a project ends, and public IP addresses attached to nothing. Most cost "
    "tools stop at a dashboard that reports how much was spent, leaving the decisions about who should act, and whether the "
    "action helped, to people. This project presents CloudPulse, a cloud cost monitoring and optimisation platform that "
    "carries each cost problem through a complete loop: signal, context, finding, ownership, action and verification. "
    "CloudPulse signs in to an Azure subscription with a read-only service principal holding only the Reader and Cost "
    "Management Reader roles, and reads the bill, resource inventory, virtual machine metrics, Azure Advisor recommendations "
    "and the Activity Log through a small custom REST client. Rule-based detectors and transparent statistics, namely a "
    "weekday-aware robust z-score for spend anomalies, Holt's linear smoothing for month-end and budget forecasts, and a "
    "percentile verdict for idle and oversized machines, turn this data into de-duplicated findings. Each finding is priced "
    "per month, scored from P1 to P4, assigned to the person who created the resource, and tracked through a defined "
    "lifecycle. A saving is counted only after seven days of billed cost confirm the drop, and a fixed resource that "
    "returns reopens its finding. The system uses Python, FastAPI, SQLAlchemy and a framework-free JavaScript interface, "
    "encrypts stored cloud secrets with Fernet, and is validated by 27 automated tests and a scripted Azure environment "
    "that plants real waste. On the bundled FOCUS sample bill CloudPulse reported $262.94 a month of open waste and "
    "$33.44 a month of verified savings at 94% estimate accuracy.")


def centre(r, text, size=12, bold=True, italic=False, before=0, after=0, spacing=1.15):
    return r.para(text, align="c", size=size, bold=bold, italic=italic, before=before, after=after, spacing=spacing)


def cover(r):
    centre(r, TITLE, 15, before=40, after=22, spacing=1.3)
    centre(r, "A PROJECT REPORT", 13, after=26)
    centre(r, "Submitted by", 12, italic=True, after=22)
    t = r.doc.add_table(rows=1, cols=2)
    for cell, txt in zip(t.rows[0].cells, ("[REGISTER NUMBER]", "[STUDENT NAME]")):
        cell.text = ""
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_font(p.add_run(txt), 12, True)
    centre(r, "", after=14)
    centre(r, "in partial fulfillment for the award of the degree", 12, italic=True, after=6)
    centre(r, "of", 12, italic=True, after=6)
    centre(r, "BACHELOR OF ENGINEERING", 12, after=6)
    centre(r, "in", 12, italic=True, after=6)
    centre(r, "COMPUTER SCIENCE AND ENGINEERING", 12, after=26)
    centre(r, "R. M. K. COLLEGE OF ENGINEERING AND TECHNOLOGY", 12, after=2)
    centre(r, "(An Autonomous Institution)", 10, after=14)
    centre(r, "PUDUVOYAL", 12, after=10)
    p = r.doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(HERE / "assets/crest_cover.png"), width=Cm(2.6))
    centre(r, "OCTOBER 2026", 12, before=8)
    r.page_break()


def bonafide(r):
    t = r.doc.add_table(rows=1, cols=3)
    Report._fix_widths(t, (2.4, 10.7, 2.4))
    c0, c1, c2 = t.rows[0].cells
    c0.paragraphs[0].add_run().add_picture(str(HERE / "assets/crest_cover.png"), width=Cm(2.2))
    c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    c2.paragraphs[0].add_run().add_picture(str(HERE / "assets/iso.png"), width=Cm(2.1))
    def line(txt, size, color, bold=True, first=False):
        p = c1.paragraphs[0] if first else c1.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.0; p.paragraph_format.space_after = Pt(0)
        _set_font(p.add_run(txt), size, bold, color=color)
    line("R.M.K. COLLEGE OF ENGINEERING AND TECHNOLOGY", 13.5, "C00000", False, True)
    line("(An Autonomous Institution)", 11, "C55A11", False)
    for txt in ("R.S.M. Nagar, PUDUVOYAL-601 206", "Approved by AICTE, New Delhi /Affiliated to Anna University, Chennai",
                "Accredited by NBA, New Delhi (All Eligible Courses)/ NAAC with ‘A’ Grade",
                "An ISO 21001:2018 Certified Institution"):
        line(txt, 7.5, "843C0C")
    centre(r, "", after=18)
    centre(r, "BONAFIDE CERTIFICATE", 14, after=18)
    r.para("This is to certify that **Mr./Ms. ______________________________**, bearing **Register Number "
           "__________________**, of ______ **Year**, ______ **Semester**, **Department of Computer Science and Engineering**, "
           f"has successfully completed the mini project entitled **“{TITLE_TC}”** during the academic year **2026–2027** "
           "under my guidance and supervision.", spacing=1.5)
    r.para("The work submitted in this report is a bonafide record of the work carried out by the student/team as part of the "
           "academic requirements of the course.", spacing=1.5)
    centre(r, "", after=50)
    t = r.doc.add_table(rows=1, cols=2)
    for cell, txt in zip(t.rows[0].cells, ("Name of the Student", "Project Guide")):
        cell.text = ""
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_font(p.add_run(txt), 12, True)
    r.page_break()


def abstract(r):
    centre(r, "ABSTRACT", 14, after=14)
    r.para(ABSTRACT, spacing=1.5)
    r.page_break()


def toc(r, pages):
    centre(r, "TABLE OF CONTENTS", 14, after=14)
    t = r.doc.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    t.autofit = False
    w = (Cm(1.6), Cm(9.0), Cm(4.4))
    hdr = ("S.No", "Section", "Page No.")
    for i, (c, txt) in enumerate(zip(t.rows[0].cells, hdr)):
        c.width = w[i]; c.text = ""
        p = c.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_font(p.add_run(txt), 12, True)
    for i, name in enumerate(CHAPTERS, 1):
        cells = t.add_row().cells
        vals = (str(i), name, str(pages["chapters"].get(i, "")))
        for j, (c, txt) in enumerate(zip(cells, vals)):
            c.width = w[j]; c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(5); p.paragraph_format.space_after = Pt(5)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j != 1 else WD_ALIGN_PARAGRAPH.LEFT
            _set_font(p.add_run(txt), 12)
    Report._fix_widths(t, (1.6, 9.0, 4.4))
    r.para("", after=6)
    r.page_break()


def lists(r, captions, pages):
    centre(r, "LIST OF FIGURES AND TABLES", 13, after=4)
    for kind in ("Figure", "Table"):
        items = [c for c in captions if c.startswith(kind + " ")]
        r.para(kind + "s", align="l", size=11.5, bold=True, before=4, after=2, spacing=1.0)
        t = r.doc.add_table(rows=0, cols=2)
        for cap in items:
            m = re.match(r"(Figure|Table) (\d+\.\d+): (.*)", cap)
            cells = t.add_row().cells
            pass
            for c, txt, al in ((cells[0], f"{m.group(1)} {m.group(2)}  {m.group(3)}", WD_ALIGN_PARAGRAPH.LEFT),
                               (cells[1], str(pages["captions"].get(f"{m.group(1)} {m.group(2)}", "")), WD_ALIGN_PARAGRAPH.RIGHT)):
                c.text = ""
                p = c.paragraphs[0]; p.alignment = al
                p.paragraph_format.line_spacing = 1.0; p.paragraph_format.space_after = Pt(0)
                _set_font(p.add_run(txt), 9.5)
        Report._fix_widths(t, (14.0, 1.5))
    r.page_break()


def build(out_docx, pages, captions_hint):
    r = Report()
    cover(r); bonafide(r); abstract(r); toc(r, pages); lists(r, captions_hint, pages)
    r.start_body()
    c13.chapter1(r); r.page_break()
    c13.chapter2(r); r.page_break()
    c13.chapter3(r); r.page_break()
    c45.chapter4(r); r.page_break()
    c45.chapter5(r); r.page_break()
    c68.chapter6(r); r.page_break()
    c68.chapter7(r); r.page_break()
    c68.chapter8(r)
    r.save(out_docx)
    return r


def to_pdf(docx, outdir):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(docx)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)


def page_texts(pdf):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout).group(1))
    out = []
    for i in range(1, n + 1):
        out.append(subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", str(pdf), "-"],
                                  capture_output=True, text=True).stdout)
    return out


def locate(pdf, captions):
    texts = page_texts(pdf)
    heads = {1: "1. INTRODUCTION", 2: "2. OBJECTIVES", 3: "3. TOOLS AND TECHNOLOGIES", 4: "4. ARCHITECTURE DIAGRAM",
             5: "5. METHODOLOGY", 6: "6. RESULTS", 7: "7. CONCLUSION", 8: "8. REFERENCE"}
    start = next(i for i, t in enumerate(texts) if re.search(r"^\s*1\. INTRODUCTION\s*$", t, re.M))
    pages = {"chapters": {}, "captions": {}, "total": len(texts), "body_start": start + 1}
    for k, h in heads.items():
        for i in range(start, len(texts)):
            if re.search(rf"^\s*{re.escape(h)}\s*$", texts[i], re.M):
                pages["chapters"][k] = i - start + 1
                break
    for cap in captions:
        m = re.match(r"(Figure|Table) (\d+\.\d+):", cap)
        key = f"{m.group(1)} {m.group(2)}"
        for i in range(start, len(texts)):
            if re.search(rf"^\s*{re.escape(key)}:", texts[i], re.M):
                pages["captions"][key] = i - start + 1
                break
    return pages


if __name__ == "__main__":
    out = HERE / "output"; out.mkdir(exist_ok=True)
    docx = out / "CloudPulse_Mini_Project_Report.docx"
    empty = {"chapters": {}, "captions": {}}
    r = build(docx, empty, [])          # pass 0: discover captions
    caps = r.captions
    r = build(docx, {"chapters": {i: 99 for i in range(1, 9)}, "captions": {c.split(":")[0]: 99 for c in caps}}, caps)
    to_pdf(docx, out)
    pages = locate(out / "CloudPulse_Mini_Project_Report.pdf", caps)
    build(docx, pages, caps)
    to_pdf(docx, out)
    pages2 = locate(out / "CloudPulse_Mini_Project_Report.pdf", caps)
    if pages2["chapters"] != pages["chapters"] or pages2["captions"] != pages["captions"]:
        build(docx, pages2, caps); to_pdf(docx, out)
        pages2 = locate(out / "CloudPulse_Mini_Project_Report.pdf", caps)
    print("total pdf pages:", pages2["total"], "body starts at pdf page", pages2["body_start"])
    print("chapters:", pages2["chapters"])
