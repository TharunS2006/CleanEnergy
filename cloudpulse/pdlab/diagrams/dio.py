"""Plain, slightly hand-drawn diagram helpers (draw.io-like palette, wobbly lines, ordinary fonts)."""
import random
from html import escape

FONT = "Liberation Sans, Arial, sans-serif"
PAL = {"blue": ("#dae8fc", "#6c8ebf"), "green": ("#d5e8d4", "#82b366"), "yellow": ("#fff2cc", "#d6b656"),
       "orange": ("#ffe6cc", "#d79b00"), "red": ("#f8cecc", "#b85450"), "purple": ("#e1d5e7", "#9673a6"),
       "grey": ("#f5f5f5", "#666666"), "white": ("#ffffff", "#333333")}


class D:
    def __init__(self, w, h, seed=7, jitter=1.3):
        self.w, self.h, self.p, self.r, self.j = w, h, [], random.Random(seed), jitter
        self.p.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                      '<path d="M0,1 L10,5 L0,9 z" fill="#222"/></marker></defs>')

    def _j(self, v):
        return v + self.r.uniform(-self.j, self.j)

    def add(self, s):
        self.p.append(s)

    def text(self, x, y, lines, size=16, bold=False, anchor="middle", color="#111", italic=False, lh=1.25):
        lines = lines if isinstance(lines, list) else [lines]
        for i, t in enumerate(lines):
            self.add(f'<text x="{x}" y="{y + i * size * lh}" font-family="{FONT}" font-size="{size}" '
                     f'font-weight="{"700" if bold else "400"}" font-style="{"italic" if italic else "normal"}" '
                     f'text-anchor="{anchor}" fill="{color}">{escape(t)}</text>')

    def box(self, x, y, w, h, lines, kind="blue", size=16, bold=False, dashed=False, top=False, sub=None):
        f, s = PAL[kind]
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        d = "M" + " L".join(f"{self._j(a):.1f},{self._j(b):.1f}" for a, b in pts) + " Z"
        da = ' stroke-dasharray="7 5"' if dashed else ""
        self.add(f'<path d="{d}" fill="{f}" stroke="{s}" stroke-width="1.8" stroke-linejoin="round"{da}/>')
        lines = lines if isinstance(lines, list) else [lines]
        if top:
            self.text(x + 10, y + size + 6, lines, size, bold, "start")
        else:
            n = len(lines)
            self.text(x + w / 2, y + h / 2 - (n - 1) * size * 0.625 + size * 0.35, lines, size, bold)

    def group(self, x, y, w, h, title, kind="grey", size=15):
        f, s = PAL[kind]
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{s}" stroke-width="1.6" stroke-dasharray="8 5"/>')
        self.text(x + 10, y + size + 4, title, size, True, "start", "#333")

    def ellipse(self, cx, cy, rx, ry, lines, kind="yellow", size=15):
        f, s = PAL[kind]
        self.add(f'<ellipse cx="{self._j(cx):.1f}" cy="{self._j(cy):.1f}" rx="{rx}" ry="{ry}" fill="{f}" stroke="{s}" stroke-width="1.8"/>')
        lines = lines if isinstance(lines, list) else [lines]
        self.text(cx, cy - (len(lines) - 1) * size * 0.625 + size * 0.35, lines, size)

    def diamond(self, cx, cy, w, h, lines, kind="yellow", size=14):
        f, s = PAL[kind]
        pts = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
        d = "M" + " L".join(f"{self._j(a):.1f},{self._j(b):.1f}" for a, b in pts) + " Z"
        self.add(f'<path d="{d}" fill="{f}" stroke="{s}" stroke-width="1.8"/>')
        lines = lines if isinstance(lines, list) else [lines]
        self.text(cx, cy - (len(lines) - 1) * size * 0.625 + size * 0.35, lines, size)

    def cylinder(self, x, y, w, h, lines, kind="green", size=15):
        f, s = PAL[kind]; ry = 11
        self.add(f'<path d="M{x},{y + ry} L{x},{y + h - ry} A{w / 2},{ry} 0 0 0 {x + w},{y + h - ry} L{x + w},{y + ry} Z" fill="{f}" stroke="{s}" stroke-width="1.8"/>')
        self.add(f'<ellipse cx="{x + w / 2}" cy="{y + ry}" rx="{w / 2}" ry="{ry}" fill="{f}" stroke="{s}" stroke-width="1.8"/>')
        lines = lines if isinstance(lines, list) else [lines]
        self.text(x + w / 2, y + h / 2 + 4 - (len(lines) - 1) * size * 0.6, lines, size)

    def actor(self, cx, y, label, size=15):
        s = "#333"
        self.add(f'<g fill="none" stroke="{s}" stroke-width="2" stroke-linecap="round"><circle cx="{cx}" cy="{y + 9}" r="9"/>'
                 f'<path d="M{cx},{y + 18} L{cx},{y + 44} M{cx - 15},{y + 28} L{cx + 15},{y + 28} M{cx},{y + 44} L{cx - 13},{y + 64} M{cx},{y + 44} L{cx + 13},{y + 64}"/></g>')
        self.text(cx, y + 82, label if isinstance(label, list) else [label], size)

    def arrow(self, pts, label=None, dashed=False, both=False, lx=None, ly=None, size=13, side="above"):
        pts = [(self._j(a) if 0 < i < len(pts) - 1 else a, self._j(b) if 0 < i < len(pts) - 1 else b) for i, (a, b) in enumerate(pts)]
        d = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
        da = ' stroke-dasharray="6 4"' if dashed else ""
        ms = ' marker-start="url(#a)"' if both else ""
        self.add(f'<path d="{d}" fill="none" stroke="#222" stroke-width="1.6" stroke-linejoin="round"{da} marker-end="url(#a)"{ms}/>')
        if label:
            (x1, y1), (x2, y2) = pts[0], pts[-1]
            mx = lx if lx is not None else (x1 + x2) / 2
            my = ly if ly is not None else (y1 + y2) / 2 - 6
            lines = label if isinstance(label, list) else [label]
            wd = max(len(t) for t in lines) * size * 0.52 + 8
            self.add(f'<rect x="{mx - wd / 2:.1f}" y="{my - size:.1f}" width="{wd:.1f}" height="{size * 1.25 * len(lines) + 2:.1f}" fill="#fff" opacity="0.85"/>')
            self.text(mx, my, lines, size)

    def render(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                f'<rect width="{self.w}" height="{self.h}" fill="#fff"/>' + "".join(self.p) + "</svg>")

    def save(self, name):
        import subprocess, pathlib
        pathlib.Path(name + ".svg").write_text(self.render())
        subprocess.run(["node", "render.js", name + ".svg", name + ".png", str(self.w), str(self.h)], check=True)
