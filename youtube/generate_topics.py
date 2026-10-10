"""Generates youtube/topics.csv: ~600 non-repeating, pre-validated scenarios.

Run once (or again with a new --seed to append more). Rows that already exist
are kept, so published history stays consistent.

    python youtube/generate_topics.py --count 600
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "shared"))
import debt_math as dm  # noqa: E402

TOPICS = Path(__file__).resolve().parent / "topics.csv"
FIELDS = ["id", "pillar", "title", "params"]


def money(x):
    return f"${x:,.0f}"


TEMPLATES = {
    "min_trap": [
        "Paying only the minimum on {b} takes HOW long?",
        "{b} at {apr}% APR, minimum payments only. Brutal math",
        "The minimum payment trap on {b} of credit card debt",
        "Why your {b} card balance never goes down",
        "What the minimum payment really costs on {b}",
    ],
    "extra_payment": [
        "{b} at {apr}% APR: what an extra payment changes",
        "Add {x} a month to a {b} balance. Watch what happens",
        "How {x} extra per month kills {b} of debt faster",
        "{b} at {apr}%: paying {p} vs {p2} a month",
        "The {x} trick that saves months on {b} of debt",
    ],
    "snowball_vs_avalanche": [
        "Snowball vs Avalanche on {total}. Which wins?",
        "{n} debts, {total} total. Snowball or Avalanche?",
        "Debt Snowball vs Avalanche: the real numbers on {total}",
        "{n} debts, two methods: Snowball vs Avalanche",
        "Smallest balance first or highest APR first? {total} test",
    ],
    "utilization": [
        "Your {b} balance on a {l} limit is hurting your score",
        "How much to pay to get under 30% utilization on a {l} card",
        "{u}% credit utilization: the payoff math",
        "The credit utilization math on a {l} limit",
        "How much to pay before the statement closes ({b} on {l})",
    ],
    "apr_gap": [
        "Same {b} debt: {hi}% APR vs {lo}% APR",
        "What a {hi}% APR really costs on {b}",
        "{b} at {hi}% or {lo}%? The difference is wild",
        "Is your {hi}% APR costing you this much?",
        "How much a lower APR changes on {b}",
    ],
    "balance_transfer": [
        "Does a 0% balance transfer work on {b}?",
        "0% for {m} months on {b}: worth the {f}% fee?",
        "Balance transfer math on {b} at {apr}% APR",
        "Is a balance transfer worth it? {b} test",
        "{f}% fee vs {apr}% APR: the {b} balance transfer test",
    ],
    "payment_ladder": [
        "{b} of debt: paying {p1}, {p2} or {p3} a month?",
        "How long {b} takes at {p1} vs {p3} a month",
        "Pick your payment: {b} at {apr}% APR",
        "What changes if you pay {p3} instead of {p1}? ({b})",
        "The monthly payment that clears {b} fastest",
    ],
    "two_friends": [
        "Two friends, same {b} debt. One pays the minimum 😬",
        "{n1} pays the minimum. {n2} pays {p}. Same {b} debt",
        "Same {b} card, two choices: {n1} vs {n2}",
        "Minimum vs {p} a month on {b}: two friends compared",
        "{n1} and {n2} both owe {b}. Only one is out fast",
    ],
}
# Paylaşım ağırlığı: ilk 2 haftada min_trap ve utilization en çok izlendi; yeni türler denensin diye orta ağırlık
WEIGHTS = {"two_friends": 4, "min_trap": 3, "utilization": 3, "apr_gap": 2, "balance_transfer": 2, "payment_ladder": 2,
           "extra_payment": 1, "snowball_vs_avalanche": 1}


def round_to(x, step):
    return int(round(x / step) * step)


def make_min_trap(rng):
    b = round_to(rng.uniform(1000, 25000), 250)
    apr = rng.randint(15, 29)
    params = {"balance": b, "apr": apr, "min_pct": 1, "min_floor": 25}
    r = dm.payoff_minimum(b, apr, 1, 25)
    if r["months"] < 60 or r["months"] >= dm.MAX_MONTHS:
        return None
    t = rng.choice(TEMPLATES["min_trap"])
    return params, t.format(b=money(b), apr=apr)


def make_extra_payment(rng):
    b = round_to(rng.uniform(1000, 50000), 250)
    apr = rng.randint(15, 29)
    p = max(50, round_to(b * rng.uniform(0.025, 0.04), 10))
    x = rng.choice([25, 50, 75, 100, 150, 200, 250, 300, 400, 500])
    if x > p:
        x = round_to(p * 0.5, 25) or 25
    c = dm.compare(b, apr, p, x)
    if c is None or c["months_saved"] < 3:
        return None
    params = {"balance": b, "apr": apr, "payment": p, "extra": x}
    t = rng.choice(TEMPLATES["extra_payment"])
    return params, t.format(b=money(b), apr=apr, x=money(x), p=money(p), p2=money(p + x))


CARD_NAMES = ["Card A", "Card B", "Store card", "Card C", "Personal loan", "Card D"]


def make_snowball(rng):
    n = rng.randint(2, 5)
    names = rng.sample(CARD_NAMES, n)
    debts = []
    for name in names:
        b = round_to(rng.uniform(500, 15000), 100)
        apr = rng.randint(12, 29)
        debts.append({"name": name, "balance": b, "apr": apr, "min": max(25, round_to(b * 0.025, 5))})
    budget = sum(d["min"] for d in debts) + rng.choice([100, 150, 200, 300, 400, 500, 600])
    c = dm.snowball_vs_avalanche(debts, budget)
    if c is None:
        return None
    total = sum(d["balance"] for d in debts)
    params = {"debts": debts, "budget": budget}
    t = rng.choice(TEMPLATES["snowball_vs_avalanche"])
    return params, t.format(total=money(total), n=n)


def make_utilization(rng):
    l = rng.choice([1000, 1500, 2000, 2500, 3000, 4000, 5000, 7500, 10000, 12000, 15000, 20000])
    u = rng.randint(35, 95)
    b = round_to(l * u / 100, 50)
    r = dm.utilization(b, l)
    if r["utilization_pct"] <= 30:
        return None
    params = {"balance": b, "limit": l}
    t = rng.choice(TEMPLATES["utilization"])
    return params, t.format(b=money(b), l=money(l), u=round(r["utilization_pct"]))


def make_apr_gap(rng):
    b = round_to(rng.uniform(2000, 30000), 250)
    hi = rng.randint(24, 30)
    lo = rng.randint(12, hi - 6)
    p = max(60, round_to(b * rng.uniform(0.025, 0.045), 10))
    rh, rl = dm.payoff(b, hi, p), dm.payoff(b, lo, p)
    if rh is None or rl is None or round(rh["total_interest"]) - round(rl["total_interest"]) < 300:
        return None
    params = {"balance": b, "apr_high": hi, "apr_low": lo, "payment": p}
    return params, rng.choice(TEMPLATES["apr_gap"]).format(b=money(b), hi=hi, lo=lo)


def make_balance_transfer(rng):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from facts import promo_payoff
    b = round_to(rng.uniform(2000, 20000), 250)
    apr = rng.randint(20, 29)
    m = rng.choice([12, 15, 18, 21])
    f = rng.choice([3, 4, 5])
    p = max(80, round_to(b * rng.uniform(0.03, 0.06), 10))
    stay, bt = dm.payoff(b, apr, p), promo_payoff(b, apr, p, m, f)
    if stay is None or bt is None:
        return None
    if round(stay["total_interest"]) - (round(bt["total_interest"]) + round(bt["fee"])) < 200:
        return None
    params = {"balance": b, "apr": apr, "payment": p, "promo_months": m, "fee_pct": f}
    return params, rng.choice(TEMPLATES["balance_transfer"]).format(b=money(b), apr=apr, m=m, f=f)


def make_payment_ladder(rng):
    b = round_to(rng.uniform(2000, 25000), 250)
    apr = rng.randint(16, 29)
    p1 = max(60, round_to(b * rng.uniform(0.022, 0.03), 25))
    pays = [p1, round_to(p1 * 1.5, 25), round_to(p1 * 2, 25)]
    rs = [dm.payoff(b, apr, x) for x in pays]
    if any(r is None for r in rs) or rs[0]["months"] - rs[2]["months"] < 12 or len(set(pays)) < 3:
        return None
    params = {"balance": b, "apr": apr, "payments": pays}
    return params, rng.choice(TEMPLATES["payment_ladder"]).format(
        b=money(b), apr=apr, p1=money(pays[0]), p2=money(pays[1]), p3=money(pays[2]))


FRIENDS = ["Alex", "Sam", "Jordan", "Taylor", "Chris", "Morgan", "Jamie", "Casey", "Riley", "Drew"]


def make_two_friends(rng):
    """2026-10-10: kıyas formatı (Bloop'ta 'Normal vs Psycho' tuttu): aynı borç, biri minimum, biri sabit ödeme."""
    b = round_to(rng.uniform(3000, 20000), 250)
    apr = rng.randint(18, 29)
    p = max(100, round_to(b * rng.uniform(0.03, 0.05), 25))
    lo = dm.payoff_minimum(b, apr, 1, 25)
    hi = dm.payoff(b, apr, p)
    if hi is None or lo["months"] >= dm.MAX_MONTHS or lo["months"] - hi["months"] < 60:
        return None
    n1, n2 = rng.sample(FRIENDS, 2)
    params = {"balance": b, "apr": apr, "payment": p, "names": [n1, n2]}
    return params, rng.choice(TEMPLATES["two_friends"]).format(b=money(b), p=money(p), n1=n1, n2=n2)


MAKERS = {
    "two_friends": make_two_friends,
    "min_trap": make_min_trap,
    "extra_payment": make_extra_payment,
    "snowball_vs_avalanche": make_snowball,
    "utilization": make_utilization,
    "apr_gap": make_apr_gap,
    "balance_transfer": make_balance_transfer,
    "payment_ladder": make_payment_ladder,
}


def load_existing():
    if not TOPICS.exists():
        return []
    with TOPICS.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=600, help="new rows to add")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--drop-unpublished", action="store_true",
                    help="yayınlanmamış satırları sil (yeni türlerle yeniden karıştırmak için)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rows = load_existing()
    if args.drop_unpublished:
        pub = Path(__file__).resolve().parent / "published.csv"
        keep = set()
        if pub.exists():
            with pub.open(newline="", encoding="utf-8") as f:
                keep = {r["topic_id"] for r in csv.DictReader(f)}
        queue = Path(__file__).resolve().parent / "queue"
        if queue.exists():
            keep |= {json.loads(q.read_text(encoding="utf-8")).get("topic", {}).get("id") for q in queue.glob("*.json")}
        rows = [r for r in rows if r["id"] in keep]
    titles = {r["title"] for r in rows}
    next_id = max((int(r["id"]) for r in rows), default=0) + 1
    pillars = list(MAKERS)
    added, attempts = 0, 0
    while added < args.count and attempts < args.count * 50:
        attempts += 1
        # art arda aynı tür gelmesin; ağırlıklı seçim
        last = rows[-1]["pillar"] if rows else None
        options = [p for p in pillars if p != last]
        pillar = rng.choices(options, weights=[WEIGHTS.get(p, 1) for p in options])[0]
        made = MAKERS[pillar](rng)
        if not made:
            continue
        params, title = made
        if title in titles:
            continue
        titles.add(title)
        rows.append({"id": next_id, "pillar": pillar, "title": title, "params": json.dumps(params, separators=(",", ":"))})
        next_id += 1
        added += 1

    with TOPICS.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"added {added} topics, total {len(rows)}")


if __name__ == "__main__":
    main()
