"""CTA text, video card, description and tags. All links come from shared/links.json;
empty links are simply left out."""
import json
from pathlib import Path

LINKS = Path(__file__).resolve().parent.parent / "shared" / "links.json"

AFFILIATE_NOTE = "We may earn a commission if you sign up through our links."
DISCLAIMER = (
    "Educational only. Not financial advice. Numbers are estimates based on the stated "
    "balance, APR and payment, assuming no new charges."
)

TAGS = {
    "min_trap": ["minimum payment", "credit card debt", "credit card interest", "debt payoff"],
    "extra_payment": ["pay off debt faster", "extra payment", "credit card debt", "debt payoff"],
    "snowball_vs_avalanche": ["debt snowball", "debt avalanche", "snowball vs avalanche", "debt payoff plan"],
    "utilization": ["credit utilization", "credit score", "raise credit score", "credit card tips"],
    "apr_gap": ["credit card APR", "lower interest rate", "credit card interest", "debt payoff"],
    "balance_transfer": ["balance transfer", "0% APR", "credit card debt", "debt payoff"],
    "payment_ladder": ["debt payoff calculator", "monthly payment", "credit card debt", "pay off debt faster"],
}
HASHTAGS = {
    "min_trap": "#creditcarddebt #debtfree",
    "extra_payment": "#debtfree #payoffdebt",
    "snowball_vs_avalanche": "#debtsnowball #debtfree",
    "utilization": "#creditscore #creditcards",
    "apr_gap": "#creditcarddebt #apr",
    "balance_transfer": "#balancetransfer #debtfree",
    "payment_ladder": "#debtfree #payoffdebt",
}


def links():
    return json.loads(LINKS.read_text(encoding="utf-8"))


def cta(l=None):
    """Returns (spoken_text, card) for the end of the video."""
    l = l or links()
    if l.get("website"):
        return (
            "Get your free debt payoff plan at the link in the description.",
            {"headline": "FREE DEBT PLAN", "lines": ["Link in description", _domain(l["website"])]},
        )
    if l.get("play_store") or l.get("app_store"):
        return (
            "Get the free DebtLab app at the link in the description.",
            {"headline": "GET THE APP", "lines": ["Free debt payoff planner", "Link in description"]},
        )
    return (
        "Follow for more real debt math.",
        {"headline": "FOLLOW", "lines": ["Real debt math", "every day"]},
    )


def _domain(url):
    return url.split("//")[-1].rstrip("/")


def description(topic, built, l=None):
    l = l or links()
    out = [topic["title"], ""]
    out += [
        f"{k.replace('_', ' ').capitalize().replace('Apr', 'APR')}: {v}"
        for k, v in built["facts"].items()
        if not isinstance(v, list)
    ]
    for item in built["facts"].get("debts", []):
        out.append(f"  - {item}")
    out.append("")
    if l.get("website"):
        out.append(f"Free debt calculators: {l['website']}")
    if l.get("play_store"):
        out.append(f"Android app: {l['play_store']}")
    if l.get("app_store"):
        out.append(f"iPhone app: {l['app_store']}")
    if l.get("affiliate_experian"):
        out.append(f"Check your real credit score: {l['affiliate_experian']}")
        out.append(AFFILIATE_NOTE)
    out += ["", DISCLAIMER, "", f"#Shorts {HASHTAGS[topic['pillar']]} #personalfinance"]
    return "\n".join(out)


def tags(topic):
    return TAGS[topic["pillar"]] + ["personal finance", "DebtLab", "shorts"]


def title(topic):
    t = topic["title"]
    return t if len(t) + 8 > 100 else f"{t} #Shorts"
