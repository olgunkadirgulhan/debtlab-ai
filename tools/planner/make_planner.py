"""Builds the printable DebtLab Debt Payoff Planner (paid product) and the free sample.

    python tools/planner/make_planner.py

Outputs:
    product/DebtLab-Debt-Payoff-Planner-Letter.pdf   (sell on Etsy / Gumroad)
    product/DebtLab-Debt-Payoff-Planner-A4.pdf
    web/public/downloads/free-debt-payoff-tracker.pdf (3-page free sample linked from the site)

Every number printed in the planner comes from shared/debt_math.py.
"""
import sys
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))
import debt_math as dm  # noqa: E402

FONTS = Path(__file__).resolve().parent / "fonts"
pdfmetrics.registerFont(TTFont("R", FONTS / "Montserrat-400.ttf"))
pdfmetrics.registerFont(TTFont("S", FONTS / "Montserrat-600.ttf"))
pdfmetrics.registerFont(TTFont("B", FONTS / "Montserrat-800.ttf"))

BRAND = HexColor("#0F52BA")
SOFT = HexColor("#EAF1FC")
GREEN = HexColor("#16A34A")
GREEN_SOFT = HexColor("#E8F7EE")
RED = HexColor("#DC2626")
INK = HexColor("#0F172A")
MUTED = HexColor("#64748B")
LINE = HexColor("#CBD5E1")
SITE = "debtlabai.com"
M = 40  # page margin


def money(x):
    return f"${round(x):,}"


def years_months(n):
    y, m = divmod(n, 12)
    parts = ([f"{y} yr"] if y else []) + ([f"{m} mo"] if m else [])
    return " ".join(parts) or "0 mo"


class Planner:
    def __init__(self, path, size):
        self.c = Canvas(str(path), pagesize=size)
        self.c.setTitle("DebtLab Debt Payoff Planner")
        self.c.setAuthor("DebtLab")
        self.W, self.H = size
        self.page = 0

    # ---------- primitives ----------
    def text(self, x, y, s, font="R", size=10, color=INK, align="left"):
        c = self.c
        c.setFont(font, size)
        c.setFillColor(color)
        {"left": c.drawString, "center": c.drawCentredString, "right": c.drawRightString}[align](x, y, s)

    def wrap(self, x, y, s, width, font="R", size=10, color=INK, leading=None):
        leading = leading or size * 1.45
        words, line = s.split(), ""
        for w in words:
            trial = f"{line} {w}".strip()
            if pdfmetrics.stringWidth(trial, font, size) > width and line:
                self.text(x, y, line, font, size, color)
                y -= leading
                line = w
            else:
                line = trial
        if line:
            self.text(x, y, line, font, size, color)
            y -= leading
        return y

    def rect(self, x, y, w, h, fill=None, stroke=LINE, r=6, lw=0.8):
        c = self.c
        c.setLineWidth(lw)
        c.setStrokeColor(stroke or white)
        if fill:
            c.setFillColor(fill)
        c.roundRect(x, y, w, h, r, stroke=1 if stroke else 0, fill=1 if fill else 0)

    def hline(self, x1, x2, y, color=LINE, lw=0.6):
        self.c.setStrokeColor(color)
        self.c.setLineWidth(lw)
        self.c.line(x1, y, x2, y)

    def header(self, title, subtitle=None):
        """Starts a page. Returns the y below the header."""
        if self.page:
            self.c.showPage()
        self.page += 1
        W, H = self.W, self.H
        self.rect(M, H - M - 6, 26, 6, fill=BRAND, stroke=None, r=3)
        self.text(M, H - M - 34, title, "B", 22)
        y = H - M - 34
        if subtitle:
            y = self.wrap(M, y - 20, subtitle, W - 2 * M, size=10, color=MUTED)
        else:
            y -= 12
        # footer
        self.hline(M, W - M, M + 8)
        self.text(M, M - 4, "DebtLab Debt Payoff Planner", "S", 8, MUTED)
        self.text(W - M, M - 4, f"{SITE}  ·  {self.page}", "R", 8, MUTED, "right")
        return y - 10

    def table(self, x, y, widths, heads, rows, row_h=20, fill_rows=None, head_fill=SOFT, total=False):
        """Empty fill-in table. widths are fractions of the available width. Returns bottom y."""
        avail = self.W - M - x
        ws = [avail * f for f in widths]
        self.rect(x, y - row_h, avail, row_h, fill=head_fill, stroke=None, r=4)
        cx = x
        for w, h in zip(ws, heads):
            self.text(cx + 6, y - row_h + 6.5, h, "S", 8.5, BRAND if head_fill == SOFT else INK)
            cx += w
        yy = y - row_h
        for i in range(rows):
            if fill_rows:
                cx = x
                for w, v in zip(ws, fill_rows[i]):
                    self.text(cx + 6, yy - row_h + 6.5, str(v), "S" if cx == x else "R", 9)
                    cx += w
            yy -= row_h
            self.hline(x, x + avail, yy)
        # column guides
        cx = x
        self.c.setStrokeColor(LINE)
        for w in ws[:-1]:
            cx += w
            self.c.line(cx, y - row_h, cx, yy)
        if total:
            self.rect(x, yy - row_h - 4, avail, row_h, fill=GREEN_SOFT, stroke=None, r=4)
            self.text(x + 6, yy - row_h + 2.5, "TOTAL", "B", 9, GREEN)
            yy -= row_h + 4
        return yy

    def field(self, x, y, label, width):
        self.text(x, y, label, "S", 9, MUTED)
        lw = pdfmetrics.stringWidth(label, "S", 9)
        self.hline(x + lw + 6, x + width, y - 2, INK, 0.7)

    def lines(self, y, bottom, gap=22):
        while y > bottom:
            self.hline(M, self.W - M, y)
            y -= gap

    def section(self, y, label):
        self.text(M, y, label.upper(), "B", 10, BRAND)
        return y - 10

    # ---------- pages ----------
    def cover(self):
        self.page += 1
        W, H = self.W, self.H
        c = self.c
        c.setFillColor(BRAND)
        c.rect(0, H * 0.42, W, H * 0.58, stroke=0, fill=1)
        # rising "paid off" bars
        c.setFillColor(HexColor("#2D6FD6"))
        n = 9
        bw = (W - 2 * M) / n
        for i in range(n):
            h = 40 + i * 22
            c.roundRect(M + i * bw + 6, H * 0.42, bw - 12, h, 6, stroke=0, fill=1)
        self.text(M, H - 110, "DEBTLAB", "B", 12, HexColor("#BFD3F5"))
        self.text(M, H - 170, "Debt Payoff", "B", 46, white)
        self.text(M, H - 222, "Planner", "B", 46, white)
        self.text(M, H - 256, "Plan it. Track it. Finish it.", "S", 15, HexColor("#DCE7FA"))
        y = H * 0.42 - 60
        for label in ["Name", "Start date", "Total debt today", "My debt-free goal date"]:
            self.field(M, y, label, W - 2 * M)
            y -= 40
        self.text(M, M + 10, "Snowball & avalanche worksheets · 6 debt trackers · coloring chart · interest cheat sheet", "R", 8.5, MUTED)
        self.text(W - M, M - 4, SITE, "S", 8.5, BRAND, "right")

    def how_to(self):
        y = self.header("How to use this planner", "Six steps, about 30 minutes to set up. Then 10 minutes a month.")
        steps = [
            ("List every debt", "Fill in My Debts with the balance, APR, minimum payment and due day from your latest statements."),
            ("Find your extra money", "Use the Monthly Budget page. Whatever is left after bills and minimums is your debt payment power."),
            ("Pick a method", "Snowball (smallest balance first) for quick wins, or avalanche (highest APR first) to pay the least interest."),
            ("Set the order", "Write your debts in order on the Snowball or Avalanche page. Every month: minimums on all, extra on #1."),
            ("Track every payment", "Each debt gets a tracker. When one is paid off, roll its whole payment into the next debt."),
            ("Color your progress", "Fill the coloring chart and countdown as the total drops. Write your wins down; they keep you going."),
        ]
        for i, (t, d) in enumerate(steps, 1):
            self.rect(M, y - 26, 26, 26, fill=BRAND, stroke=None, r=13)
            self.text(M + 13, y - 17, str(i), "B", 12, white, "center")
            self.text(M + 40, y - 9, t, "B", 12)
            y = self.wrap(M + 40, y - 25, d, self.W - 2 * M - 40, size=9.5, color=MUTED) - 12
        y -= 6
        half = (self.W - 2 * M - 16) / 2
        for i, (title, color, soft, lines) in enumerate(
            [
                ("SNOWBALL", BRAND, SOFT, ["Smallest balance first.", "Fast first win, strong motivation.", "Can cost a bit more interest."]),
                ("AVALANCHE", GREEN, GREEN_SOFT, ["Highest APR first.", "Lowest total interest.", "First win can take longer."]),
            ]
        ):
            x = M + i * (half + 16)
            self.rect(x, y - 110, half, 110, fill=soft, stroke=None, r=10)
            self.text(x + 16, y - 26, title, "B", 13, color)
            yy = y - 50
            for line in lines:
                self.text(x + 16, yy, "•  " + line, "R", 10)
                yy -= 18
        y -= 140
        self.wrap(
            M, y,
            "Educational tool only, not financial advice. Figures in this planner are estimates based on fixed monthly interest "
            "(APR ÷ 12) and no new charges. Your lender's numbers may differ. Free calculators: " + SITE,
            self.W - 2 * M, size=8, color=MUTED,
        )

    def my_debts(self):
        y = self.header("My Debts", "Everything you owe, in one place. Use your latest statements.")
        y = self.table(M, y, [0.26, 0.15, 0.1, 0.15, 0.1, 0.24], ["Creditor", "Balance", "APR", "Min payment", "Due day", "Notes"], 16, row_h=24, total=True)
        y -= 30
        third = (self.W - 2 * M - 24) / 3
        for i, label in enumerate(["Total debt", "Total minimums / mo", "Highest APR"]):
            x = M + i * (third + 12)
            self.rect(x, y - 54, third, 54, fill=SOFT, stroke=None, r=8)
            self.text(x + 12, y - 20, label.upper(), "S", 8, BRAND)

    def order_pages(self):
        y = self.header("Payoff order", "Write your debts in the order you will attack them. Minimums on all; every extra dollar to #1.")
        for title, rule, color, soft in [
            ("Snowball order", "Smallest balance → largest", BRAND, SOFT),
            ("Avalanche order", "Highest APR → lowest", GREEN, GREEN_SOFT),
        ]:
            self.text(M, y, title, "B", 13, color)
            self.text(self.W - M, y, rule, "S", 9, MUTED, "right")
            y = self.table(M, y - 8, [0.07, 0.31, 0.16, 0.1, 0.16, 0.2], ["#", "Debt", "Balance", "APR", "Payment", "Paid off on"], 8, row_h=24, head_fill=soft)
            y -= 34
        self.text(M, y, "My method:", "S", 10)
        for i, opt in enumerate(["Snowball", "Avalanche", "Mix"]):
            x = M + 90 + i * 110
            self.rect(x, y - 3, 12, 12, r=2)
            self.text(x + 18, y, opt, "R", 10)

    def budget(self):
        y = self.header("Monthly budget", "Month: ________________   Find the money for your extra debt payment.")
        half = (self.W - 2 * M - 20) / 2
        top = y
        for col, blocks in enumerate([[("Income", 6), ("Fixed bills", 11)], [("Flexible spending", 11), ("Savings & goals", 6)]]):
            x = M + col * (half + 20)
            yy = top
            for title, n in blocks:
                self.rect(x, yy - 20, half, 20, fill=SOFT, stroke=None, r=4)
                self.text(x + 8, yy - 13.5, title, "S", 9, BRAND)
                self.text(x + half - 8, yy - 13.5, "Amount", "S", 9, BRAND, "right")
                yy -= 20
                for _ in range(n):
                    yy -= 20
                    self.hline(x, x + half, yy)
                yy -= 16
        y = min(yy, top) - 6
        self.rect(M, y - 88, self.W - 2 * M, 88, fill=GREEN_SOFT, stroke=None, r=10)
        labels = ["Income", "− Bills & spending", "− Minimum payments", "= Extra for debt"]
        w = (self.W - 2 * M) / 4
        for i, l in enumerate(labels):
            self.text(M + 14 + i * w, y - 24, l, "S", 9, GREEN)
            self.hline(M + 14 + i * w, M + i * w + w - 10, y - 62, INK, 0.7)

    def tracker_page(self, first_no):
        y = self.header("Debt trackers", "One per debt. Log each payment and the new balance from your statement.")
        for k in range(2):
            self.rect(M, y - 22, self.W - 2 * M, 22, fill=BRAND, stroke=None, r=5)
            self.text(M + 10, y - 15, f"DEBT {first_no + k}", "B", 9, white)
            fields = ["Name", "Start balance", "APR", "Min"]
            fx = M + 70
            fw = (self.W - M - fx) / 4
            for i, f in enumerate(fields):
                self.text(fx + i * fw, y - 15, f + ":", "S", 8.5, HexColor("#DCE7FA"))
            y -= 26
            avail_h = (y - (M + 20)) if k else (y - self.H / 2 + 10)
            rows = int((avail_h - 20) // 17)
            y = self.table(M, y, [0.2, 0.2, 0.2, 0.2, 0.2], ["Date", "Payment", "Extra", "Interest", "New balance"], rows, row_h=17) - 22

    def coloring_chart(self):
        y = self.header("Debt payoff coloring chart", "Each circle is 1% of your total debt. Color one in for every 1% you pay off.")
        self.field(M, y, "Total debt", 240)
        self.field(M + 270, y, "Each circle = $", self.W - 2 * M - 270)
        y -= 30
        size = min((self.W - 2 * M) / 10, (y - M - 80) / 10)
        x0 = M + (self.W - 2 * M - size * 10) / 2
        n = 0
        for r in range(10):
            for col in range(10):
                n += 1
                cx = x0 + col * size + size / 2
                cy = y - r * size - size / 2
                milestone = n % 25 == 0
                self.c.setStrokeColor(GREEN if milestone else BRAND)
                self.c.setLineWidth(1.6 if milestone else 1)
                self.c.circle(cx, cy, size * 0.42, stroke=1, fill=0)
                self.text(cx, cy - 3, f"{n}%" if milestone else str(n), "B" if milestone else "R", 7.5 if milestone else 7, GREEN if milestone else MUTED, "center")
        y -= size * 10 + 26
        self.text(self.W / 2, y, "25% · 50% · 75% · 100% — celebrate each green circle (cheaply!).", "S", 10, GREEN, "center")

    def countdown(self):
        y = self.header("Debt-free countdown", "60 months. Cross one off every month you make all your payments. Write the date inside.")
        cols, rows = 6, 10
        gw = (self.W - 2 * M) / cols
        gh = min(54, (y - M - 30) / rows)
        for i in range(60):
            r, col = divmod(i, cols)
            x = M + col * gw + 3
            yy = y - (r + 1) * gh + 3
            self.rect(x, yy, gw - 6, gh - 6, fill=SOFT if (i + 1) % 12 else GREEN_SOFT, stroke=None, r=6)
            self.text(x + 8, yy + gh - 20, f"MONTH {i + 1}", "S", 7.5, BRAND if (i + 1) % 12 else GREEN)
            if (i + 1) % 12 == 0:
                self.text(x + gw - 14, yy + 8, f"YEAR {(i + 1) // 12}", "B", 7.5, GREEN, "right")

    def checkin(self):
        y = self.header("Monthly check-in", "Ten minutes at the end of each month. Watching the total fall is the motivation.")
        self.table(M, y, [0.14, 0.16, 0.14, 0.18, 0.38], ["Month", "Total paid", "Extra paid", "Total debt left", "Win of the month"], 12, row_h=40)

    def cheat_sheet(self):
        y = self.header(
            "Interest cheat sheet",
            "Real math (APR ÷ 12, fixed payment, no new charges). Numbers are per $1,000 of balance: multiply by your balance in thousands.",
        )
        y = self.section(y, "Monthly payment to clear $1,000 in…")
        aprs = [15, 18, 20, 22, 24, 26, 29]
        terms = [12, 24, 36, 48, 60]

        def pmt(apr, n):
            r = apr / 1200
            return 1000 * r / (1 - (1 + r) ** -n)

        rows = [[f"{a}% APR", *[f"${pmt(a, n):.2f}" for n in terms]] for a in aprs]
        y = self.table(M, y - 4, [0.2] + [0.16] * 5, ["APR", *[f"{n} months" for n in terms]], len(rows), row_h=21, fill_rows=rows) - 28

        y = self.section(y, "Total interest per $1,000 at those payments")
        rows = []
        for a in aprs:
            cells = []
            for n in terms:
                res = dm.payoff(1000, a, pmt(a, n) + 1e-9)
                cells.append(money(res["total_interest"]))
            rows.append([f"{a}% APR", *cells])
        y = self.table(M, y - 4, [0.2] + [0.16] * 5, ["APR", *[f"{n} months" for n in terms]], len(rows), row_h=21, fill_rows=rows) - 28

        y = self.section(y, "The minimum-payment trap: $5,000 at 24% APR")
        mn = dm.payoff_minimum(5000, 24)
        fx = dm.payoff(5000, 24, 200)
        rows = [
            [f"Minimum only (starts {money(mn['first_payment'])}, shrinks)", years_months(mn["months"]), money(mn["total_interest"])],
            ["Fixed $200 every month", years_months(fx["months"]), money(fx["total_interest"])],
        ]
        self.table(M, y - 4, [0.56, 0.22, 0.22], ["Plan", "Time", "Interest"], 2, row_h=22, fill_rows=rows)

    def emergency_fund(self):
        y = self.header("Starter emergency fund", "A small cushion stops a surprise bill from going back on the card. Shade one bar per deposit.")
        self.field(M, y, "My goal  $", 220)
        self.field(M + 250, y, "Each bar = $", self.W - 2 * M - 250)
        y -= 30
        bars = 20
        bh = (y - M - 40) / bars
        w = 160
        x = (self.W - w) / 2
        for i in range(bars):
            yy = y - (i + 1) * bh
            self.rect(x, yy + 2, w, bh - 4, stroke=GREEN, r=4)
            self.text(x + w + 12, yy + bh / 2 - 3, f"{100 - i * 5}%", "S", 8, GREEN if i % 5 == 0 else MUTED)

    def wins(self):
        y = self.header("Milestones & wins", "Check them off. Small wins count.")
        items = [
            "Listed every debt and its APR", "Made a monthly budget", "Chose snowball or avalanche", "Built a starter emergency fund",
            "Paid more than the minimum for 3 months", "Stopped using the cards", "Paid off debt #1", "Rolled payment into debt #2",
            "Total debt down 25%", "Total debt down 50%", "Paid off debt #3", "Total debt down 75%", "Last payment made", "DEBT FREE",
        ]
        for it in items:
            self.rect(M, y - 13, 14, 14, r=3, stroke=BRAND)
            self.text(M + 24, y - 10, it, "B" if it == "DEBT FREE" else "R", 11, GREEN if it == "DEBT FREE" else INK)
            self.hline(self.W - M - 120, self.W - M, y - 12)
            y -= 30
        self.text(self.W - M - 120, y + 30 * len(items) + 6, "Date", "S", 8, MUTED)
        y -= 10
        self.text(M, y, "My why — the reason I'm doing this:", "S", 10, BRAND)
        self.lines(y - 26, M + 30)

    def notes(self):
        y = self.header("Notes")
        self.lines(y - 6, M + 30, gap=24)

    def save(self):
        self.c.save()


def build_full(path, size):
    p = Planner(path, size)
    p.cover()
    p.how_to()
    p.my_debts()
    p.order_pages()
    p.budget()
    for n in (1, 3, 5):
        p.tracker_page(n)
    p.coloring_chart()
    p.countdown()
    p.checkin()
    p.cheat_sheet()
    p.emergency_fund()
    p.wins()
    p.notes()
    p.save()
    return p.page


def build_free(path, size):
    p = Planner(path, size)
    p.my_debts()
    p.coloring_chart()
    p.countdown()
    # last page: what the full planner adds
    y = p.header("Want the full planner?")
    for line in [
        "This free sample has 3 pages. The full DebtLab Debt Payoff Planner (15 pages) adds:",
        "•  Snowball and avalanche order worksheets",
        "•  A monthly budget page to find your extra payment",
        "•  6 debt trackers, monthly check-ins and milestones",
        "•  An interest cheat sheet with real payoff math",
        "•  Letter and A4 sizes",
        "",
        f"Free calculators and the full planner: {SITE}",
    ]:
        p.text(M, y, line, "S" if line.startswith(("This", "Free")) else "R", 11)
        y -= 22
    p.save()
    return p.page


if __name__ == "__main__":
    out = ROOT / "product"
    out.mkdir(exist_ok=True)
    free = ROOT / "web" / "public" / "downloads"
    free.mkdir(parents=True, exist_ok=True)
    print("letter", build_full(out / "DebtLab-Debt-Payoff-Planner-Letter.pdf", letter), "pages")
    print("a4", build_full(out / "DebtLab-Debt-Payoff-Planner-A4.pdf", A4), "pages")
    print("free", build_free(free / "free-debt-payoff-tracker.pdf", letter), "pages")
