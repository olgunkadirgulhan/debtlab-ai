"""Voiceover script: Gemini first, validated so it never invents numbers; template fallback."""
import json
import os
import re
import time

import requests

PROMPT = """You narrate a debt-calculator walkthrough for a YouTube Short. Write a 25-30 second
voiceover (60-80 words) for the title: "{title}".
Use ONLY these computed facts, never invent numbers:
{facts_json}
Retention matters more than completeness (viewers swipe away in the first 2 seconds):
- Sentence 1 (under 10 words) states the single most surprising number from the facts as a fact, e.g.
  "31 years. That's how long the minimum takes." No greeting, no "let's", no question-only opener.
- Then only the 2-3 numbers needed to see why. Skip every other fact.
- One short takeaway the numbers show, then the CTA: "{cta_text}".
You are NOT a person and NOT an advisor: never say "I", "my", "as an expert", "trust me", never tell the viewer
what they should do with their own money. Describe what the calculation shows ("the math shows", "this example").
No guarantees, no "you will", say "could". Plain spoken English. No emojis.
Write every number exactly as it appears in the facts (keep the $ and % signs).
Output only the script."""

NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
SMALL_OK = {str(i) for i in range(0, 13)}  # "3 cards", "1 tip", "12 months" etc.


def _numbers(text):
    return {m.replace(",", "").rstrip(".") for m in NUM_RE.findall(text)}


def invented_numbers(script, facts):
    allowed = _numbers(json.dumps(facts)) | SMALL_OK
    return sorted(n for n in _numbers(script) if n not in allowed)


def validate(script, facts):
    words = len(script.split())
    problems = []
    if not 50 <= words <= 95:
        problems.append(f"word count {words}, must be 60-80")
    bad = invented_numbers(script, facts)
    if bad:
        problems.append(f"numbers not in facts: {', '.join(bad)}")
    if re.search(r"\byou will\b|\bguarantee", script, re.I):
        problems.append("contains 'you will' or a guarantee")
    if re.search(r"\bI\b|\bI'm\b|\bmy\b|\bas an expert\b|\btrust me\b", script):
        problems.append("speaks as a person/expert (I, my, trust me)")
    return problems


# Tried in order; a busy (503/429) or retired (404) model falls through to the next.
# The flash models share one capacity pool and are often busy together; lite and gemma usually answer.
MODELS = ("gemini-3.5-flash,gemini-3.8-flash,gemini-flash-latest,gemini-3.7-flash,gemini-3-flash-preview,"
          "gemini-flash-lite-latest,gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemma-4-26b-a4b-it,gemma-4-31b-it")


def gemini(prompt, timeout=90):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    models = [m.strip() for m in (os.environ.get("GEMINI_MODELS") or MODELS).split(",") if m.strip()]
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.9}}
    errors = []
    for attempt in range(2):
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            try:
                r = requests.post(url, json=body, headers={"x-goog-api-key": key}, timeout=timeout)
            except requests.RequestException as e:
                errors.append(f"{model}:{type(e).__name__}")
                continue
            if r.status_code == 200:
                cands = r.json().get("candidates") or [{}]
                parts = cands[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
                if text:
                    return text
                errors.append(f"{model}:empty")
                continue
            errors.append(f"{model}:{r.status_code}")
            if r.status_code not in (404, 429, 500, 503):
                r.raise_for_status()
        if attempt == 0:
            time.sleep(60)  # every model busy: spikes usually pass within a minute or two
    raise RuntimeError(f"Gemini unavailable: {', '.join(errors)}")


def clean(text):
    text = re.sub(r"[*_#`\"]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def write(topic, built, cta_text):
    facts = built["facts"]
    prompt = PROMPT.format(title=topic["title"], facts_json=json.dumps(facts, indent=2), cta_text=cta_text)
    last_err = None
    for _ in range(3):
        try:
            s = clean(gemini(prompt))
        except Exception as e:  # network / key / quota -> template
            last_err = e
            break
        problems = validate(s, facts)
        if not problems:
            return s, "gemini"
        last_err = "; ".join(problems)
        prompt += f"\n\nYour previous attempt had problems: {last_err}. Fix them."
    print(f"[script] falling back to template: {last_err}")
    return fallback(topic, facts, cta_text), "template"


def fallback(topic, f, cta):
    p = topic["pillar"]
    if p == "two_friends":
        n1, n2 = f["friend_paying_minimum"], f["friend_paying_fixed"]
        body = (
            f"Same debt, two choices, and a {f['interest_difference']} difference. "
            f"{n1} and {n2} both owe {f['balance']} at {f['apr']} APR. "
            f"{n1} pays only the minimum and needs {f[n1 + '_time_to_pay_off']}, paying {f[n1 + '_total_interest']} in interest. "
            f"{n2} pays a fixed {f[n2 + '_monthly_payment']} a month and is done in {f[n2 + '_time_to_pay_off']}, "
            f"with {f[n2 + '_total_interest']} in interest. "
        )
    elif p == "min_trap":
        body = (
            f"Paying only the minimum could keep you in debt for {f['time_to_pay_off']}. "
            f"Here's the math. You owe {f['balance']} at {f['apr']} APR. "
            f"Your minimum is {f['minimum_rule']}, so the first payment is about {f['first_minimum_payment']}. "
            f"But as the balance drops, the minimum drops too, so progress slows to a crawl. "
            f"It takes {f['time_to_pay_off']} and you'd pay {f['total_interest_paid']} in interest. "
            f"That's {f['total_paid']} total for a {f['balance']} balance. "
            f"In this example, a fixed payment that does not shrink with the minimum changes the picture. "
        )
    elif p == "extra_payment":
        body = (
            f"A small extra payment could save you {f['interest_saved']}. "
            f"You owe {f['balance']} at {f['apr']} APR and pay {f['monthly_payment']} a month. "
            f"At that pace it takes {f['time_with_payment_only']} and costs {f['interest_with_payment_only']} in interest. "
            f"Now add just {f['extra_per_month']} a month. "
            f"Payoff drops to {f['time_with_extra']}, and interest drops to {f['interest_with_extra']}. "
            f"That's {f['time_saved']} sooner and {f['interest_saved']} back in your pocket. "
            f"Worth knowing: set the extra payment to autopay the day after payday, so you never see the money. "
        )
    elif p == "snowball_vs_avalanche":
        cheaper = f["cheaper_method"]
        verdict = (
            f"The avalanche saves {f['interest_difference']} in interest"
            if cheaper == "avalanche"
            else f"The snowball actually saves {f['interest_difference']}" if cheaper == "snowball"
            else "Both cost the same here"
        )
        body = (
            f"Snowball or avalanche? Let's test it on {f['total_debt']}. "
            f"The budget is {f['monthly_budget']} a month across every debt. "
            f"Snowball pays the smallest balance first, starting with {f['snowball_first_paid_off']}. "
            f"It finishes in {f['snowball_time']} with {f['snowball_interest']} in interest. "
            f"Avalanche attacks the highest rate first, starting with {f['avalanche_first_paid_off']}. "
            f"It finishes in {f['avalanche_time']} with {f['avalanche_interest']} in interest. "
            f"{verdict}. "
            f"Worth knowing: if quick wins keep you motivated, snowball could still be the better fit for you. "
        )
    elif p == "apr_gap":
        body = (
            f"Same debt, different APR, and the gap could cost you {f['interest_difference']}. "
            f"You owe {f['balance']} and pay {f['monthly_payment']} a month. "
            f"At {f['high_apr']} APR it takes {f['time_at_high_apr']} and {f['interest_at_high_apr']} in interest. "
            f"At {f['low_apr']} APR it takes {f['time_at_low_apr']} and {f['interest_at_low_apr']} in interest. "
            f"That's {f['time_difference']} longer at the higher rate. "
            f"Same balance, same payment. The only thing that changed is the rate. "
            f"Worth knowing: call your card issuer and ask for a lower rate. It's a short call, and some people get a yes. "
            f"If they say no, a lower rate card or a consolidation loan could be worth comparing. "
        )
    elif p == "balance_transfer":
        body = (
            f"Could a zero percent balance transfer really help? Let's run it on {f['balance']}. "
            f"Stay at {f['apr']} APR paying {f['monthly_payment']} a month: {f['time_if_you_stay']} and {f['interest_if_you_stay']} in interest. "
            f"Now take an offer of {f['intro_offer']}. The fee is {f['transfer_fee']}. "
            f"Interest plus fee comes to {f['interest_plus_fee_with_transfer']}, and you're done in {f['time_with_transfer']}. "
            f"That's a {f['difference']} difference. "
            f"This assumes you qualify and make no new charges on the card. "
            f"The key is to keep paying the same amount during the zero percent months, "
            f"so the promo goes to the balance and not to new spending. "
        )
    elif p == "payment_ladder":
        lines = " ".join(x + "." for x in f["payments_compared"])
        body = (
            f"How much should you pay each month on {f['balance']} at {f['apr']} APR? Here are three options. "
            f"{lines} "
            f"Going from the smallest to the biggest payment could save {f['interest_difference_slowest_vs_fastest']} in interest. "
            f"Notice how the first jump in payment saves the most time. "
            f"Worth knowing: pick the highest payment you can keep every month, even in a tight month, "
            f"and put it on autopay so it never slips. "
        )
    else:
        body = (
            f"Your credit utilization could be dragging your score down. "
            f"A {f['balance']} balance on a {f['credit_limit']} limit is {f['utilization']} utilization. "
            f"A common guideline is to stay under 30 percent, and under 10 percent is often better. "
            f"To get under 30 percent, you'd pay down {f['pay_to_get_under_30_percent']}. "
            f"To get under 10 percent, pay down {f['pay_to_get_under_10_percent']}. "
            f"Worth knowing: utilization is usually reported on your statement closing date, not your due date. "
            f"A payment made before the statement closes could show a lower balance on the report. "
        )
    # kısa tut (Shorts izlenme süresi): ilk 4 cümle + CTA
    sentences = re.split(r"(?<=[.?!])\s+", clean(body))
    return clean(" ".join(sentences[:4]) + " " + cta)
