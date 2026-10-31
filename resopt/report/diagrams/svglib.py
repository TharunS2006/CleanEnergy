"""Tiny SVG helper used to draw the report's architecture diagrams by hand-placed coordinates."""
from html import escape

FONT = "Liberation Sans, Arial, Helvetica, sans-serif"
INK, MUTE, LINE = "#1f2933", "#52606d", "#9aa5b1"
AZ, AZ_D, AZ_L = "#0f6cbd", "#0b4f8a", "#e6f1fb"      # Azure-ish blue
APP, APP_D, APP_L = "#1f7a6d", "#14564c", "#e5f4f1"   # CloudPulse teal
DATA, DATA_D, DATA_L = "#7a5c1f", "#5a4314", "#fbf3df"
SEC, SEC_D, SEC_L = "#a4372b", "#7d261c", "#fbe9e6"
USR, USR_D, USR_L = "#4b4f8a", "#33366b", "#eceefa"
EXT, EXT_D, EXT_L = "#5b6770", "#3e4850", "#eef0f2"


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.parts = w, h, []
        self.parts.append(f'''<defs>
<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>
<marker id="arrB" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{AZ}"/></marker>
<marker id="arrR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{SEC}"/></marker>
<marker id="arrG" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{APP}"/></marker>
</defs>''')

    def add(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, fill="#fff", stroke=LINE, sw=1.5, rx=8, dash=None, op=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} opacity="{op}"/>')

    def text(self, x, y, s, size=17, weight="400", fill=INK, anchor="start", italic=False, family=None):
        st = ' font-style="italic"' if italic else ""
        fam = family or FONT
        self.add(f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{st}>{escape(s)}</text>')

    def lines(self, x, y, ss, size=17, lh=None, **kw):
        lh = lh or size * 1.28
        for i, s in enumerate(ss):
            self.text(x, y + i * lh, s, size, **kw)

    def line(self, pts, stroke=INK, sw=2, dash=None, marker="arr", start=False):
        d = " ".join(("M" if i == 0 else "L") + f"{x},{y}" for i, (x, y) in enumerate(pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        ms = f' marker-end="url(#{marker})"' if marker else ""
        mst = f' marker-start="url(#{marker})"' if start else ""
        self.add(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"{da}{ms}{mst}/>')

    def badge(self, x, y, n, fill=INK, r=13):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>')
        self.text(x, y + 6, str(n), 16, "700", "#fff", "middle")

    def zone(self, x, y, w, h, title, color, light, dash="7 5"):
        self.rect(x, y, w, h, fill=light, stroke=color, sw=2, rx=12, dash=dash, op=1)
        tw = 10.2 * len(title) + 34
        self.rect(x + 16, y - 15, tw, 30, fill=color, stroke=color, rx=6)
        self.text(x + 29, y + 6, title, 16, "700", "#fff")

    def box(self, x, y, w, h, title, sub=None, color=APP, light="#fff", icon=None, tsize=17, ssize=14.5):
        self.rect(x, y, w, h, fill=light, stroke=color, sw=1.8, rx=8)
        self.rect(x, y, 7, h, fill=color, stroke=color, rx=3)
        tx = x + 20
        if icon:
            icon(self, x + 22, y + h / 2, color)
            tx = x + 52
        if sub:
            self.text(tx, y + 25, title, tsize, "700", INK)
            self.lines(tx, y + 25 + ssize * 1.45, sub if isinstance(sub, list) else [sub], ssize, fill=MUTE)
        else:
            self.text(tx, y + h / 2 + 6, title, tsize, "700", INK)

    def render(self, title=""):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                f'<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>' + "".join(self.parts) + "</svg>")


# ---- icons (drawn centred on x,y, ~26px) ---------------------------------
def i_key(s, x, y, c):
    s.add(f'<g fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round"><circle cx="{x-6}" cy="{y}" r="7"/><path d="M{x+1},{y} L{x+16},{y} M{x+11},{y} L{x+11},{y+6} M{x+16},{y} L{x+16},{y+6}"/></g>')

def i_shield(s, x, y, c):
    s.add(f'<path d="M{x},{y-14} L{x+13},{y-9} L{x+13},{y+2} Q{x+13},{y+11} {x},{y+16} Q{x-13},{y+11} {x-13},{y+2} L{x-13},{y-9} z" fill="none" stroke="{c}" stroke-width="2.4"/><path d="M{x-6},{y+1} L{x-1},{y+6} L{x+7},{y-5}" fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>')

def i_db(s, x, y, c):
    s.add(f'<g fill="none" stroke="{c}" stroke-width="2.2"><ellipse cx="{x}" cy="{y-9}" rx="12" ry="5"/><path d="M{x-12},{y-9} L{x-12},{y+9} A12,5 0 0 0 {x+12},{y+9} L{x+12},{y-9}"/><path d="M{x-12},{y} A12,5 0 0 0 {x+12},{y}"/></g>')

def i_user(s, x, y, c):
    s.add(f'<g fill="none" stroke="{c}" stroke-width="2.4"><circle cx="{x}" cy="{y-6}" r="6"/><path d="M{x-12},{y+14} Q{x-12},{y+3} {x},{y+3} Q{x+12},{y+3} {x+12},{y+14}"/></g>')

def i_cloud(s, x, y, c):
    s.add(f'<path d="M{x-12},{y+8} Q{x-18},{y+8} {x-17},{y+1} Q{x-16},{y-4} {x-10},{y-4} Q{x-8},{y-14} {x+2},{y-13} Q{x+11},{y-12} {x+11},{y-3} Q{x+19},{y-3} {x+18},{y+4} Q{x+17},{y+8} {x+11},{y+8} z" fill="none" stroke="{c}" stroke-width="2.3" stroke-linejoin="round"/>')

def i_gear(s, x, y, c):
    s.add(f'<g fill="none" stroke="{c}" stroke-width="2.4"><circle cx="{x}" cy="{y}" r="5"/><circle cx="{x}" cy="{y}" r="11" stroke-dasharray="4 3.2"/></g>')

def i_chart(s, x, y, c):
    s.add(f'<g fill="{c}"><rect x="{x-12}" y="{y+1}" width="6" height="12" rx="1"/><rect x="{x-3}" y="{y-7}" width="6" height="20" rx="1"/><rect x="{x+6}" y="{y-13}" width="6" height="26" rx="1"/></g>')

def i_server(s, x, y, c):
    s.add(f'<g fill="none" stroke="{c}" stroke-width="2.2"><rect x="{x-13}" y="{y-13}" width="26" height="10" rx="2"/><rect x="{x-13}" y="{y+2}" width="26" height="10" rx="2"/></g><circle cx="{x+7}" cy="{y-8}" r="1.8" fill="{c}"/><circle cx="{x+7}" cy="{y+7}" r="1.8" fill="{c}"/>')

def i_clock(s, x, y, c):
    s.add(f'<g fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round"><circle cx="{x}" cy="{y}" r="12"/><path d="M{x},{y-7} L{x},{y} L{x+6},{y+4}"/></g>')

def i_lock(s, x, y, c):
    s.add(f'<g fill="none" stroke="{c}" stroke-width="2.4"><rect x="{x-10}" y="{y-3}" width="20" height="14" rx="3"/><path d="M{x-6},{y-3} L{x-6},{y-9} A6,6 0 0 1 {x+6},{y-9} L{x+6},{y-3}"/></g>')

def i_doc(s, x, y, c):
    s.add(f'<g fill="none" stroke="{c}" stroke-width="2.2"><path d="M{x-9},{y-13} L{x+4},{y-13} L{x+10},{y-7} L{x+10},{y+13} L{x-9},{y+13} z"/><path d="M{x-4},{y-1} L{x+5},{y-1} M{x-4},{y+5} L{x+5},{y+5}"/></g>')
