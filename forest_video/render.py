import numpy as np, math, random, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1280, 720, 24, 60
random.seed(7)
rng = np.random.default_rng(7)
FONT = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)

def vgrad(w, h, stops):
    ys = np.linspace(0, 1, h)
    out = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        out[:, :, c] = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])[:, None]
    return Image.fromarray(out.astype(np.uint8))

def radial(w, h, cx, cy, rad, power=2.0):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / rad
    return np.clip(1 - d, 0, 1) ** power

def view(img, z, cx=.5, cy=.5):
    w, h = img.size
    cw, ch = w / z, h / z
    x0 = clamp(cx * w - cw / 2, 0, w - cw); y0 = clamp(cy * h - ch / 2, 0, h - ch)
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))

def mix(a, b, t): return tuple(int(lerp(a[i], b[i], t)) for i in range(3))

# ---------------------------------------------------------------- vignette
_vy, _vx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.5 * (((_vx - W / 2) / (W / 2)) ** 2 + ((_vy - H / 2) / (H / 2)) ** 2) * 0.62)[:, :, None]
VIG = np.clip(VIG, 0.35, 1)

def trunk_layer(w, h, n, wmin, wmax, base, rim, seed, hazy=0.0):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    r = random.Random(seed)
    for x in sorted(r.uniform(-60, w + 60) for _ in range(n)):
        tw = r.uniform(wmin, wmax); bw = tw * 1.18
        col = mix(base, (180, 160, 100), hazy)
        d.polygon([(x - tw / 2, -10), (x + tw / 2, -10), (x + bw / 2, h + 10), (x - bw / 2, h + 10)], fill=col + (255,))
        d.polygon([(x - tw / 2, -10), (x - tw / 2 + tw * .22, -10), (x - bw / 2 + bw * .22, h + 10), (x - bw / 2, h + 10)], fill=mix(col, rim, 0.55) + (255,))
        for _ in range(int(tw / 9)):
            xx = x + r.uniform(-tw / 2, tw / 2)
            d.line([(xx, -10), (xx + (bw - tw) * (xx - x) / tw * .5, h + 10)], fill=mix(col, (0, 0, 0), .35) + (200,), width=2)
    return im

# ---------------------------------------------------------------- scene 1 assets
LW, LH = 1920, 1080
SKY1 = vgrad(LW, LH, [(0, (250, 215, 140)), (.45, (255, 238, 185)), (1, (215, 195, 120))])
_g = (radial(LW, LH, 1300, 250, 900, 1.6)[:, :, None] * np.array([40, 30, 10], np.float32))
SKY1 = Image.fromarray(np.clip(np.asarray(SKY1).astype(np.float32) + _g, 0, 255).astype(np.uint8))
FAR1 = trunk_layer(LW, LH, 20, 24, 44, (96, 98, 60), (190, 170, 100), 1, hazy=.35)
MID1 = trunk_layer(LW, LH, 12, 52, 92, (52, 54, 30), (170, 140, 70), 2, hazy=.1)
NEAR1 = trunk_layer(LW, LH, 5, 120, 190, (20, 24, 13), (120, 95, 45), 3)
_can = np.zeros((LH, LW, 4), np.uint8); _can[:, :, 0], _can[:, :, 1], _can[:, :, 2] = 12, 34, 14
_can[:, :, 3] = (np.clip(1 - np.arange(LH) / 420, 0, 1) ** 1.4 * 235).astype(np.uint8)[:, None]
CAN1 = Image.fromarray(_can, "RGBA")
NEAR1 = Image.alpha_composite(NEAR1, CAN1)

def shafts_img(w, h, n, seed, col=(255, 222, 140), blur=22):
    r = random.Random(seed); im = Image.new("RGB", (w, h), (0, 0, 0)); d = ImageDraw.Draw(im)
    for _ in range(n):
        x = r.uniform(0, w * .9); wt = r.uniform(.02, .04) * w; wb = r.uniform(.08, .16) * w; sh = r.uniform(.12, .22) * w
        k = r.uniform(.45, 1.0); c = tuple(int(v * k) for v in col)
        d.polygon([(x, 0), (x + wt, 0), (x + sh + wb, h), (x + sh, h)], fill=c)
    return im.filter(ImageFilter.GaussianBlur(blur))
SHAFTS1 = np.asarray(shafts_img(LW, LH, 8, 5)).astype(np.float32)

def fog_alpha(w, h, seed, strength):
    r = np.random.default_rng(seed); n = r.random((9, 36)).astype(np.float32)
    im = Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(50))
    a = np.asarray(im).astype(np.float32); a = (a - a.min()) / (a.max() - a.min())
    return Image.fromarray((a ** 1.3 * strength).astype(np.uint8), "L")
FOG_A = fog_alpha(3840, LH, 11, 150)
FOG_B = fog_alpha(3840, LH, 12, 110)
DUST = [(random.uniform(0, W), random.uniform(0, H), random.uniform(-6, 6), random.uniform(-9, -2), random.uniform(1, 2.8), random.uniform(.3, 1)) for _ in range(70)]

def add_dust(img, t, boost=1.0):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for x, y, vx, vy, s, b in DUST:
        xx = (x + vx * t) % W; yy = (y + vy * t) % H
        a = int(160 * b * boost * (0.6 + 0.4 * math.sin(t * 1.3 + x)))
        d.ellipse((xx - s, yy - s, xx + s, yy + s), fill=(255, 240, 190, max(0, a)))
    return Image.alpha_composite(img, ov.filter(ImageFilter.GaussianBlur(0.8)))

def scene1(t):
    p = clamp(t / 15)
    img = view(SKY1, 1.4 * (1 + .08 * p)).convert("RGBA")
    img = Image.alpha_composite(img, view(FAR1, 1.4 * (1 + .10 * p)))
    fx = int((t * 18) % 1920)
    fa = FOG_A.crop((fx, 0, fx + LW, LH)); fogc = Image.new("RGBA", (LW, LH), (255, 240, 200, 255)); fogc.putalpha(fa)
    img = Image.alpha_composite(img, view(fogc, 1.4 * (1 + .12 * p)))
    img = Image.alpha_composite(img, view(MID1, 1.4 * (1 + .22 * p)))
    fx2 = int((t * 32 + 700) % 1920)
    fb = FOG_B.crop((fx2, 0, fx2 + LW, LH)); fogd = Image.new("RGBA", (LW, LH), (255, 232, 180, 255)); fogd.putalpha(fb)
    img = Image.alpha_composite(img, view(fogd, 1.4 * (1 + .25 * p)))
    sh = np.asarray(view(Image.fromarray(SHAFTS1.astype(np.uint8)), 1.4 * (1 + .15 * p))).astype(np.float32)
    arr = np.asarray(img.convert("RGB")).astype(np.float32) + sh * (0.55 + 0.12 * math.sin(t * 1.1))
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    img = Image.alpha_composite(img, view(NEAR1, 1.4 * (1 + .45 * p)))
    return add_dust(img, t)

# ---------------------------------------------------------------- scene 2 (macro)
def build_macro():
    bg = vgrad(1500, 860, [(0, (70, 120, 50)), (.5, (150, 175, 70)), (1, (60, 90, 35))]).convert("RGBA")
    ov = Image.new("RGBA", bg.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    r = random.Random(21)
    for _ in range(46):
        x, y, rad = r.uniform(0, 1500), r.uniform(0, 860), r.uniform(18, 85)
        c = r.choice([(230, 240, 130), (190, 230, 110), (255, 230, 150), (120, 190, 80)])
        d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=c + (r.randint(40, 95),))
    ov = ov.filter(ImageFilter.GaussianBlur(7))
    bg = Image.alpha_composite(bg, ov)
    # fern leaf (supersampled)
    SS = 2; ls = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(ls)
    P0, P1, P2 = (-120, 130), (560, 40), (990, 300)
    B = lambda u: ((1 - u) ** 2 * P0[0] + 2 * (1 - u) * u * P1[0] + u * u * P2[0], (1 - u) ** 2 * P0[1] + 2 * (1 - u) * u * P1[1] + u * u * P2[1])
    def T(u):
        dx = 2 * (1 - u) * (P1[0] - P0[0]) + 2 * u * (P2[0] - P1[0]); dy = 2 * (1 - u) * (P1[1] - P0[1]) + 2 * u * (P2[1] - P1[1]); n = math.hypot(dx, dy); return dx / n, dy / n
    pts = [B(u / 60) for u in range(61)]
    d.line([(x * SS, y * SS) for x, y in pts], fill=(35, 90, 30, 255), width=11 * SS)
    for i in range(34):
        u = 0.03 + i * 0.0285
        bx, by = B(u); tx, ty = T(u); nx, ny = -ty, tx
        L = 190 * (1 - u * .72) + 30; wd = L * .11 + 4
        col = mix((30, 120, 35), (150, 215, 70), u)
        for sgn in (1, -1):
            mx, my = bx + sgn * nx * L * .5 + tx * L * .12, by + sgn * ny * L * .5 + ty * L * .12
            tipx, tipy = bx + sgn * nx * L + tx * L * .38, by + sgn * ny * L + ty * L * .38
            poly = [(bx, by), (mx + tx * wd, my + ty * wd), (tipx, tipy), (mx - tx * wd, my - ty * wd)]
            d.polygon([(x * SS, y * SS) for x, y in poly], fill=col + (255,), outline=mix(col, (10, 50, 15), .5) + (255,))
            d.line([(bx * SS, by * SS), (tipx * SS, tipy * SS)], fill=mix(col, (230, 255, 150), .45) + (255,), width=2 * SS)
    leaf = ls.resize((W, H), Image.LANCZOS)
    # mushroom + foreground
    ms = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(ms)
    cx, cy = 970, 585
    d.rounded_rectangle(((cx - 48) * SS, (cy - 10) * SS, (cx + 48) * SS, (cy + 130) * SS), radius=30 * SS, fill=(224, 208, 178, 255))
    d.ellipse(((cx - 175) * SS, (cy - 78) * SS, (cx + 175) * SS, (cy + 58) * SS), fill=(70, 38, 22, 255))
    for k in range(10):
        f = k / 10; d.ellipse(((cx - 175 + 12 * k) * SS, (cy - 82 + 5 * k) * SS, (cx + 175 - 14 * k) * SS, (cy + 30 - 4 * k) * SS), fill=mix((120, 66, 36), (190, 120, 70), f) + (255,))
    for sx, sy, sr in [(-90, -35, 13), (-30, -52, 10), (45, -40, 15), (100, -18, 9), (10, -15, 7)]:
        d.ellipse(((cx + sx - sr) * SS, (cy + sy - sr * .6) * SS, (cx + sx + sr) * SS, (cy + sy + sr * .6) * SS), fill=(238, 224, 196, 235))
    d.ellipse(((cx - 150) * SS, (cy - 62) * SS, (cx - 50) * SS, (cy - 40) * SS), fill=(255, 220, 170, 120))
    mush = ms.resize((W, H), Image.LANCZOS)
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fg)
    for i in range(14):
        x = i * 100 - 20 + random.uniform(-20, 20); d.ellipse((x - 90, 690, x + 90, 800), fill=(18, 48, 20, 255))
    fg = fg.filter(ImageFilter.GaussianBlur(2))
    return bg, leaf, mush, fg, B(1.0), (cx, cy - 75)
BG2, LEAF2, MUSH2, FG2, TIP2, CAPTOP2 = build_macro()
LEAFB = lambda u: None

def draw_drop(img, x, y, r, stretch=1.0, alpha=1.0):
    s = 4; sz = int(r * 4) + 4
    p = Image.new("RGBA", (sz * s, sz * s), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
    c = sz * s / 2; rx = r * s; ry = r * s * stretch
    d.ellipse((c - rx, c - ry, c + rx, c + ry), fill=(180, 225, 240, int(150 * alpha)), outline=(255, 255, 255, int(235 * alpha)), width=int(s * 1.3))
    d.ellipse((c - rx * .6, c - ry * .7, c - rx * .1, c - ry * .2), fill=(255, 255, 255, int(240 * alpha)))
    d.ellipse((c + rx * .1, c + ry * .2, c + rx * .6, c + ry * .7), fill=(255, 235, 180, int(130 * alpha)))
    p = p.resize((sz, sz), Image.LANCZOS)
    img.paste(p, (int(x - sz / 2), int(y - sz / 2)), p)

def scene2(t):
    ox = lerp(0, 90, clamp(t / 15)); oy = lerp(20, 60, clamp(t / 15))
    img = BG2.crop((int(ox), int(oy), int(ox) + W, int(oy) + H)).copy()
    img.alpha_composite(LEAF2); img.alpha_composite(MUSH2)
    P0, P1, P2 = (-120, 130), (560, 40), (990, 300)
    B = lambda u: ((1 - u) ** 2 * P0[0] + 2 * (1 - u) * u * P1[0] + u * u * P2[0], (1 - u) ** 2 * P0[1] + 2 * (1 - u) * u * P1[1] + u * u * P2[1])
    tipx, tipy = TIP2; capx, capy = CAPTOP2
    if t < 6:
        u = lerp(.55, 1.0, ease(t / 6)); x, y = B(u); draw_drop(img, x, y + 12, 11)
    elif t < 8.2:
        k = (t - 6) / 2.2; draw_drop(img, tipx, tipy + 12 + k * 8, 12 + 6 * k, 1 + .35 * k)
    elif t < 11.6:
        k = (t - 8.2) / 3.4; yy = tipy + 18 + (capy - tipy - 18) * (k ** 2.2); draw_drop(img, tipx + 2 * k, yy, 17 - 3 * k, 1.5)
    else:
        k = t - 11.6
        if k < 0.7: draw_drop(img, tipx, capy, 12 * (1 - k / .7) + 2, .4, 1 - k / .7)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        for j in range(3):
            kk = k - j * .35
            if 0 < kk < 2.2:
                rr = 14 + 110 * kk / 2.2
                d.ellipse((capx - rr, capy - rr * .22, capx + rr, capy + rr * .22), outline=(240, 250, 255, int(210 * (1 - kk / 2.2))), width=3)
        for j in range(9):
            ang = -math.pi * (0.15 + 0.7 * j / 8); sp = 160 + 40 * ((j * 37) % 5)
            px = capx + math.cos(ang) * sp * k * .55; py = capy + math.sin(ang) * sp * k + 330 * k * k
            if k < 1.4 and py < capy + 5: d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=(235, 248, 255, int(230 * (1 - k / 1.4))))
        img.alpha_composite(ov.filter(ImageFilter.GaussianBlur(.7)))
    img.alpha_composite(FG2)
    return add_dust(img, t * .6, .7)

# ---------------------------------------------------------------- scene 3 (stag)
WIDE = 4200
FAR3 = trunk_layer(WIDE, H, 56, 24, 40, (96, 100, 62), (190, 170, 100), 31, hazy=.45)
MID3 = trunk_layer(WIDE, H, 34, 56, 100, (46, 52, 30), (170, 140, 70), 32, hazy=.15)
NEAR3 = trunk_layer(WIDE, H, 10, 130, 200, (16, 22, 12), (120, 95, 45), 33)
def ground(seed):
    r = random.Random(seed); im = Image.new("RGBA", (WIDE, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(0, H)] + [(x, 600 + 14 * math.sin(x / 90) + r.uniform(-6, 6)) for x in range(0, WIDE + 40, 40)] + [(WIDE, H)]
    d.polygon(pts, fill=(22, 52, 24, 255))
    for _ in range(60):
        x = r.uniform(0, WIDE); y = r.uniform(610, 700)
        d.ellipse((x - 70, y - 14, x + 70, y + 14), fill=(60, 110, 40, 150))
    for _ in range(18):
        x = r.uniform(0, WIDE); y0 = 600; pts = [(x, y0)]
        for k in range(1, 9): pts.append((x + k * r.uniform(24, 40) * (1 if r.random() < .5 else -1) * 0 + k * 30, y0 + k * 14 + 10 * math.sin(k + x)))
        d.line(pts, fill=(10, 24, 10, 255), width=r.randint(10, 20))
    return im.filter(ImageFilter.GaussianBlur(1.2))
GROUND3 = ground(41)
SKY3 = vgrad(W, H, [(0, (245, 210, 130)), (.5, (255, 236, 175)), (1, (200, 180, 110))])
GLOW3 = radial(W, H, 860, 300, 620, 1.7)[:, :, None]
SHAFTS3 = np.asarray(shafts_img(W, H, 6, 9, blur=18)).astype(np.float32)
FOGN3 = fog_alpha(2560, H, 17, 120)

def crop_wide(img, off):
    off = off % (WIDE - W); return img.resize((W, H), Image.BICUBIC, box=(off, 0, off + W, H))

def stag_patch(phase, rim=False):
    S = 2; pw, ph = 760, 640; ox, oy = 330, 330
    im = Image.new("RGBA", (pw * S, ph * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    col = (255, 190, 100, 255) if rim else (14, 18, 11, 255)
    sh = -3 if rim else 0
    X = lambda x: (ox + x + sh) * S; Y = lambda y: (oy + y + sh) * S
    def line(p, q, w):
        d.line([(X(p[0]), Y(p[1])), (X(q[0]), Y(q[1]))], fill=col, width=int(w * S))
        d.ellipse((X(q[0]) - w * S / 2, Y(q[1]) - w * S / 2, X(q[0]) + w * S / 2, Y(q[1]) + w * S / 2), fill=col)
    bob = 3 * math.sin(phase * 2)
    d.ellipse((X(-150), Y(-55 + bob), X(150), Y(65 + bob)), fill=col)
    d.polygon([(X(95), Y(-40 + bob)), (X(150), Y(-20 + bob)), (X(230), Y(-120 + bob)), (X(185), Y(-140 + bob))], fill=col)
    d.ellipse((X(190), Y(-150 + bob), X(262), Y(-100 + bob)), fill=col)
    d.polygon([(X(205), Y(-150 + bob)), (X(195), Y(-188 + bob)), (X(222), Y(-155 + bob))], fill=col)
    d.polygon([(X(-150), Y(-20 + bob)), (X(-180), Y(-45 + bob)), (X(-160), Y(10 + bob))], fill=col)
    for hx, off in [(-105, 0), (-70, math.pi), (80, math.pi), (112, 0)]:
        a = .5 * math.sin(phase + off); lift = max(0, math.cos(phase + off))
        kx, ky = hx + 70 * math.sin(a), 35 + bob + 70 * math.cos(a)
        a2 = .55 * math.sin(phase + off - .9) + (.35 if hx < 0 else -.15)
        fx, fy = kx + 78 * math.sin(a2), ky + 78 * math.cos(a2) - 16 * lift
        line((hx, 35 + bob), (kx, ky), 17); line((kx, ky), (fx, fy), 10)
    def antler(x, y, ang, L, depth, w):
        ex, ey = x + L * math.cos(ang), y - L * math.sin(ang); line((x, y), (ex, ey), w)
        if depth > 0:
            for f, da, lf in [(.45, .75, .55), (.75, -.55, .5), (1.0, .35, .6)]:
                sx, sy = x + (ex - x) * f, y + (ey - y) * f; antler(sx, sy, ang + da, L * lf, depth - 1, max(3, w - 3))
    antler(210, -150 + bob, 1.25, 85, 2, 9); antler(200, -148 + bob, 1.0, 80, 2, 8)
    return im.resize((pw, ph), Image.LANCZOS), (ox, oy)

def scene3(t):
    p = clamp(t / 15); cam = t * 90
    img = SKY3.copy()
    base = np.asarray(img).astype(np.float32) + GLOW3 * np.array([40, 22, 0], np.float32) * (1 + p)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    img.alpha_composite(crop_wide(FAR3, cam * .18))
    fx = int((t * 14) % 1280); fl = Image.new("RGBA", (W, H), (255, 238, 195, 255)); fl.putalpha(FOGN3.crop((fx, 0, fx + W, H))); img.alpha_composite(fl)
    img.alpha_composite(crop_wide(MID3, cam * .5))
    arr = np.asarray(img.convert("RGB")).astype(np.float32) + SHAFTS3 * (0.25 + 0.55 * p) * (0.9 + 0.1 * math.sin(t))
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    img.alpha_composite(crop_wide(GROUND3, cam))
    img.alpha_composite(crop_wide(NEAR3, cam * 1.5))
    phase = t * 3.2
    rim, (ox, oy) = stag_patch(phase, True); body, _ = stag_patch(phase, False)
    sx, sy = 470 + 40 * math.sin(t * .3), 506
    img.paste(rim, (int(sx - ox), int(sy - oy)), rim); img.paste(body, (int(sx - ox), int(sy - oy)), body)
    return add_dust(img, t + 4, 1.0)

# ---------------------------------------------------------------- scene 4 (pull-back)
def strip(w, h, seed, base, rim, hmin, hmax, step):
    r = random.Random(seed); im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = -20
    while x < w + 40:
        hh = r.uniform(hmin, hmax); ww = step * r.uniform(.9, 1.5)
        d.polygon([(x, h), (x + ww / 2, h - hh), (x + ww, h)], fill=base + (255,))
        d.line([(x + ww / 2, h - hh), (x + ww * .78, h - hh * .45)], fill=rim + (255,), width=3)
        x += ww * .62
    d.rectangle((0, h - hmin, w, h), fill=base + (255,))
    return im
def mountains(w, h, seed, col, amp, base_y):
    r = random.Random(seed); ph = [r.uniform(0, 6) for _ in range(4)]
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); pts = [(0, h)]
    for x in range(0, w + 20, 20):
        y = base_y - amp * (.55 * abs(math.sin(x / 260 + ph[0])) + .3 * abs(math.sin(x / 120 + ph[1])) + .15 * math.sin(x / 55 + ph[2]) ** 2)
        pts.append((x, y))
    pts.append((w, h)); d.polygon(pts, fill=col + (255,)); return im
NEAR4 = strip(2000, 340, 51, (13, 30, 17), (210, 165, 80), 110, 300, 46)
MID4 = strip(2000, 200, 52, (44, 78, 56), (200, 175, 110), 50, 170, 34)
FAR4 = strip(2000, 110, 53, (110, 125, 110), (225, 200, 150), 25, 100, 24)
MT1 = mountains(2000, 500, 61, (150, 135, 150), 190, 300)
MT2 = mountains(2000, 500, 62, (190, 160, 140), 130, 330)
SKY4 = vgrad(W, H, [(0, (70, 100, 160)), (.35, (200, 170, 170)), (.62, (255, 205, 130)), (1, (255, 225, 160))])
FOG4 = fog_alpha(2560, 300, 71, 170)

def scene4(t):
    p = clamp(t / 15); e = ease(p)
    img = SKY4.copy().convert("RGBA")
    sunY = lerp(360, 430, e)
    glow = radial(W, H, 900, sunY, 520, 1.5)[:, :, None]
    arr = np.asarray(img.convert("RGB")).astype(np.float32) + glow * np.array([120, 70, 10], np.float32)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img); d.ellipse((900 - 34, sunY - 34, 900 + 34, sunY + 34), fill=(255, 250, 220, 255))
    img.alpha_composite(MT1.crop((int(t * 4), 0, int(t * 4) + W, 500)).resize((W, 500)), (0, int(lerp(120, 270, e))))
    img.alpha_composite(MT2.crop((int(t * 6) + 300, 0, int(t * 6) + 300 + W, 500)), (0, int(lerp(170, 310, e))))
    fx = int((t * 20) % 1280); fl = Image.new("RGBA", (W, 300), (255, 236, 200, 255)); fl.putalpha(FOG4.crop((fx, 0, fx + W, 300)))
    img.alpha_composite(fl, (0, int(lerp(300, 400, e))))
    for im_, h_, sp, y_, col in [(FAR4, 110, 8, lerp(300, 440, e), (110, 125, 110)), (MID4, 200, 14, lerp(190, 480, e), (44, 78, 56)), (NEAR4, 340, 22, lerp(-70, 570, e), (13, 30, 17))]:
        img.alpha_composite(im_.crop((int(t * sp), 0, int(t * sp) + W, h_)), (0, int(y_)))
        if int(y_) + h_ - 1 < H: ImageDraw.Draw(img).rectangle((0, int(y_) + h_ - 1, W, H - 1), fill=col + (255,))
    return add_dust(img, t, .6)

# ---------------------------------------------------------------- compositor
def title_overlay(img, t):
    a = clamp((t - 1.0) / 1.0) * clamp((6.0 - t) / 1.0)
    if a <= 0: return img
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    f = ImageFont.truetype(FONT, 50); f2 = ImageFont.truetype(FONT, 22)
    txt = "AWAKENING OF THE ANCIENT FOREST"
    wtot = sum(d.textlength(c, font=f) + 5 for c in txt); x = (W - wtot) / 2
    for c in txt:
        d.text((x + 2, 500 + 2), c, font=f, fill=(0, 0, 0, int(140 * a))); d.text((x, 500), c, font=f, fill=(255, 245, 220, int(255 * a))); x += d.textlength(c, font=f) + 5
    d.text((W / 2, 566), "A  NATURE  SEQUENCE", font=f2, fill=(255, 235, 190, int(220 * a)), anchor="mm")
    return Image.alpha_composite(img, ov)

def frame(t):
    sc = [(0, scene1), (15, scene2), (30, scene3), (45, scene4)]
    idx = min(3, int(t // 15)); lt = t - sc[idx][0]
    img = sc[idx][1](lt)
    x = 0.6
    if idx < 3 and lt > 15 - x:
        nxt = sc[idx + 1][1](0.0)
        img = Image.blend(img.convert("RGB"), nxt.convert("RGB"), ease((lt - (15 - x)) / x)).convert("RGBA")
    if idx > 0 and lt < 0:  # not used
        pass
    img = title_overlay(img.convert("RGBA"), t)
    arr = np.asarray(img.convert("RGB")).astype(np.float32) * VIG
    arr = arr + rng.normal(0, 2.2, arr.shape).astype(np.float32)
    if t < 0.8: arr *= t / 0.8
    if t > DUR - 2.0: arr *= clamp((DUR - t) / 2.0)
    return np.clip(arr, 0, 255).astype(np.uint8)

def work(i): return frame(i / FPS).tobytes()

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
        import time
        for tt in [float(x) for x in sys.argv[3:]]:
            t0 = time.time(); Image.fromarray(frame(tt)).save(f"{outdir}/f_{tt:05.1f}.png"); print(tt, round(time.time() - t0, 2), "s")
    else:
        from multiprocessing import Pool
        out = sys.argv[2]; n = DUR * FPS
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", sys.argv[3],
               "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", out]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for k, b in enumerate(pool.imap(work, range(n), chunksize=6)):
                pr.stdin.write(b)
                if k % 120 == 0: print("frame", k, "/", n, flush=True)
        pr.stdin.close(); pr.wait(); print("done")
