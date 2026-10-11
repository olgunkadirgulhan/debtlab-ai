"""Etsy / Gumroad listing images for the planner (run after make_planner.py).

    python tools/planner/make_listing_images.py   ->  product/images/*.png (2400x1800)
"""
from pathlib import Path

import fitz  # pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "product" / "DebtLab-Debt-Payoff-Planner-Letter.pdf"
OUT = ROOT / "product" / "images"
FONTS = Path(__file__).resolve().parent / "fonts"
W, H = 2400, 1800
BRAND, SOFT, INK, GREEN = (15, 82, 186), (234, 241, 252), (15, 23, 42), (22, 163, 74)


def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"Montserrat-{weight}.ttf"), size)


def pages(dpi=150):
    doc = fitz.open(PDF)
    out = []
    for p in doc:
        pix = p.get_pixmap(dpi=dpi)
        out.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    return out


def paper(img, height):
    """Page scaled to `height` with a soft drop shadow."""
    img = img.resize((int(img.width * height / img.height), height), Image.LANCZOS)
    pad = 40
    sh = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([pad, pad + 14, pad + img.width, pad + img.height + 14], fill=(0, 0, 0, 90))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    sh.paste(img, (pad, pad))
    return sh


def place(canvas, layer, x, y, angle=0):
    if angle:
        layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    canvas.paste(layer, (int(x), int(y)), layer)


def headline(d, x, y, lines, color=INK, size=96, weight=800, gap=1.15):
    f = font(weight, size)
    for line in lines:
        d.text((x, y), line, font=f, fill=color)
        y += int(size * gap)
    return y


def pill(d, x, y, text, bg=GREEN, fg=(255, 255, 255), size=40):
    f = font(800, size)
    w = d.textlength(text, font=f)
    d.rounded_rectangle([x, y, x + w + 60, y + size + 36], radius=(size + 36) // 2, fill=bg)
    d.text((x + 30, y + 16), text, font=f, fill=fg)
    return x + w + 80


def hero(ps):
    im = Image.new("RGB", (W, H), BRAND)
    d = ImageDraw.Draw(im)
    place(im, paper(ps[8], 1150), 1560, 380, -6)
    place(im, paper(ps[2], 1150), 1330, 340, 4)
    place(im, paper(ps[0], 1250), 1130, 260)
    y = headline(d, 120, 300, ["Debt Payoff", "Planner"], (255, 255, 255), 150)
    y = headline(d, 120, y + 30, ["Printable PDF · 15 pages", "Letter + A4 sizes"], (200, 218, 248), 58, 600)
    x = pill(d, 120, y + 60, "SNOWBALL")
    pill(d, x, y + 60, "AVALANCHE")
    d.text((120, H - 150), "Instant download · print at home", font=font(600, 48), fill=(200, 218, 248))
    return im


def inside(ps):
    im = Image.new("RGB", (W, H), SOFT)
    d = ImageDraw.Draw(im)
    d.text((W // 2, 110), "What's inside: 15 pages", font=font(800, 96), fill=INK, anchor="mm")
    cols, th = 5, 470
    tiles = [paper(p, th) for p in ps[:15]]
    tw = tiles[0].width
    gx = (W - cols * tw) / 2
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        place(im, t, gx + c * tw, 180 + r * (th + 60))
    return im


def feature(ps, idx, title, sub, bg=SOFT):
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    y = headline(d, 120, 420, title, INK, 120)
    for s in sub:
        d.text((120, y + 40), s, font=font(400, 52), fill=(71, 85, 105))
        y += 76
    page = paper(ps[idx], 1560)
    place(im, page, W - page.width - 40, (H - page.height) // 2)
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ps = pages()
    imgs = {
        "1-hero": hero(ps),
        "2-inside": inside(ps),
        "3-coloring-chart": feature(ps, 8, ["Color your", "way to", "debt free"], ["100 circles, 1% each.", "Milestones at 25/50/75%."]),
        "4-cheat-sheet": feature(ps, 11, ["Real payoff", "math, done", "for you"], ["Payments for 1–5 years", "at 15%–29% APR."], (232, 247, 238)),
        "5-trackers": feature(ps, 5, ["6 debt", "trackers"], ["Log every payment.", "Roll it into the next debt."]),
        "6-order": feature(ps, 3, ["Snowball or", "avalanche?"], ["Both worksheets included.", "Pick one, set the order."]),
    }
    for name, im in imgs.items():
        im.save(OUT / f"{name}.png", optimize=True)
    print("images:", ", ".join(imgs))


if __name__ == "__main__":
    main()
