"""Turns a topic row into computed facts (for the script) and chart data (for the video)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
import debt_math as dm  # noqa: E402


def money(x):
    return f"${round(x):,}"


def years_months(m):
    y, mo = divmod(int(m), 12)
    ys = f"{y} year" + ("s" if y != 1 else "")
    ms = f"{mo} month" + ("s" if mo != 1 else "")
    if y and mo:
        return f"{ys} and {ms}"
    return ys if y else ms


def build(topic):
    """Returns {"facts": {...}, "hook": {...}, "chart": {...}, "stats": [...]}"""
    p = json.loads(topic["params"]) if isinstance(topic["params"], str) else topic["params"]
    return BUILDERS[topic["pillar"]](p)


def _min_trap(p):
    r = dm.payoff_minimum(p["balance"], p["apr"], p["min_pct"], p["min_floor"])
    facts = {
        "balance": money(p["balance"]),
        "apr": f"{p['apr']}%",
        "minimum_rule": f"{p['min_pct']}% of the balance plus that month's interest, at least {money(p['min_floor'])}",
        "first_minimum_payment": money(r["first_payment"]),
        "time_to_pay_off": years_months(r["months"]),
        "total_interest_paid": money(r["total_interest"]),
        "total_paid": money(p["balance"] + r["total_interest"]),
    }
    return {
        "facts": facts,
        "hook": {"big": years_months(r["months"]).split(" and ")[0].upper(), "small": f"to clear {money(p['balance'])} with minimums"},
        "chart": {"type": "lines", "series": [{"label": "Minimum only", "data": r["history"], "color": "red"}], "x_unit": "months"},
        "stats": [("Interest paid", money(r["total_interest"])), ("Time", years_months(r["months"]))],
    }


def _extra_payment(p):
    c = dm.compare(p["balance"], p["apr"], p["payment"], p["extra"])
    facts = {
        "balance": money(p["balance"]),
        "apr": f"{p['apr']}%",
        "monthly_payment": money(p["payment"]),
        "extra_per_month": money(p["extra"]),
        "time_with_payment_only": years_months(c["min_only"]["months"]),
        "interest_with_payment_only": money(c["min_only"]["total_interest"]),
        "time_with_extra": years_months(c["with_extra"]["months"]),
        "interest_with_extra": money(c["with_extra"]["total_interest"]),
        "time_saved": years_months(c["months_saved"]),
        "interest_saved": money(c["interest_saved"]),
    }
    return {
        "facts": facts,
        "hook": {"big": money(c["interest_saved"]), "small": f"saved with {money(p['extra'])} extra a month"},
        "chart": {
            "type": "lines",
            "series": [
                {"label": f"{money(p['payment'])}/mo", "data": c["min_only"]["history"], "color": "red"},
                {"label": f"{money(p['payment'] + p['extra'])}/mo", "data": c["with_extra"]["history"], "color": "green"},
            ],
            "x_unit": "months",
        },
        "stats": [("Interest saved", money(c["interest_saved"])), ("Time saved", years_months(c["months_saved"]))],
    }


def _snowball(p):
    c = dm.snowball_vs_avalanche(p["debts"], p["budget"])
    total = sum(d["balance"] for d in p["debts"])
    winner = "avalanche" if c["interest_diff"] > 0 else "snowball" if c["interest_diff"] < 0 else "tie"
    # "Card A" / "Visa" keep their case; generic two-word names read as "the store card"
    named = lambda n: n if n.startswith("Card") else f"the {n.lower()}" if " " in n else f"the {n}"  # noqa: E731
    facts = {
        "debts": [f"{d['name']}: {money(d['balance'])} at {d['apr']}%" for d in p["debts"]],
        "total_debt": money(total),
        "monthly_budget": money(p["budget"]),
        "snowball_time": years_months(c["snowball"]["months"]),
        "snowball_interest": money(c["snowball"]["total_interest"]),
        "snowball_first_paid_off": named(c["snowball"]["payoff_order"][0]),
        "avalanche_time": years_months(c["avalanche"]["months"]),
        "avalanche_interest": money(c["avalanche"]["total_interest"]),
        "avalanche_first_paid_off": named(c["avalanche"]["payoff_order"][0]),
        "interest_difference": money(abs(c["interest_diff"])),
        "cheaper_method": winner,
    }
    big = money(abs(c["interest_diff"])) if winner != "tie" else "TIE"
    return {
        "facts": facts,
        "hook": {"big": big, "small": f"difference on {money(total)} of debt"},
        "chart": {
            "type": "lines",
            "series": [
                {"label": "Snowball", "data": c["snowball"]["history"], "color": "blue"},
                {"label": "Avalanche", "data": c["avalanche"]["history"], "color": "green"},
            ],
            "x_unit": "months",
        },
        "stats": [("Snowball interest", money(c["snowball"]["total_interest"])), ("Avalanche interest", money(c["avalanche"]["total_interest"]))],
    }


def _utilization(p):
    r = dm.utilization(p["balance"], p["limit"])
    facts = {
        "balance": money(p["balance"]),
        "credit_limit": money(p["limit"]),
        "utilization": f"{r['utilization_pct']:g}%",
        "common_guideline": "under 30%, and under 10% is often better",
        "pay_to_get_under_30_percent": money(r["pay_to_30"]),
        "pay_to_get_under_10_percent": money(r["pay_to_10"]),
        "tip_timing": "utilization is usually reported on the statement closing date",
    }
    return {
        "facts": facts,
        "hook": {"big": f"{r['utilization_pct']:.0f}%", "small": "credit utilization"},
        "chart": {
            "type": "bars",
            "bars": [
                {"label": "Now", "value": r["utilization_pct"], "color": "red"},
                {"label": f"Pay {money(r['pay_to_30'])}", "value": 30.0, "color": "yellow"},
                {"label": f"Pay {money(r['pay_to_10'])}", "value": 10.0, "color": "green"},
            ],
        },
        "stats": [("Pay for 30%", money(r["pay_to_30"])), ("Pay for 10%", money(r["pay_to_10"]))],
    }


def _apr_gap(p):
    hi, lo = dm.payoff(p["balance"], p["apr_high"], p["payment"]), dm.payoff(p["balance"], p["apr_low"], p["payment"])
    diff = round(hi["total_interest"]) - round(lo["total_interest"])
    facts = {
        "balance": money(p["balance"]),
        "monthly_payment": money(p["payment"]),
        "high_apr": f"{p['apr_high']}%",
        "low_apr": f"{p['apr_low']}%",
        "time_at_high_apr": years_months(hi["months"]),
        "interest_at_high_apr": money(hi["total_interest"]),
        "time_at_low_apr": years_months(lo["months"]),
        "interest_at_low_apr": money(lo["total_interest"]),
        "interest_difference": money(diff),
        "time_difference": years_months(hi["months"] - lo["months"]),
    }
    return {
        "facts": facts,
        "hook": {"big": money(diff), "small": f"the APR gap costs on {money(p['balance'])}"},
        "chart": {
            "type": "lines",
            "series": [
                {"label": f"{p['apr_high']}% APR", "data": hi["history"], "color": "red"},
                {"label": f"{p['apr_low']}% APR", "data": lo["history"], "color": "green"},
            ],
            "x_unit": "months",
        },
        "stats": [("Extra interest", money(diff)), ("Extra time", years_months(hi["months"] - lo["months"]))],
    }


def promo_payoff(balance, apr, payment, promo_months, fee_pct):
    """Balance transfer: fee added up front, 0% for promo_months, then the regular APR."""
    bal = balance * (1 + fee_pct / 100)
    history, months, interest = [round(bal, 2)], 0, 0.0
    r = apr / 100 / 12
    while bal > 0.005 and months < dm.MAX_MONTHS:
        i = bal * r if months >= promo_months else 0.0
        if payment <= i:
            return None
        interest += i
        bal = max(0.0, bal + i - payment)
        months += 1
        history.append(round(bal, 2))
    return {"months": months, "total_interest": round(interest, 2), "fee": round(balance * fee_pct / 100, 2), "history": history}


def _balance_transfer(p):
    stay = dm.payoff(p["balance"], p["apr"], p["payment"])
    bt = promo_payoff(p["balance"], p["apr"], p["payment"], p["promo_months"], p["fee_pct"])
    cost_bt = round(bt["total_interest"]) + round(bt["fee"])
    saved = round(stay["total_interest"]) - cost_bt
    facts = {
        "balance": money(p["balance"]),
        "apr": f"{p['apr']}%",
        "monthly_payment": money(p["payment"]),
        "intro_offer": f"0% for {p['promo_months']} months with a {p['fee_pct']}% transfer fee",
        "transfer_fee": money(bt["fee"]),
        "interest_if_you_stay": money(stay["total_interest"]),
        "time_if_you_stay": years_months(stay["months"]),
        "interest_plus_fee_with_transfer": money(cost_bt),
        "time_with_transfer": years_months(bt["months"]),
        "difference": money(saved),
        "assumptions": "you qualify for the offer, make no new charges and the rate after the promo is the same APR",
    }
    return {
        "facts": facts,
        "hook": {"big": money(saved), "small": f"difference with a 0% transfer on {money(p['balance'])}"},
        "chart": {
            "type": "lines",
            "series": [
                {"label": f"Stay at {p['apr']}%", "data": stay["history"], "color": "red"},
                {"label": f"0% for {p['promo_months']} mo", "data": bt["history"], "color": "green"},
            ],
            "x_unit": "months",
        },
        "stats": [("Fee", money(bt["fee"])), ("Difference", money(saved))],
    }


def _payment_ladder(p):
    pays = p["payments"]
    rs = [dm.payoff(p["balance"], p["apr"], x) for x in pays]
    facts = {
        "balance": money(p["balance"]),
        "apr": f"{p['apr']}%",
        "payments_compared": [f"{money(x)} a month: {years_months(r['months'])}, {money(r['total_interest'])} interest"
                              for x, r in zip(pays, rs)],
        "slowest_time": years_months(rs[0]["months"]),
        "fastest_time": years_months(rs[-1]["months"]),
        "interest_difference_slowest_vs_fastest": money(round(rs[0]["total_interest"]) - round(rs[-1]["total_interest"])),
    }
    return {
        "facts": facts,
        "hook": {"big": years_months(rs[-1]["months"]).split(" and ")[0].upper(),
                 "small": f"vs {years_months(rs[0]['months'])} on {money(p['balance'])}"},
        "chart": {
            "type": "lines",
            "series": [{"label": f"{money(x)}/mo", "data": r["history"], "color": c}
                       for x, r, c in zip(pays, rs, ("red", "yellow", "green"))],
            "x_unit": "months",
        },
        "stats": [("Slowest", years_months(rs[0]["months"])), ("Fastest", years_months(rs[-1]["months"]))],
    }


def _two_friends(p):
    n1, n2 = p["names"]
    lo = dm.payoff_minimum(p["balance"], p["apr"], 1, 25)
    hi = dm.payoff(p["balance"], p["apr"], p["payment"])
    diff = round(lo["total_interest"]) - round(hi["total_interest"])
    facts = {
        "balance": money(p["balance"]),
        "apr": f"{p['apr']}%",
        "friend_paying_minimum": n1,
        "friend_paying_fixed": n2,
        f"{n2}_monthly_payment": money(p["payment"]),
        f"{n1}_first_minimum_payment": money(lo["first_payment"]),
        f"{n1}_time_to_pay_off": years_months(lo["months"]),
        f"{n1}_total_interest": money(lo["total_interest"]),
        f"{n2}_time_to_pay_off": years_months(hi["months"]),
        f"{n2}_total_interest": money(hi["total_interest"]),
        "interest_difference": money(diff),
    }
    return {
        "facts": facts,
        "hook": {"big": money(diff), "small": f"difference between {n1} and {n2}"},
        "chart": {
            "type": "lines",
            "series": [
                {"label": f"{n1} (minimum)", "data": lo["history"], "color": "red"},
                {"label": f"{n2} ({money(p['payment'])}/mo)", "data": hi["history"], "color": "green"},
            ],
            "x_unit": "months",
        },
        "stats": [(f"{n1}", years_months(lo["months"]).split(" and ")[0]), (f"{n2}", years_months(hi["months"]).split(" and ")[0])],
    }


BUILDERS = {
    "two_friends": _two_friends,
    "min_trap": _min_trap,
    "extra_payment": _extra_payment,
    "snowball_vs_avalanche": _snowball,
    "utilization": _utilization,
    "apr_gap": _apr_gap,
    "balance_transfer": _balance_transfer,
    "payment_ladder": _payment_ladder,
}
