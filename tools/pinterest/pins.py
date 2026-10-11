"""Pinterest pin queue + 1000x1500 pin images for debtlabai.com.

    python tools/pinterest/pins.py --preview 6   # render the next 6 pins into tools/pinterest/out/

Pins point at site pages (payoff tables, free printable, calculators, blog posts).
All numbers come from shared/debt_math.py, the same math as the site.
"""
import argparse
import csv
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "shared"))
import debt_math as dm  # noqa: E402

SITE = "https://debtlabai.com"
FONTS = ROOT / "tools" / "planner" / "fonts"
OUT = Path(__file__).resolve().parent / "out"
POSTED = Path(__file__).resolve().parent / "posted.csv"
FREE_PDF = ROOT / "web" / "public" / "downloads" / "free-debt-payoff-tracker.pdf"
W, H = 1000, 1500
BRAND, SOFT, INK, MUTED, GREEN, RED, WHITE = (15, 82, 186), (234, 241, 252), (15, 23, 42), (71, 85, 105), (22, 163, 74), (220, 38, 38), (255, 255, 255)

# Keep in sync with web/lib/payoffScenarios.ts
BALANCES = [1000, 2000, 3000, 5000, 7500, 10000, 12000, 15000, 20000, 25000, 30000, 50000]
APRS = [18, 20, 22, 24, 26, 29]


def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"Montserrat-{weight}.ttf"), size)


def money(x):
    return f"${round(x):,}"


def ym(n):
    y, m = divmod(n, 12)
    return " ".join(([f"{y} yr" + ("s" if y != 1 else "")] if y else []) + ([f"{m} mo"] if m else []))


def pmt(balance, apr, n):
    r = apr / 1200
    import math

    return math.ceil(balance * r / (1 - (1 + r) ** -n))


def centered(d, y, text, f, fill):
    d.text((W // 2, y), text, font=f, fill=fill, anchor="mt")


def footer(d, label="debtlabai.com"):
    half = d.textlength(label, font=font(800, 34)) / 2 + 50
    d.rounded_rectangle([W // 2 - half, H - 120, W // 2 + half, H - 50], radius=35, fill=WHITE if label == "debtlabai.com" else BRAND)
    centered(d, H - 103, label, font(800, 34), BRAND if label == "debtlabai.com" else WHITE)


# ---------------------------------------------------------------- pin types
def render_payoff(spec):
    b, a = spec["balance"], spec["apr"]
    mn = dm.payoff_minimum(b, a)
    p36 = pmt(b, a, 36)
    fx = dm.payoff(b, a, p36)
    im = Image.new("RGB", (W, H), BRAND)
    d = ImageDraw.Draw(im)
    centered(d, 90, "HOW TO PAY OFF", font(800, 44), (191, 211, 245))
    centered(d, 160, money(b), font(800, 190), WHITE)
    centered(d, 380, f"of credit card debt at {a}% APR", font(600, 46), (220, 231, 250))
    # two cards
    y = 500
    for title, big, small, color in [
        ("MINIMUM PAYMENTS ONLY", ym(mn["months"]), f"{money(mn['total_interest'])} in interest", RED),
        (f"PAY {money(p36)} A MONTH", "3 years", f"{money(fx['total_interest'])} in interest", GREEN),
    ]:
        d.rounded_rectangle([70, y, W - 70, y + 330], radius=36, fill=WHITE)
        centered(d, y + 45, title, font(800, 38), color)
        centered(d, y + 115, big, font(800, 110), INK)
        centered(d, y + 250, small, font(600, 44), MUTED)
        y += 370
    centered(d, y + 10, "Full payoff table + balance transfer math", font(600, 36), (220, 231, 250))
    footer(d)
    return im


def render_freebie(spec):
    import fitz

    im = Image.new("RGB", (W, H), SOFT)
    d = ImageDraw.Draw(im)
    centered(d, 80, "FREE PRINTABLE", font(800, 46), GREEN)
    for i, line in enumerate(spec["headline"]):
        centered(d, 150 + i * 105, line, font(800, 92), INK)
    doc = fitz.open(FREE_PDF)
    page_idx = spec.get("page", 1)
    pix = doc[page_idx].get_pixmap(dpi=110)
    pg = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    pg = pg.resize((700, int(700 * pg.height / pg.width)), Image.LANCZOS)
    shadow = Image.new("RGBA", (pg.width + 80, pg.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle([40, 52, 40 + pg.width, 52 + pg.height], fill=(0, 0, 0, 80))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    top = 150 + len(spec["headline"]) * 105 + 30
    im.paste(shadow, ((W - shadow.width) // 2, top - 40), shadow)
    crop = pg.crop((0, 0, pg.width, min(pg.height, H - 170 - top)))
    im.paste(crop, ((W - crop.width) // 2, top))
    footer(d, "No sign-up · debtlabai.com")
    return im


def render_text(spec):
    im = Image.new("RGB", (W, H), spec.get("bg", BRAND))
    d = ImageDraw.Draw(im)
    dark = spec.get("bg", BRAND) != SOFT
    block = 90 + len(spec["headline"]) * 122 + 40 + len(spec["points"]) * 145
    y = max(110, (H - 140 - block) // 2)
    centered(d, y, spec["kicker"], font(800, 44), (191, 211, 245) if dark else BRAND)
    y += 90
    for line in spec["headline"]:
        centered(d, y, line, font(800, 104), WHITE if dark else INK)
        y += 122
    y += 40
    for line in spec["points"]:
        d.rounded_rectangle([90, y, W - 90, y + 120], radius=28, fill=WHITE)
        centered(d, y + 38, line, font(600, 42), INK)
        y += 145
    footer(d)
    return im


RENDER = {"payoff": render_payoff, "freebie": render_freebie, "text": render_text}


# ---------------------------------------------------------------- queue
def blog_posts():
    posts = []
    for md in sorted((ROOT / "web" / "content" / "blog").glob("*.md")):
        text = md.read_text(encoding="utf-8")
        if re.search(r"^draft:\s*true", text, re.M):
            continue
        title = re.search(r'^title:\s*"?(.*?)"?\s*$', text, re.M)
        desc = re.search(r'^description:\s*"?(.*?)"?\s*$', text, re.M)
        if title:
            posts.append((md.stem, title.group(1), desc.group(1) if desc else ""))
    return posts


def wrap(text, width=16):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + [cur]


def queue():
    """Deterministic, interleaved list of every pin we could post."""
    free = [
        {"id": "free-chart", "type": "freebie", "page": 1, "headline": ["Debt payoff", "coloring chart"],
         "title": "Free Debt Payoff Coloring Chart (Printable PDF)",
         "description": "Color one circle for every 1% of debt you pay off. Free printable debt tracker with a debt list and 60-month countdown. No sign-up.",
         "link": f"{SITE}/free-debt-payoff-planner/"},
        {"id": "free-countdown", "type": "freebie", "page": 2, "headline": ["Debt-free", "countdown"],
         "title": "Free Printable Debt-Free Countdown Tracker",
         "description": "60 months to cross off on your way to debt free. Free PDF with a debt list and coloring chart.",
         "link": f"{SITE}/free-debt-payoff-planner/"},
        {"id": "free-list", "type": "freebie", "page": 0, "headline": ["Free debt", "tracker"],
         "title": "Free Printable Debt Tracker: List Every Debt",
         "description": "Write down every balance, APR and minimum in one place. Free printable debt payoff tracker, letter size PDF.",
         "link": f"{SITE}/free-debt-payoff-planner/"},
    ]
    calcs = [
        {"id": "calc-snowball", "type": "text", "kicker": "FREE CALCULATOR", "headline": ["Debt", "snowball", "calculator"],
         "points": ["Smallest balance first", "See your debt-free date", "Free, nothing to sign up"],
         "title": "Debt Snowball Calculator (Free)", "description": "Enter your debts and see your debt-free date with the snowball method, plus the interest you pay.",
         "link": f"{SITE}/calculators/debt-snowball/"},
        {"id": "calc-avalanche", "type": "text", "kicker": "FREE CALCULATOR", "headline": ["Debt", "avalanche", "calculator"], "bg": SOFT,
         "points": ["Highest APR first", "Pay the least interest", "Compare with snowball"],
         "title": "Debt Avalanche Calculator (Free)", "description": "See how much interest the avalanche method could save versus the snowball, with your own numbers.",
         "link": f"{SITE}/calculators/debt-avalanche/"},
        {"id": "calc-card", "type": "text", "kicker": "FREE CALCULATOR", "headline": ["How long to", "pay off my", "credit card?"],
         "points": ["Balance + APR + payment", "Months and total interest", "What +$100/mo changes"],
         "title": "Credit Card Payoff Calculator: How Long Will It Take?", "description": "Free calculator: see how long your credit card takes to pay off and how much a bigger payment saves.",
         "link": f"{SITE}/calculators/credit-card-payoff/"},
    ]
    payoffs = []
    # spread across balances/APRs instead of 1000@18, 1000@20, ...
    order = sorted(((b, a) for b in BALANCES for a in APRS), key=lambda t: ((BALANCES.index(t[0]) * 5 + APRS.index(t[1]) * 7) % 13, t))
    for b, a in order:
        mn = dm.payoff_minimum(b, a)
        p36 = pmt(b, a, 36)
        payoffs.append({
            "id": f"payoff-{b}-{a}", "type": "payoff", "balance": b, "apr": a,
            "title": f"How to Pay Off {money(b)} Credit Card Debt at {a}% APR",
            "description": (f"{money(b)} at {a}% APR with only minimum payments could take {ym(mn['months'])} and cost "
                            f"{money(mn['total_interest'])} in interest. Paying {money(p36)} a month clears it in 3 years. "
                            "See the full payoff table, balance transfer and loan math. Educational, not financial advice."),
            "link": f"{SITE}/payoff/{b}-at-{a}-apr/",
        })
    posts = [
        {"id": f"blog-{slug}", "type": "text", "kicker": "DEBT MATH", "headline": wrap(title)[:4],
         "points": [], "title": title[:100], "description": desc or title, "link": f"{SITE}/blog/{slug}/",
         "bg": SOFT if i % 2 else BRAND}
        for i, (slug, title, desc) in enumerate(blog_posts())
    ]
    # interleave: freebie/calc first, then payoff, payoff, blog, payoff, ...
    out = free[:1] + calcs[:1]
    extras = free[1:] + calcs[1:] + posts
    for i, p in enumerate(payoffs):
        out.append(p)
        if i % 2 == 1 and extras:
            out.append(extras.pop(0))
    return out + extras


def posted_ids():
    if not POSTED.exists():
        return set()
    with POSTED.open(encoding="utf-8") as f:
        return {r["id"] for r in csv.DictReader(f)}


def pending():
    done = posted_ids()
    return [p for p in queue() if p["id"] not in done]


def render(spec):
    return RENDER[spec["type"]](spec)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=int, default=6)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    q = pending()
    print(f"{len(q)} pins pending")
    for spec in q[: args.preview]:
        render(spec).save(OUT / f"{spec['id']}.png")
        print(spec["id"], "|", spec["title"])
