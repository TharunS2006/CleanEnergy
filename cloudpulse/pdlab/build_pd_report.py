"""Builds the PD Lab III report by editing the uploaded sample .docx in place, so that the cover, logos,
college details, Vision/Mission page and every style stay exactly as in the sample."""
import copy, pathlib, re, subprocess, sys
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph
from PIL import Image

import pd_content as C

HERE = pathlib.Path(__file__).parent
SAMPLE = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "sample.docx")
ASSETS = HERE.parent / "internship" / "assets"
OUT = HERE / "output"; OUT.mkdir(exist_ok=True)
DOCX = OUT / "PD_Lab_III_Report_CloudPulse.docx"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def set_text(p, text):
    first = None
    for ch in list(p):
        if ch.tag == qn("w:pPr"):
            continue
        if ch.tag == qn("w:r") and first is None and (ch.find(qn("w:t")) is not None or ch.find(qn("w:tab")) is not None):
            first = ch; continue
        p.remove(ch)
    for t in list(first):
        if t.tag in (qn("w:t"), qn("w:tab"), qn("w:br")):
            first.remove(t)
    t = OxmlElement("w:t"); t.set(XML_SPACE, "preserve"); t.text = text; first.append(t)
    return p


def pbb(p):
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        ppr = OxmlElement("w:pPr"); p.insert(0, ppr)
    e = OxmlElement("w:pageBreakBefore")
    st = ppr.find(qn("w:pStyle"))
    (st.addnext(e) if st is not None else ppr.insert(0, e))


def align(p, val):
    ppr = p.find(qn("w:pPr"))
    for j in ppr.findall(qn("w:jc")): ppr.remove(j)
    j = OxmlElement("w:jc"); j.set(qn("w:val"), val); ppr.append(j)


def title_case(s):
    small = {"of", "and", "in", "the", "for", "to", "a", "on"}
    w = s.lower().split()
    return " ".join(x if (i and x in small) else x.capitalize() for i, x in enumerate(w))


class Builder:
    def __init__(self):
        self.d = Document(SAMPLE)
        self.body = self.d.element.body
        self.els = list(self.body.iterchildren())
        e = self.els
        # templates (deep copies, taken before anything is removed)
        self.T = dict(ch=copy.deepcopy(e[159]), h1=copy.deepcopy(e[162]), h2=copy.deepcopy(e[167]), p=copy.deepcopy(e[172]),
                      obj=copy.deepcopy(e[240]), bul=copy.deepcopy(e[242]), num=copy.deepcopy(e[226]),
                      ref=copy.deepcopy(e[354]), h1abbr=copy.deepcopy(e[348]), refhead=copy.deepcopy(e[353]))
        self.heads = []          # (kind, number, title)
        self.caps = {"Figure": [], "Table": []}
        self.cnt = {"Figure": {}, "Table": {}}
        self.chapter = 0

    # --------------------------------------------------------------- factories
    def para(self, kind, text):
        p = copy.deepcopy(self.T[kind])
        set_text(p, text)
        return p

    def caption(self, kind, title):
        n = self.cnt[kind].get(self.chapter, 0) + 1
        self.cnt[kind][self.chapter] = n
        label = f"{kind} {self.chapter}.{n}"
        self.caps[kind].append((label, title))
        p = copy.deepcopy(self.T["obj"])
        set_text(p, f"{label}: {title}")
        ppr = p.find(qn("w:pPr"))
        for s in ppr.findall(qn("w:spacing")): ppr.remove(s)
        sp = OxmlElement("w:spacing"); sp.set(qn("w:after"), "200"); ppr.insert(0, sp)
        align(p, "center")
        if kind == "Table":
            p.find(qn("w:pPr")).insert(0, OxmlElement("w:keepNext"))
        rpr = OxmlElement("w:rPr")
        for tag in ("w:b", "w:sz"):
            x = OxmlElement(tag)
            if tag == "w:sz": x.set(qn("w:val"), "21")
            rpr.append(x)
        p.find(qn("w:r")).insert(0, rpr)
        return p, label

    def picture(self, path, width_cm=None, height_cm=None):
        p = copy.deepcopy(self.T["obj"])
        set_text(p, "")
        align(p, "center")
        ppr = p.find(qn("w:pPr"))
        for s in ppr.findall(qn("w:spacing")): ppr.remove(s)
        sp = OxmlElement("w:spacing"); sp.set(qn("w:after"), "120"); ppr.insert(0, sp)
        run = Paragraph(p, self.d._body).runs[0]
        kw = {"width": Cm(width_cm)} if width_cm else {"height": Cm(height_cm)}
        run.add_picture(str(path), **kw)
        return p

    def table(self, header, rows, widths, size=10, borders=True, bold_last=False, center_cols=(), pad=3):
        t = self.d.add_table(rows=1, cols=len(header))
        self.body.remove(t._tbl)
        tblPr = t._tbl.tblPr
        for ch in list(tblPr):
            tblPr.remove(ch)
        tw = OxmlElement("w:tblW"); tw.set(qn("w:w"), str(int(sum(widths) * 567))); tw.set(qn("w:type"), "dxa"); tblPr.append(tw)
        jc = OxmlElement("w:jc"); jc.set(qn("w:val"), "center"); tblPr.append(jc)
        if borders:
            bd = OxmlElement("w:tblBorders")
            for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
                x = OxmlElement(f"w:{side}"); x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "4"); x.set(qn("w:space"), "0"); x.set(qn("w:color"), "000000")
                bd.append(x)
            tblPr.append(bd)
        lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
        look = OxmlElement("w:tblLook"); look.set(qn("w:val"), "04A0"); tblPr.append(look)
        for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(int(w * 567)))

        def fill(cells, vals, bold=False, hdr=False):
            for i, (c, v) in enumerate(zip(cells, vals)):
                c.width = Cm(widths[i])
                p = c.paragraphs[0]
                p.paragraph_format.space_after = Pt(pad); p.paragraph_format.space_before = Pt(pad)
                p.paragraph_format.line_spacing = 1.5
                p.paragraph_format.left_indent = Cm(0.05); p.paragraph_format.right_indent = Cm(0.05)
                p.paragraph_format.first_line_indent = Cm(0)
                p.alignment = 1 if (hdr or i in center_cols) else 0
                r = p.add_run(str(v)); r.font.size = Pt(size); r.font.bold = bold or hdr
        fill(t.rows[0].cells, header, hdr=True)
        trPr = t.rows[0]._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
        for k, row in enumerate(rows):
            fill(t.add_row().cells, row, bold=bold_last and k == len(rows) - 1)
        for row in (t.rows[:-1] if len(rows) <= 14 else []):
            for c in row.cells:
                for pp in c.paragraphs: pp.paragraph_format.keep_with_next = True
        for r in t.rows:
            cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true"); r._tr.get_or_add_trPr().append(cs)
        return t._tbl

    def spacer(self):
        p = copy.deepcopy(self.T["obj"]); set_text(p, "")
        ppr = p.find(qn("w:pPr"))
        for s in ppr.findall(qn("w:spacing")): ppr.remove(s)
        sp = OxmlElement("w:spacing"); sp.set(qn("w:after"), "120"); ppr.insert(0, sp)
        return p

    # ------------------------------------------------------------------ chapters
    def para_lead(self, lead, text):
        p = copy.deepcopy(self.T["p"]); set_text(p, lead + " ")
        r1 = p.find(qn("w:r")); rp = r1.find(qn("w:rPr"))
        if rp is None:
            rp = OxmlElement("w:rPr"); r1.insert(0, rp)
        rp.append(OxmlElement("w:b"))
        r2 = OxmlElement("w:r"); t = OxmlElement("w:t"); t.set(XML_SPACE, "preserve"); t.text = text; r2.append(t); p.append(r2)
        return p

    def chapters(self):
        out = []
        for raw in (HERE / "content_src.txt").read_text().splitlines():
            if not raw.strip():
                continue
            k, _, rest = raw.partition("|")
            if k == "CH":
                num, _, ttl = rest.partition("|")
                self.chapter = int(num)
                p1 = self.para("ch", f"CHAPTER {num}"); p2 = self.para("ch", ttl)
                if int(num) > 1:
                    pbb(p1)
                out += [p1, p2]; self.heads.append(("ch", num, ttl))
            elif k == "H1":
                num, _, ttl = rest.partition("|")
                out.append(self.para("h1", f"{num} {ttl}")); self.heads.append(("h1", num, ttl))
            elif k == "P":
                out.append(self.para("p", rest))
            elif k == "PL":
                lead, _, txt = rest.partition("|")
                out.append(self.para_lead(lead, txt))
            elif k == "T":
                parts = rest.split("|")
                title, widths = parts[0], [float(x) for x in parts[-1].split(",")]
                header = re.split(r",(?! )", parts[1]); rows = [re.split(r",(?! )", r) for r in parts[2:-1]]
                cap, _ = self.caption("Table", title)
                out.append(cap)
                out.append(self.table(header, rows, widths, size=10.5, bold_last=(header[0] in ("Resource",))))
                out.append(self.spacer())
            elif k == "F":
                f, cap_t, w = rest.split("|")
                out.append(self.picture(ASSETS / f, width_cm=float(w)))
                cap, _ = self.caption("Figure", cap_t); out.append(cap)
        return out

    def abbreviations_and_refs(self):
        out = []
        h = copy.deepcopy(self.T["h1abbr"]); set_text(h, "LIST OF ABBREVIATIONS"); pbb(h); out.append(h)
        rows = [[f"{i}.", a, f] for i, (a, f) in enumerate(C.ABBREV, 1)]
        out.append(self.table(["No.", "Abbreviation", "Full Form"], rows, [1.4, 3.4, 11.0], size=12, borders=False, center_cols=(0,), pad=3.5))
        h = copy.deepcopy(self.T["refhead"]); set_text(h, "REFERENCES"); pbb(h); out.append(h)
        for r_ in C.REFS:
            pr = self.para("ref", r_)
            sp = pr.find(qn("w:pPr")).find(qn("w:spacing")); sp.set(qn("w:after"), "20")
            out.append(pr)
        return out

    # ------------------------------------------------------------------- build
    def build(self, pages):
        e = self.els
        # cover ------------------------------------------------------------
        title = set_text(e[9], C.TITLE)
        ppr = title.find(qn("w:pPr"))
        for ind in ppr.findall(qn("w:ind")): ppr.remove(ind)
        ppr.append(OxmlElement("w:ind")); ppr.find(qn("w:ind")).set(qn("w:left"), "0")
        align(title, "center")
        base = e[11]; anchor = e[13]
        for n, (name, reg) in enumerate(C.TEAM):
            if n < 3:
                p = (e[11], e[12], e[13])[n]
            else:
                p = copy.deepcopy(e[13]); anchor.addnext(p); anchor = p
            runs = p.findall(qn("w:r"))
            # normalise to: [tab][name][tab + reg] using the first paragraph's structure
            for ch in list(p):
                if ch.tag != qn("w:pPr"): p.remove(ch)
            r1 = OxmlElement("w:r"); r1.append(OxmlElement("w:tab")); p.append(r1)
            for txt, tabbed in ((name, False), (reg, True)):
                r = OxmlElement("w:r"); rp = OxmlElement("w:rPr"); sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "28"); rp.append(sz); r.append(rp)
                if tabbed: r.append(OxmlElement("w:tab"))
                t = OxmlElement("w:t"); t.text = txt; r.append(t); p.append(r)
            sp = p.find(qn("w:pPr")).find(qn("w:spacing")); sp.set(qn("w:after"), "120")
        # bonafide ----------------------------------------------------------
        names = ", ".join(f"“{n}” ({r})" for n, r in C.TEAM)
        set_text(e[29], f"Certified that this project report “{C.TITLE_SHORT}” is the bonafide work of {names}, who carried out "
                        "the project work under my supervision.")
        # abstract ----------------------------------------------------------
        for el, txt in zip((e[63], e[64], e[65]), C.ABSTRACT):
            set_text(el, txt)
        pbb(e[62])
        for el in (e[63], e[64], e[65]):
            ppr = el.find(qn("w:pPr"))
            for ind in ppr.findall(qn("w:ind")): ppr.remove(ind)
            ind = OxmlElement("w:ind"); ind.set(qn("w:left"), "0"); ind.set(qn("w:right"), "0"); ppr.append(ind)
            align(el, "both")
        # remove the Vision / Mission / PEO / PSO page and put the 7 policy pages in its place
        for i in list(range(38, 62)) + [30, 31, 32, 34, 35]:
            self.body.remove(e[i])
        anchor = e[37]
        for n in range(1, 8):
            p = copy.deepcopy(self.T["obj"]); set_text(p, "")
            ppr = p.find(qn("w:pPr"))
            for x in ppr.findall(qn("w:spacing")) + ppr.findall(qn("w:ind")): ppr.remove(x)
            sp = OxmlElement("w:spacing"); sp.set(qn("w:before"), "0"); sp.set(qn("w:after"), "0"); sp.set(qn("w:line"), "240"); sp.set(qn("w:lineRule"), "auto"); ppr.append(sp)
            pbb(p); align(p, "center")
            Paragraph(p, self.d._body).runs[0].add_picture(str(HERE / f"policy-{n}.png"), width=Cm(16.2))
            anchor.addnext(p); anchor = p
        # remove old TOC / lists / chapters --------------------------------
        for i in list(range(69, 124)) + list(range(124, 127)) + list(range(128, 136)) + list(range(137, 158)) + list(range(159, 361)):
            self.body.remove(e[i])
        # chapters first (collects headings and captions) -------------------
        sect = self.body.find(qn("w:sectPr"))
        ch_els = self.chapters()
        ch_els += self.abbreviations_and_refs()
        for el in ch_els:
            sect.addprevious(el)
        # TOC ---------------------------------------------------------------
        rows = [["", "ABSTRACT", pages.get("ABSTRACT", "")], ["", "LIST OF TABLES", pages.get("LIST OF TABLES", "")],
                ["", "LIST OF FIGURES", pages.get("LIST OF FIGURES", "")], ["", "LIST OF ABBREVIATIONS", pages.get("LIST OF ABBREVIATIONS", "")]]
        for kind, num, ttl in self.heads:
            if kind == "ch":
                rows.append([num, ttl, pages.get(("h", num), "")])
            else:
                label = title_case(ttl)
                rows.append([num, ("        " if kind == "h2" else "") + label, pages.get(("h", num), "")])
        rows.append(["", "REFERENCES", pages.get("REFERENCES", "")])
        toc = self.table(["CHAPTER NO", "TITLE", "PAGE"], rows, [2.6, 11.4, 2.0], size=12, borders=False, center_cols=(0,), pad=3.5)
        # bold chapter rows, right-align page numbers
        for tr in toc.findall(qn("w:tr"))[1:]:
            tcs = tr.findall(qn("w:tc"))
            num = "".join(t.text or "" for t in tcs[0].iter(qn("w:t")))
            ttl = "".join(t.text or "" for t in tcs[1].iter(qn("w:t")))
            if ("." not in num) or ttl in ("ABSTRACT", "LIST OF TABLES", "LIST OF FIGURES", "LIST OF ABBREVIATIONS", "REFERENCES"):
                for r in tcs[1].iter(qn("w:r")):
                    rp = r.find(qn("w:rPr"))
                    rb = rp.find(qn("w:b")) if rp is not None else None
                    if rb is not None and qn("w:val") in rb.attrib:
                        del rb.attrib[qn("w:val")]
            for p in tcs[2].iter(qn("w:p")):
                align(p, "right") if p.find(qn("w:pPr")) is not None else None
        e[68].addnext(toc)
        # lists ---------------------------------------------------------------
        sectpara = e[158]
        for kind, head in (("Table", e[127]), ("Figure", e[136])):
            pbb(head)
            sectpara.addprevious(head)
            items = self.caps[kind]
            rws = [[lab.split(" ", 1)[1], ttl, pages.get(lab, "")] for lab, ttl in items]
            tbl = self.table([f"{kind.upper()} NO", "TITLE", "PAGE NO"], rws, [2.6, 11.4, 2.0], size=12, borders=False, center_cols=(0, 2), pad=5.5)
            sectpara.addprevious(tbl)
        self.finish(e)
        self.d.save(DOCX)

    def finish(self, e):
        # box border, margins, page numbers on every section; 1.5 line spacing everywhere after the cover
        skip = set(id(x) for x in e[0:38] if x.getparent() is not None) | set(id(x) for x in e[0:24])
        for sp in self.body.iter(qn('w:sectPr')):
            _borders(sp)
        first = next(self.body.iter(qn('w:sectPr')))
        pm = first.find(qn('w:pgMar'))
        for k, v in (('left', 1134), ('right', 1134), ('top', 1021), ('bottom', 900)):
            pm.set(qn('w:' + k), str(v))
        for sec in self.d.sections:
            sec.footer.is_linked_to_previous = False
            fp = sec.footer.paragraphs[0]
            for ch in list(fp._p):
                if ch.tag != qn("w:pPr"): fp._p.remove(ch)
            fp.alignment = 1
            _pagefield(fp._p)
        for p in self.body.iter(qn('w:p')):
            if id(p) in skip:
                continue
            ppr = p.find(qn('w:pPr'))
            if ppr is None:
                ppr = OxmlElement('w:pPr'); p.insert(0, ppr)
            sp = ppr.find(qn('w:spacing'))
            if sp is None:
                sp = OxmlElement('w:spacing'); ppr.insert(0, sp)
            cur = int(sp.get(qn('w:line'), '0') or 0)
            if sp.get(qn('w:lineRule')) in (None, 'auto') and cur < 360 and p.find('.//' + qn('w:drawing')) is None:
                sp.set(qn('w:line'), '360'); sp.set(qn('w:lineRule'), 'auto')


def _borders(sect):
    for old in sect.findall(qn('w:pgBorders')):
        sect.remove(old)
    b = OxmlElement('w:pgBorders'); b.set(qn('w:offsetFrom'), 'page')
    for side in ('top', 'left', 'bottom', 'right'):
        x = OxmlElement('w:' + side); x.set(qn('w:val'), 'single'); x.set(qn('w:sz'), '8'); x.set(qn('w:space'), '24'); x.set(qn('w:color'), '000000'); b.append(x)
    sect.find(qn('w:pgMar')).addnext(b)


def _pagefield(p):
    def mk(t, **kw):
        el = OxmlElement(t)
        for k, v in kw.items(): el.set(qn(k), v)
        return el
    for kind in ('begin', 'instr', 'sep', 'txt', 'end'):
        r = OxmlElement('w:r')
        if kind == 'instr':
            it = mk('w:instrText'); it.set(XML_SPACE, 'preserve'); it.text = ' PAGE '; r.append(it)
        elif kind == 'txt':
            t = OxmlElement('w:t'); t.text = '1'; r.append(t)
        else:
            r.append(mk('w:fldChar', **{'w:fldCharType': {'begin': 'begin', 'sep': 'separate', 'end': 'end'}[kind]}))
        p.append(r)


def to_pdf():
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(DOCX)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    return OUT / DOCX.with_suffix(".pdf").name


def page_lines(pdf):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout).group(1))
    out = []
    for i in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
        out.append([re.sub(r"\s+", " ", l).strip() for l in t.splitlines()])
    return out


def locate(pdf, b):
    L = page_lines(pdf)
    start = next(i for i, ls in enumerate(L) if "CHAPTER 1" in ls)
    pages = {}
    def first(pred, frm=0):
        return next((i + 1 for i in range(frm, len(L)) if any(pred(l) for l in L[i])), "")
    def last(pred):
        r = [i + 1 for i in range(len(L)) if any(pred(l) for l in L[i])]
        return r[-1] if r else ""
    pages["ABSTRACT"] = first(lambda l: l == "ABSTRACT")
    for k in ("LIST OF TABLES", "LIST OF FIGURES", "LIST OF ABBREVIATIONS", "REFERENCES"):
        pages[k] = last(lambda l, k=k: l == k)
    for kind, num, ttl in b.heads:
        if kind == "ch":
            pages[("h", num)] = first(lambda l, n=num: l == f"CHAPTER {n}", start)
        else:
            pages[("h", num)] = first(lambda l, n=num, t=ttl: l.startswith(f"{n} {t[:28]}"), start)
    for kind in ("Figure", "Table"):
        for lab, ttl in b.caps[kind]:
            pages[lab] = first(lambda l, lab=lab: l.startswith(lab + ":"), start)
    return pages, len(L)


if __name__ == "__main__":
    pages = {}
    for _ in range(4):
        b = Builder(); b.build(pages); pdf = to_pdf()
        new, total = locate(pdf, b)
        if new == pages:
            break
        pages = new
    miss = [k for k, v in pages.items() if v == ""]
    print("pages:", total, "| missing:", miss)
