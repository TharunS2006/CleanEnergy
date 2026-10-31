from svglib import *

# ================= Figure 4.1: layered architecture =================
W, H = 900, 640
s = Svg(W, H)
s.text(450, 34, "Layers of the Automata-Based URL Validator", 21, "700", INK, "middle")
def layer(y, h, title, color, light):
    s.rect(30, y, 840, h, light, color, 2, 12, dash="7 5")
    s.rect(46, y - 14, 10.4 * len(title) + 30, 28, color, color, 1, 6)
    s.text(60, y + 6, title, 15.5, "700", "#fff")
layer(66, 116, "PRESENTATION", USR_D, USR_L)
s.box(60, 92, 250, 74, "Command line", ["urlvalidator.cli", "--trace, --info, --file"], USR_D, "#fff", i_gear)
s.box(340, 92, 250, 74, "Browser page", ["web/index.html (JS)", "single URL, batch, trace"], USR_D, "#fff", i_doc)
s.box(620, 92, 220, 74, "HTTP server", ["urlvalidator.server", "/api/validate, /api/batch"], USR_D, "#fff", i_server)
layer(220, 130, "APPLICATION", APP_D, APP_L)
s.box(60, 246, 250, 88, "validate(url)", ["runs the DFA, stops at the", "first dead state"], APP_D, "#fff", i_gear)
s.box(340, 246, 250, 88, "Error reporting", ["position, offending character,", "expected characters, hint"], APP_D, "#fff", i_shield)
s.box(620, 246, 220, 88, "Component split", ["scheme, host, port,", "path, query, fragment"], APP_D, "#fff", i_chart)
layer(388, 130, "AUTOMATA ENGINE", AZ_D, AZ_L)
bx = [(45, "Regex parser"), (213, "Thompson NFA"), (381, "Subset DFA"), (549, "Moore minimiser"), (717, "DFA runner")]
for x, t in bx:
    s.rect(x, 424, 138, 70, "#fff", AZ_D, 1.8, 8); s.text(x + 69, 464, t, 15.5, "700", INK, "middle")
for x1, x2 in ((183, 213), (351, 381), (519, 549), (687, 717)):
    s.line([(x1, 459), (x2, 459)], INK, 2.2)
layer(556, 70, "GRAMMAR", DATA_D, DATA_L)
s.rect(60, 576, 780, 38, "#fff", DATA_D, 1.8, 8)
s.text(450, 601, "grammar.py: scheme · host (name, IPv4, localhost) · port · path · query · fragment, written as one regular expression", 14.5, "400", INK, "middle")
for x in (260, 465, 730):
    s.line([(x, 166), (x, 246)], INK, 2)
for x in (260, 465, 730):
    s.line([(x, 334), (x, 388)], INK, 2)
s.line([(450, 518), (450, 556)], DATA_D, 2.2, marker="arr", start=True)
open("fig41.svg", "w").write(s.render())

# ================= Figure 4.2: build once, run per URL =================
W2, H2 = 900, 520
p = Svg(W2, H2)
p.text(450, 32, "Building the automaton once and using it for every URL", 21, "700", INK, "middle")
p.zone(30, 70, 840, 130, "BUILT ONCE AT START-UP (about 70 ms)", AZ_D, AZ_L)
steps = [(50, "URL grammar", "regular expression"), (222, "NFA", "618 states"), (394, "DFA", "299 states"), (566, "Minimal DFA", "258 states"), (738, "Tables", "258 × 29 cells")]
for x, a, b in steps:
    p.rect(x, 110, 142, 70, "#fff", AZ_D, 1.8, 8); p.text(x + 71, 140, a, 16.5, "700", INK, "middle"); p.text(x + 71, 164, b, 13.5, "400", MUTE, "middle")
for x1, x2, t in ((192, 222, "Thompson"), (364, 394, "subset"), (536, 566, "Moore"), (708, 738, "classes")):
    p.line([(x1, 145), (x2, 145)], INK, 2.2)
p.zone(30, 240, 840, 250, "FOR EVERY URL", APP_D, APP_L)
p.rect(60, 280, 160, 70, "#fff", APP_D, 1.8, 8); p.text(140, 310, "Input string", 16.5, "700", INK, "middle"); p.text(140, 332, "http://exa mple.com", 12.5, "400", MUTE, "middle")
p.rect(290, 280, 190, 70, "#fff", APP_D, 1.8, 8); p.text(385, 308, "Read one character", 16, "700", INK, "middle"); p.text(385, 330, "q = delta[q][class(c)]", 13.5, "400", MUTE, "middle")
p.line([(220, 315), (290, 315)], INK, 2.2)
p.rect(550, 280, 150, 70, DATA_L, DATA_D, 1.8, 8); p.text(625, 308, "Dead state?", 16, "700", INK, "middle"); p.text(625, 330, "q cannot reach accept", 12.5, "400", MUTE, "middle")
p.line([(480, 315), (550, 315)], INK, 2.2)
p.rect(740, 270, 110, 50, SEC_L, SEC_D, 1.8, 8); p.text(795, 291, "INVALID", 15, "700", SEC_D, "middle"); p.text(795, 310, "at position i", 12.5, "400", MUTE, "middle")
p.line([(700, 300), (740, 295)], SEC_D, 2.2, marker="arrR"); p.text(716, 288, "yes", 13, "700", SEC_D, "middle")
p.line([(625, 350), (625, 390), (385, 390), (385, 350)], APP_D, 2, dash="7 4", marker="arrG")
p.text(505, 383, "no: next character", 13, "700", APP_D, "middle")
p.rect(60, 420, 250, 50, "#fff", APP_D, 1.8, 8); p.text(185, 450, "End of input reached", 16, "700", INK, "middle")
p.line([(140, 350), (140, 420)], INK, 2, dash="3 3")
p.rect(360, 420, 230, 50, APP_L, APP_D, 1.8, 8); p.text(475, 442, "accepting state: VALID", 15, "700", APP_D, "middle"); p.text(475, 460, "then split the parts", 12.5, "400", MUTE, "middle")
p.rect(620, 420, 230, 50, DATA_L, DATA_D, 1.8, 8); p.text(735, 442, "other state: INCOMPLETE", 15, "700", DATA_D, "middle"); p.text(735, 460, "give the expected characters", 12.5, "400", MUTE, "middle")
p.line([(310, 445), (360, 445)], APP_D, 2.2, marker="arrG"); p.line([(590, 445), (620, 445)], DATA_D, 2.2)
open("fig42.svg", "w").write(p.render())

# ================= Figure 5.1: the URL language as a state diagram =================
W3, H3 = 900, 560
d = Svg(W3, H3)
d.text(450, 30, "The URL language as a chain of phases (each box is a block of automaton states)", 18.5, "700", INK, "middle")
def node(x, y, label, sub, color, light, acc=False, w=128, h=56):
    d.rect(x, y, w, h, light, color, 2, 28)
    if acc: d.rect(x + 5, y + 5, w - 10, h - 10, "none", color, 1.4, 23)
    d.text(x + w / 2, y + 26, label, 16, "700", INK, "middle"); d.text(x + w / 2, y + 45, sub, 12.5, "400", MUTE, "middle")
node(24, 80, "scheme", "http(s) / ftp(s)", USR_D, USR_L)
node(188, 80, "://", "two slashes", USR_D, USR_L, w=100)
node(330, 80, "host", "name | IPv4 | localhost", AZ_D, AZ_L, True, w=190)
node(560, 80, "port", ": 1 – 65535", DATA_D, DATA_L, True)
node(330, 250, "path", "( / pchar* )*", APP_D, APP_L, True, w=150)
node(560, 250, "query", "? pchar | / | ?", APP_D, APP_L, True)
node(724, 250, "fragment", "# pchar | / | ?", APP_D, APP_L, True, w=150)
d.line([(0, 108), (24, 108)], INK, 2.4)
for x1, x2 in ((152, 188), (288, 330)):
    d.line([(x1, 108), (x2, 108)], INK, 2.4)
d.line([(520, 108), (560, 108)], INK, 2.4); d.text(540, 100, ":", 15, "700", INK, "middle")
d.line([(380, 136), (380, 250)], INK, 2.4); d.text(366, 200, "/", 16, "700", INK, "end")
d.line([(624, 136), (624, 172), (450, 172), (450, 250)], INK, 2.2); d.text(540, 166, "/", 16, "700", INK, "middle")
d.line([(500, 136), (500, 206), (610, 206), (610, 250)], INK, 2.0, dash="7 4"); d.text(555, 200, "?", 16, "700", INK, "middle")
d.line([(480, 278), (560, 278)], INK, 2.4); d.text(520, 270, "?", 16, "700", INK, "middle")
d.line([(688, 278), (724, 278)], INK, 2.4); d.text(706, 270, "#", 16, "700", INK, "middle")
d.line([(405, 306), (405, 340), (790, 340), (790, 306)], INK, 2.2, dash="7 4"); d.text(600, 332, "#  (no query)", 14, "700", INK, "middle")
d.rect(24, 372, 852, 172, "#fff", LINE, 1.4, 10)
d.text(40, 408, "How to read this", 16, "700", INK)
d.lines(40, 434, ["• Double outlines are accepting phases: the URL may end there. Scheme and '://' are not accepting.",
                  "• Anything that does not fit an arrow moves the automaton to the single dead state; the validator stops there.",
                  "• A '?' or '#' may also follow the host or port directly (path, query and fragment are all optional).",
                  "• The real automaton has 258 states; the host rules built on their own need 234, mostly counting label length up to 63",
                  "   and checking the four IPv4 parts and the 5-digit port limits digit by digit."], 14.5, 24, fill=MUTE)
open("fig51.svg", "w").write(d.render())
