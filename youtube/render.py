"""1080x1920 Shorts renderer: Pillow draws each frame, FFmpeg encodes.

Timeline
  0-3s        hook: big number + one line
  3s..T-3s    animated chart built from the real calculation, then key stats
  last 3s     CTA card (text comes from links.json)
  always      title on top, karaoke captions, disclaimer band
Layout keeps captions and the disclaimer above the bottom ~400px, where the
Shorts player draws its own buttons and channel name.
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
SS = 2  # chart supersampling for smooth lines
FONTS = Path(__file__).resolve().parent / "assets" / "fonts"

COL = {
    "bg_top": (6, 18, 44),
    "bg_bottom": (12, 44, 100),
    "blue": (59, 130, 246),
    "brand": (15, 82, 186),
    "green": (34, 197, 94),
    "red": (239, 68, 68),
    "yellow": (250, 204, 21),
    "white": (255, 255, 255),
    "muted": (148, 163, 184),
    "grid": (255, 255, 255, 38),
    "card": (255, 255, 255, 24),
}

TITLE_Y, CHART_Y, CHART_H = 150, 470, 620
STATS_Y, CAPTION_Y, DISCLAIMER_Y = 1120, 1300, 1490
DISCLAIMER = "Educational only. Not financial advice."

_font_cache = {}


def font(kind, size):
    key = (kind, size)
    if key not in _font_cache:
        if kind == "display":
            f = ImageFont.truetype(str(FONTS / "Anton-Regular.ttf"), size)
        else:
            f = ImageFont.truetype(str(FONTS / "Montserrat.ttf"), size)
            f.set_variation_by_name({"bold": "ExtraBold", "semi": "SemiBold", "reg": "Medium"}[kind])
        _font_cache[key] = f
    return _font_cache[key]


def ease_out(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = min(1.0, max(0.0, t))
    c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def wrap(draw, text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_font(draw, text, kind, size, max_w, max_lines):
    while size > 30:
        f = font(kind, size)
        if len(wrap(draw, text, f, max_w)) <= max_lines:
            return f
        size -= 4
    return font(kind, size)


def centered(draw, y, text, f, fill, stroke=0, stroke_fill=(0, 0, 0)):
    w = draw.textlength(text, font=f)
    draw.text(((W - w) / 2, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)


def background():
    img = Image.new("RGB", (W, H))
    top, bot = COL["bg_top"], COL["bg_bottom"]
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bot)))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W * 0.2, -300, W * 1.3, 700], fill=(20, 60, 140))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    return ImageChops.screen(img, glow)


def nice_max(v):
    """Smallest 3 x (1|2|5 x 10^k) >= v, so gridlines read $5K / $10K / $15K."""
    unit = 100
    while True:
        for m in (1, 2, 5):
            if 3 * unit * m >= v:
                return 3 * unit * m
        unit *= 10


def money_short(v):
    if v >= 1000:
        return f"${v / 1000:.0f}K" if v >= 10000 else f"${v / 1000:.1f}K".replace(".0K", "K")
    return f"${v:.0f}"


class Chart:
    """Pre-computes geometry once; draw(progress) is called every frame."""

    def __init__(self, spec):
        self.spec = spec
        self.x0, self.y0 = 150, CHART_Y + 110
        self.w, self.h = W - 150 - 90, CHART_H - 190
        if spec["type"] == "lines":
            self.n = max(len(s["data"]) for s in spec["series"])
            self.ymax = nice_max(max(max(s["data"]) for s in spec["series"]))

    def _pt(self, i, v):
        return (self.x0 + self.w * i / max(1, self.n - 1), self.y0 + self.h * (1 - v / self.ymax))

    @staticmethod
    def _s(x, y):
        """Frame coords -> supersampled chart-layer coords."""
        return (x * SS, (y - CHART_Y) * SS)

    def draw(self, base, progress, alpha=1.0):
        layer = Image.new("RGBA", (W * SS, CHART_H * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle([60 * SS, 0, (W - 60) * SS, CHART_H * SS - 1], radius=36 * SS, fill=COL["card"])
        if self.spec["type"] == "lines":
            self._lines(d, progress)
        else:
            self._bars(d, progress)
        layer = layer.resize((W, CHART_H), Image.LANCZOS)
        if alpha < 1:
            layer.putalpha(layer.getchannel("A").point(lambda a: int(a * alpha)))
        base.paste(layer, (0, CHART_Y), layer)
        self._labels(ImageDraw.Draw(base, "RGBA"), progress, alpha)

    def _hline(self, d, y, color, width):
        d.line([self._s(self.x0, y), self._s(self.x0 + self.w, y)], fill=color, width=width * SS)

    def _lines(self, d, progress):
        for k in range(4):
            self._hline(d, self.y0 + self.h * k / 3, COL["grid"], 2)
        upto = progress * (self.n - 1)
        for s in self.spec["series"]:
            data = s["data"]
            last = min(len(data) - 1, upto)
            idx = int(last)
            pts = [self._pt(i, data[i]) for i in range(idx + 1)]
            if last > idx and idx + 1 < len(data):
                a, b = data[idx], data[idx + 1]
                pts.append(self._pt(last, a + (b - a) * (last - idx)))
            pts = [self._s(x, y) for x, y in pts]
            color = COL[s["color"]]
            if len(pts) > 1:
                d.line(pts, fill=color, width=9 * SS, joint="curve")
            if pts:
                x, y = pts[-1]
                r = 14 * SS
                d.ellipse([x - r, y - r, x + r, y + r], fill=color, outline=COL["white"], width=3 * SS)

    def _bars(self, d, progress):
        bars = self.spec["bars"]
        slot = self.w / len(bars)
        bw = slot * 0.55
        for k in range(5):
            self._hline(d, self.y0 + self.h * k / 4, COL["grid"], 2)
        for i, b in enumerate(bars):
            p = ease_out(progress * len(bars) - i * 0.6)
            v = min(100.0, b["value"]) * p
            if v <= 0:
                continue
            x = self.x0 + slot * i + (slot - bw) / 2
            top = self.y0 + self.h * (1 - v / 100)
            d.rounded_rectangle([*self._s(x, top), *self._s(x + bw, self.y0 + self.h)], radius=16 * SS, fill=COL[b["color"]])
        y30 = self.y0 + self.h * 0.7
        for x in range(int(self.x0), int(self.x0 + self.w), 40):
            d.line([self._s(x, y30), self._s(x + 22, y30)], fill=COL["yellow"], width=4 * SS)

    def _labels(self, d, progress, alpha):
        muted = COL["muted"] + (int(255 * alpha),)
        f = font("semi", 30)
        if self.spec["type"] == "lines":
            for k in range(4):
                v = self.ymax * (1 - k / 3)
                t = money_short(v)
                d.text((self.x0 - 20 - d.textlength(t, font=f), self.y0 + self.h * k / 3 - 18), t, font=f, fill=muted)
            yrs = (self.n - 1) / 12
            t = f"{yrs:.0f} yrs" if yrs >= 2 else f"{self.n - 1} mo"
            d.text((self.x0 + self.w - d.textlength(t, font=f), self.y0 + self.h + 14), t, font=f, fill=muted)
            d.text((self.x0, self.y0 + self.h + 14), "now", font=f, fill=muted)
            lx = self.x0
            for s in self.spec["series"]:
                c = COL[s["color"]] + (int(255 * alpha),)
                d.rounded_rectangle([lx, CHART_Y + 44, lx + 34, CHART_Y + 70], radius=8, fill=c)
                lf = font("bold", 34)
                d.text((lx + 46, CHART_Y + 38), s["label"], font=lf, fill=COL["white"] + (int(255 * alpha),))
                lx += 46 + d.textlength(s["label"], font=lf) + 50
        else:
            bars = self.spec["bars"]
            slot = self.w / len(bars)
            d.text((self.x0, CHART_Y + 38), "Credit utilization", font=font("bold", 34), fill=COL["white"] + (int(255 * alpha),))
            for i, b in enumerate(bars):
                p = ease_out(progress * len(bars) - i * 0.6)
                cx = self.x0 + slot * i + slot / 2
                t = f"{b['value'] * p:.0f}%"
                vf = font("bold", 44)
                top = self.y0 + self.h * (1 - min(100.0, b["value"]) * p / 100)
                if p > 0:
                    d.text((cx - d.textlength(t, font=vf) / 2, top - 58), t, font=vf, fill=COL["white"] + (int(255 * alpha),))
                lf = font("semi", 30)
                d.text((cx - d.textlength(b["label"], font=lf) / 2, self.y0 + self.h + 14), b["label"], font=lf, fill=muted)


def caption_chunks(words, max_words=4):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or w["text"][-1] in ".!?,":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def draw_captions(d, chunks, t):
    active = None
    for ch in chunks:
        if ch[0]["start"] - 0.05 <= t < ch[-1]["end"] + 0.15:
            active = ch
    if not active:
        return
    f = font("bold", 76)
    space = d.textlength(" ", font=f)
    lines, cur, cur_w = [], [], 0
    for w in active:
        tw = d.textlength(w["text"], font=f)
        if cur and cur_w + space + tw > W - 120:
            lines.append((cur, cur_w))
            cur, cur_w = [], 0
        cur_w = cur_w + (space if cur else 0) + tw
        cur.append((w, tw))
    lines.append((cur, cur_w))
    y = CAPTION_Y + (1 if len(lines) == 1 else 0) * 45
    for line, lw in lines:
        x = (W - lw) / 2
        for w, tw in line:
            on = w["start"] <= t < w["end"] + 0.05
            d.text((x, y), w["text"], font=f, fill=COL["yellow"] if on else COL["white"], stroke_width=7, stroke_fill=(0, 0, 0))
            x += tw + space
        y += 92


def render(out_mp4, audio_wav, duration, words, title, built, cta):
    total = duration + 0.4
    frames = int(total * FPS)
    bg = background()
    chart = Chart(built["chart"])
    chunks = caption_chunks(words)
    hook = built["hook"]
    stats = built["stats"]
    chart_start, cta_start = 3.0, max(6.0, total - 3.0)
    chart_end = chart_start + max(3.0, (cta_start - chart_start) * 0.55)

    probe = ImageDraw.Draw(bg)
    title_font = fit_font(probe, title, "bold", 64, W - 140, 3)
    title_lines = wrap(probe, title, title_font, W - 140)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(audio_wav),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", f"{total:.2f}",
        str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for fi in range(frames):
            t = fi / FPS
            img = bg.copy()
            d = ImageDraw.Draw(img, "RGBA")

            # brand tag + title
            tag = "DEBTLAB"
            tf = font("bold", 30)
            tw = d.textlength(tag, font=tf)
            d.rounded_rectangle([(W - tw) / 2 - 22, 78, (W + tw) / 2 + 22, 124], radius=23, fill=COL["brand"])
            centered(d, 83, tag, tf, COL["white"])
            y = TITLE_Y
            for line in title_lines:
                centered(d, y, line, title_font, COL["white"])
                y += title_font.size * 1.18

            if t < chart_start:
                # hook
                p = ease_back(t / 0.45)
                size = max(40, int(230 * p))
                big = fit_font(d, hook["big"], "display", size, W - 100, 1)
                full = fit_font(d, hook["big"], "display", 230, W - 100, 1)
                # anchor on the final size so the line below never moves or overlaps
                full_bottom = CHART_Y + 150 + d.textbbox((0, 0), hook["big"], font=full)[3]
                by = full_bottom - d.textbbox((0, 0), hook["big"], font=big)[3] + (full.size - big.size) * 0.5
                centered(d, by, hook["big"], big, COL["yellow"], stroke=6)
                if t > 0.35:
                    sf = font("bold", 50)
                    for i, line in enumerate(wrap(d, hook["small"], sf, W - 160)):
                        centered(d, full_bottom + 40 + i * 64, line, sf, COL["white"])
            elif t < cta_start:
                fade = ease_out((t - chart_start) / 0.4)
                chart.draw(img, ease_out((t - chart_start) / (chart_end - chart_start)), fade)
                d = ImageDraw.Draw(img, "RGBA")
                if t > chart_end:
                    sp = ease_out((t - chart_end) / 0.5)
                    cw = (W - 120 - 30) / 2
                    for i, (label, value) in enumerate(stats):
                        x = 60 + i * (cw + 30)
                        yy = STATS_Y + 40 * (1 - sp)
                        a = int(255 * sp)
                        d.rounded_rectangle([x, yy, x + cw, yy + 150], radius=28, fill=(255, 255, 255, int(28 * sp)))
                        vf = fit_font(d, value, "bold", 58, cw - 40, 1)
                        d.text((x + (cw - d.textlength(value, font=vf)) / 2, yy + 22), value, font=vf, fill=COL["green"] + (a,))
                        lf = font("semi", 30)
                        d.text((x + (cw - d.textlength(label, font=lf)) / 2, yy + 98), label, font=lf, fill=COL["muted"] + (a,))
            else:
                # CTA card
                p = ease_back((t - cta_start) / 0.5)
                card_h = 520
                top = CHART_Y + 60 + (1 - p) * 200
                d.rounded_rectangle([70, top, W - 70, top + card_h], radius=44, fill=COL["brand"])
                centered(d, top + 60, cta["headline"], fit_font(d, cta["headline"], "display", 110, W - 220, 1), COL["white"])
                yy = top + 220
                for line in cta["lines"]:
                    lf = fit_font(d, line, "bold", 46, W - 220, 1)
                    centered(d, yy, line, lf, COL["white"])
                    yy += 72

            draw_captions(d, chunks, t)

            df = font("semi", 30)
            dw = d.textlength(DISCLAIMER, font=df)
            d.rounded_rectangle([(W - dw) / 2 - 24, DISCLAIMER_Y - 10, (W + dw) / 2 + 24, DISCLAIMER_Y + 46], radius=28, fill=(0, 0, 0, 110))
            centered(d, DISCLAIMER_Y, DISCLAIMER, df, COL["muted"])

            if fi == 0:
                first = img.copy()
            if H > W and t > total - 0.45:   # dikey Short: son 0.45 sn ilk kareye karışır (kesintisiz döngü)
                img = Image.blend(img, first, min(1.0, (t - (total - 0.45)) / 0.45))
            proc.stdin.write(img.tobytes())
    finally:
        proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg exited with {rc}")
    return total
