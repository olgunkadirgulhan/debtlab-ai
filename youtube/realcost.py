#!/usr/bin/env python3
"""The Real Cost — etiket fiyatı ile faiz/zaman dahil gerçek maliyet (2026-10-14, DebtLab kanalının yeni konsepti).

Her rakam resmi kaynaktan, her çalışmada taze çekilir (çekilemezse son başarılı değer, data dosyasından):
  faizler: Federal Reserve (FRED: TERMCBCCINTNS kart APR, TERMCBAUTO48NS yeni araba 48 ay, TERMCBPER24NS kişisel
  kredi 24 ay, MORTGAGE30US / MORTGAGE15US mortgage); harcamalar: BLS Consumer Expenditure Survey (hane ortalaması).
Gerisi aritmetik (amortisman); varsayımlar açıklamada yazar.
Görsel kimlik (diğer kanallara benzemesin): kömür zemin, beyaz fiyat etiketi, turuncu faiz çubuğu, Anton + Montserrat.

  python youtube/realcost.py --dry-run [--format card|car|home|loan|spend]
"""
import csv
import json
import math
import os
import random
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
DATA = HERE / 'realcost_data.json'
PUBLISHED = HERE / 'published.csv'
OUT = HERE / 'out' / 'realcost'
W, H, FPS = 1080, 1920, 30
BG, BG2 = (20, 20, 22), (32, 30, 30)
WHITE, GREY, DIM, ORANGE, TAG = (245, 245, 240), (120, 120, 125), (170, 168, 165), (255, 106, 32), (250, 248, 240)
ANTON = str(HERE / 'assets' / 'fonts' / 'Anton-Regular.ttf')
MONT = str(HERE / 'assets' / 'fonts' / 'Montserrat.ttf')
DRY = '--dry-run' in sys.argv
FRED = {'card': 'TERMCBCCINTNS', 'car': 'TERMCBAUTO48NS', 'loan': 'TERMCBPER24NS', 'm30': 'MORTGAGE30US', 'm15': 'MORTGAGE15US', 'sav': 'SNDR', 'wage': 'CES0500000003'}
CE = {'eating out': ('CXUFOODAWAYLB0101M', '🍔'), 'groceries': ('CXUFOODHOMELB0101M', '🛒'),
      'entertainment': ('CXUENTRTAINLB0101M', '🎟️'), 'clothes': ('CXUAPPARELLB0101M', '👕'),
      'alcohol': ('CXUALCBEVGLB0101M', '🍺'), 'pets': ('CXUPETSLB0101M', '🐶'), 'personal care': ('CXUPERSCARELB0101M', '💇'),
      'health care': ('CXUHEALTHLB0101M', '🩺'), 'tobacco': ('CXUTOBACCOLB0101M', '🚬')}
DISCLAIMER = ('Educational only. Not financial advice. Payments are standard amortization math on the stated price, rate '
              'and term; taxes, fees and insurance are not included.')


def log(m): print(m, flush=True)


def money(v): return f'${v:,.0f}' if v >= 100 else f'${v:,.2f}'


def say(v):
    """Seslendirme için: büyük tutarlar yuvarlanır (ekranda tam rakam)."""
    if v >= 1e6: return f'about {v / 1e6:.1f} million dollars'
    if v >= 1e5: return f'about {round(v / 1000):,} thousand dollars'.replace(',', '')
    return money(v)


# ---------------------------------------------------------------- veri
def fred(series):
    r = requests.get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}', timeout=30)
    rows = [l.split(',') for l in r.text.strip().splitlines()[1:]]
    rows = [(d, float(v)) for d, v in rows if v not in ('', '.')]
    last = datetime.strptime(rows[-1][0], '%Y-%m-%d'); ago = [x for d, x in rows if (last - datetime.strptime(d, '%Y-%m-%d')).days >= 360]
    return {'value': rows[-1][1], 'date': rows[-1][0], 'year_ago': ago[-1] if ago else None}


def bls_ce():
    ids = [s for s, _ in CE.values()] + ['CXUTOTALEXPLB0101M']   # + toplam harcama (pay hesabı için)
    r = requests.post('https://api.bls.gov/publicAPI/v1/timeseries/data/', json={'seriesid': ids}, timeout=40).json()
    out = {}
    for s in r['Results']['series']:
        if s['data']:
            out[s['seriesID']] = {'value': float(s['data'][0]['value']), 'year': s['data'][0]['year']}
    return out


def load_data():
    old = json.loads(DATA.read_text()) if DATA.exists() else {}
    new = dict(old)
    for k, s in FRED.items():
        try: new[k] = fred(s)
        except Exception as e: log(f'  FRED {s} çekilemedi ({e}); eski değer')
    try:
        r = requests.get('https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL', timeout=30)
        rows = [l.split(',') for l in r.text.strip().splitlines()[1:]]; rows = [(d, float(x)) for d, x in rows if x not in ('', '.')]
        new['cpi_yoy'] = {'value': (rows[-1][1] / rows[-13][1] - 1) * 100, 'date': rows[-1][0]}
    except Exception as e: log(f'  CPI çekilemedi ({e}); eski değer')
    try: new['ce'] = {**old.get('ce', {}), **bls_ce()}
    except Exception as e: log(f'  BLS CE çekilemedi ({e}); eski değer')
    DATA.write_text(json.dumps(new, indent=1))
    return new


def load_cached():
    return json.loads(DATA.read_text()) if DATA.exists() else load_data()


def month_name(d):
    return datetime.strptime(d[:10], '%Y-%m-%d').strftime('%B %Y')


# ---------------------------------------------------------------- matematik
def pmt(p, apr, n):
    r = apr / 1200
    return p / n if r == 0 else p * r / (1 - (1 + r) ** -n)


def card_payoff(bal, apr, fixed=None):
    """Asgari ödeme = faiz + bakiyenin %1'i, en az $35 (yaygın formül). fixed verilirse sabit ödeme."""
    r = apr / 1200; months = 0; paid = 0.0; first = None
    while bal > 0.005 and months < 1200:
        i = bal * r
        p = fixed if fixed else max(35.0, i + bal * 0.01)
        p = min(p, bal + i); first = first or p
        bal = bal + i - p; paid += p; months += 1
    return months, paid, first


def yrs(m):
    y, mm = divmod(m, 12)
    ys, ms = f"{y} year{'s' if y != 1 else ''}", f"{mm} month{'s' if mm != 1 else ''}"
    return ys if mm == 0 else (f'{ys} {ms}' if y else ms)


# ---------------------------------------------------------------- konu
LONG_LOG = HERE / 'published_long.csv'


def done_keys():
    out = set()
    for p in (PUBLISHED, LONG_LOG):
        if p.exists():
            with p.open(encoding='utf-8') as f:
                out |= {r['topic_id'] for r in csv.DictReader(f)}
    return out


def recent_fmts(n=4):
    if not PUBLISHED.exists(): return []
    with PUBLISHED.open(encoding='utf-8') as f:
        return [r['topic_id'].split(':')[1] for r in csv.DictReader(f) if r['topic_id'].startswith('rc:')][-n:]


CARD_BAL = [1500, 2500, 3500, 5000, 6500, 8000, 10000, 12500, 15000, 20000]
CAR_P = list(range(20000, 72000, 4000))
HOME_P = list(range(225000, 900000, 25000))
LOAN_P = [3000, 5000, 7500, 10000, 15000, 20000, 25000, 30000]


def tkey(t):
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', re.sub(r'#\w+', ' ', t.lower())).split())


_KW = None


def fmt_weights():
    """2026-10-25: format seçimi kanalın kendi izlenmesine göre (≥24 saatlik Shorts'ların format medyanı / genel medyan).
    Veri yoksa hepsi 1; hiç denenmemiş format 1.5 (keşif). Sınırlar 0.3-4."""
    global _KW
    if _KW is not None: return _KW
    _KW = {}
    try:
        if not PUBLISHED.exists() or not os.environ.get('YT_REFRESH_TOKEN'): return _KW
        cut = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M')
        sh = [r for r in csv.DictReader(PUBLISHED.open(encoding='utf-8')) if r['topic_id'].startswith('rc:') and r['date_utc'] < cut and r['video_id']]
        if not sh: return _KW
        import statistics as st, upload
        api = upload._client(); views = {}
        for i in range(0, len(sh), 50):
            for it in api.videos().list(part='statistics', id=','.join(r['video_id'] for r in sh[i:i + 50])).execute().get('items', []):
                views[it['id']] = int(it['statistics'].get('viewCount', 0))
        by = {}
        for r in sh:
            if r['video_id'] in views: by.setdefault(r['topic_id'].split(':')[1], []).append(views[r['video_id']])
        allv = [v for vs in by.values() for v in vs]
        if not allv: return _KW
        m = st.median(allv)
        _KW = {k: max(0.3, min(4.0, (st.median(vs) + 10) / (m + 10))) for k, vs in by.items()}
        log('format ağırlıkları: ' + ', '.join(f'{k}={w:.2f}' for k, w in sorted(_KW.items(), key=lambda x: -x[1])))
    except Exception as e:
        log(f'format ağırlıkları alınamadı: {e}')
    return _KW


def pick(rnd, fmt=None, D=None):
    import realcost_more as RM
    done = done_keys(); last = recent_fmts()
    fmts = ['card', 'car', 'home', 'loan', 'spend', 'work', 'savings'] + RM.KURGU
    kw = fmt_weights()
    for _ in range(3000):
        pool = [x for x in fmts if x not in last[-4:]] or fmts
        f = fmt or rnd.choices(pool, weights=[kw.get(x, 1.5 if kw else 1) for x in pool])[0]
        if f in RM.KURGU:
            key = RM.key_for(f, rnd, D or load_cached())
            if key is None: continue
            tid = 'rc:' + ':'.join(str(k) for k in key)
            if tid not in done: return key, tid
            continue
        if f == 'card': key = [f, rnd.choice(CARD_BAL), rnd.choice([1.5, 2, 3, 4])]
        elif f == 'car': key = [f, rnd.choice(CAR_P), rnd.choice([60, 72, 84])]
        elif f == 'home': key = [f, rnd.choice(HOME_P)]
        elif f == 'loan': key = [f, rnd.choice(LOAN_P)]
        elif f == 'work':
            k = rnd.choice(['car', 'card', 'home', 'loan'])
            key = [f, k, rnd.choice({'car': CAR_P, 'card': CARD_BAL, 'home': HOME_P, 'loan': LOAN_P}[k])]
        elif f == 'savings': key = [f, rnd.choice([1000, 2500, 5000, 10000, 20000, 50000]), rnd.choice([1, 5, 10])]
        else: key = [f, rnd.choice(list(CE))]
        tid = 'rc:' + ':'.join(str(k) for k in key)
        if tid not in done:
            return key, tid
    raise RuntimeError('yeni konu kalmadı')


def C(rnd, *opts):
    return rnd.choice(opts)


def interest_of(kind, amt, D):
    """(faiz, açıklama, apr) — work formatı için."""
    if kind == 'car':
        apr = D['car']['value']; t = pmt(amt, apr, 60) * 60; return t - amt, 'a 60 month car loan', apr
    if kind == 'loan':
        apr = D['loan']['value']; t = pmt(amt, apr, 24) * 24; return t - amt, 'a 24 month personal loan', apr
    if kind == 'card':
        apr = D['card']['value']; _, t, _ = card_payoff(amt, apr); return t - amt, 'minimum payments on a credit card', apr
    apr = D['m30']['value']; P = amt * 0.8; t = pmt(P, apr, 360) * 360; return t - P, 'a 30 year mortgage with 20 percent down', apr


def build(key, D, rnd):
    import realcost_more as RM
    if key[0] in RM.KURGU: return RM.build(key, D, rnd)
    f = key[0]
    if f == 'card':
        bal, mult = key[1], key[2]; apr = D['card']['value']
        m1, p1, first = card_payoff(bal, apr)
        fixed = math.ceil(first * mult / 10) * 10
        m2, p2, _ = card_payoff(bal, apr, fixed)
        v = dict(subject=f'{money(bal)} CARD DEBT', tag=('BALANCE', money(bal)),
                 chips=[f'{apr:.2f}% APR', f'MIN PAY {money(first)}'],
                 meter=('MINIMUM PAYMENTS ONLY', p1),
                 bars=[(f'MINIMUM · {yrs(m1).upper()}', bal, p1 - bal, money(p1)),
                       (f'{money(fixed)}/MO · {yrs(m2).upper()}', bal, p2 - bal, money(p2))])
        beats = [C(rnd, f'{money(bal)} on a credit card. Here is what it really costs if you only pay the minimum.',
                   f'You owe {money(bal)} on a credit card. The minimum payment looks small. Watch what it really costs.',
                   f'The minimum payment on {money(bal)} of card debt is a trap. Here is the math.',
                   f'What does {money(bal)} of credit card debt really cost? Let us run it.'),
                 C(rnd, f'Average card rate: {apr:.2f} percent, per the Federal Reserve. First minimum: about {money(first)}.',
                   f'Cards that charge interest average {apr:.2f} percent, according to the Federal Reserve. Your first minimum is about {money(first)}.',
                   f'At the average rate of {apr:.2f} percent, the first minimum payment is only about {money(first)}.'),
                 C(rnd, f'Paying only the minimum takes {yrs(m1)}, and you pay {say(p1)} in total.',
                   f'Minimum only? {yrs(m1)}. Total paid: {say(p1)}.',
                   f'If you only pay the minimum, you are paying for {yrs(m1)}, and the total is {say(p1)}.'),
                 C(rnd, f'Pay a fixed {money(fixed)} a month instead and it is gone in {yrs(m2)}, for {money(p2)}. That saves {money(p1 - p2)}.',
                   f'Now pay a flat {money(fixed)} every month. Done in {yrs(m2)}, {money(p2)} total. You keep {money(p1 - p2)}.',
                   f'Same card, fixed {money(fixed)} a month: {yrs(m2)} and {money(p2)}. The difference is {money(p1 - p2)}.'),
                 C(rnd, 'How much do you pay on your card each month? Tell me below.',
                   'Minimum or fixed: which one are you doing right now? Comment below.',
                   f'Did you think it would take {yrs(m1)}? Tell me below.',
                   'What is the highest card rate you have ever seen? Comment below.')]
        title = C(rnd, f'{money(bal)} on a Credit Card, Minimum Payments Only: The Real Cost',
                  f'The Real Cost of {money(bal)} in Credit Card Debt',
                  f'{money(bal)} Card Debt: Minimum vs {money(fixed)} a Month')
        facts = [f'Balance: {money(bal)}', f'APR: {apr:.2f}% (Federal Reserve, accounts assessed interest, {month_name(D["card"]["date"])})',
                 'Minimum payment: interest + 1% of balance, at least $35 (a common card formula)',
                 f'Minimum only: {yrs(m1)}, {money(p1)} paid in total', f'Fixed {money(fixed)}/month: {yrs(m2)}, {money(p2)} paid in total',
                 'No new purchases assumed.']
        src = 'Rate: Federal Reserve G.19 via FRED'; cta = C(rnd, 'MINIMUM OR FIXED?', 'WHAT DO YOU PAY?')
    elif f == 'car':
        p, n1 = key[1], key[2]; apr = D['car']['value']; n0 = 48
        pay0 = pmt(p, apr, n0); t0 = pay0 * n0; pay1 = pmt(p, apr, n1); t1 = pay1 * n1
        v = dict(subject=f'{money(p)} CAR LOAN', tag=('STICKER PRICE', money(p)),
                 chips=[f'{apr:.2f}% APR', f'{n0} MONTHS', f'{money(pay0)}/MO'], meter=(f'REAL COST · {n0} MONTHS', t0),
                 bars=[(f'{n0} MONTHS · {money(pay0)}/MO', p, t0 - p, money(t0)), (f'{n1} MONTHS · {money(pay1)}/MO', p, t1 - p, money(t1))])
        beats = [C(rnd, f'A {money(p)} car. That is the sticker price. Here is the real cost.',
                   f'You finance a {money(p)} car. Here is what you really pay.',
                   f'The dealer says {money(p)}. The loan says something else.',
                   f'Why a {money(p)} car never costs {money(p)}.'),
                 C(rnd, f'Average new car loan rate: {apr:.2f} percent, per the Federal Reserve. Over {n0} months: {money(pay0)} a month.',
                   f'At {apr:.2f} percent, the Federal Reserve average, {n0} months means {money(pay0)} a month.',
                   f'The average rate is {apr:.2f} percent. On a {n0} month loan that is {money(pay0)} a month.'),
                 C(rnd, f'In total you pay {money(t0)}. That is {money(t0 - p)} just in interest.',
                   f'Add it up: {money(t0)}. {money(t0 - p)} of that is interest.',
                   f'Real cost: {money(t0)}, with {money(t0 - p)} going to the lender.'),
                 C(rnd, f'Stretch it to {n1} months and the payment drops to {money(pay1)}, but the total climbs to {money(t1)}. That is {money(t1 - t0)} more.',
                   f'The {n1} month deal looks cheaper at {money(pay1)} a month. Total: {money(t1)}. {money(t1 - t0)} more.',
                   f'Go {n1} months: {money(pay1)} a month, {money(t1)} total, and {money(t1 - t0)} extra interest.'),
                 C(rnd, f'Would you take {n0} or {n1} months? Tell me below.', 'What is your car payment? Comment below.',
                   f'Did the {n1} month loan surprise you? Tell me below.', 'How long was your last car loan? Comment below.')]
        title = C(rnd, f'The Real Cost of a {money(p)} Car Loan ({n0} vs {n1} Months)', f'{money(p)} Car: {n0} vs {n1} Month Loan, Real Cost',
                  f'What a {money(p)} Car Really Costs With a Loan')
        facts = [f'Price financed: {money(p)}', f'APR: {apr:.2f}% (Federal Reserve, new car loans at commercial banks, 48 months, '
                 f'{month_name(D["car"]["date"])}); the same rate is used for {n1} months for comparison',
                 f'{n0} months: {money(pay0)}/month, {money(t0)} total', f'{n1} months: {money(pay1)}/month, {money(t1)} total']
        src = 'Rate: Federal Reserve G.19 via FRED'; cta = f'{n0} OR {n1} MONTHS?'
    elif f == 'loan':
        p = key[1]; apr = D['loan']['value']; n0 = 24; pay0 = pmt(p, apr, n0); t0 = pay0 * n0
        capr = D['card']['value']; pc = pmt(p, capr, n0); tc = pc * n0
        v = dict(subject=f'{money(p)} LOAN', tag=('YOU BORROW', money(p)),
                 chips=[f'{apr:.2f}% APR', f'{n0} MONTHS', f'{money(pay0)}/MO'], meter=('REAL COST', t0),
                 bars=[(f'PERSONAL LOAN · {apr:.1f}%', p, t0 - p, money(t0)), (f'CREDIT CARD · {capr:.1f}%', p, tc - p, money(tc))])
        beats = [C(rnd, f'You borrow {money(p)}. Here is what it really costs.', f'{money(p)} borrowed for two years. Here is the real cost.',
                   f'Loan or credit card for {money(p)}? Here is the difference.', f'Borrowing {money(p)} is never just {money(p)}.'),
                 C(rnd, f'Average two year personal loan rate: {apr:.2f} percent, per the Federal Reserve. That is {money(pay0)} a month.',
                   f'Personal loans average {apr:.2f} percent, according to the Federal Reserve. {money(pay0)} a month for two years.'),
                 C(rnd, f'You pay back {money(t0)} in total, so {money(t0 - p)} is interest.', f'Total: {money(t0)}. Interest: {money(t0 - p)}.'),
                 C(rnd, f'Put the same {money(p)} on a credit card at {capr:.2f} percent and pay it off in 24 months, and it costs {money(tc)}. That is {money(tc - t0)} more.',
                   f'On a card at {capr:.2f} percent, the same two year payoff costs {money(tc)}, or {money(tc - t0)} more.'),
                 C(rnd, 'Have you ever used a loan to pay off a card? Tell me below.', 'Loan or card: which would you use? Comment below.',
                   'What rate did your last loan have? Tell me below.')]
        title = C(rnd, f'The Real Cost of Borrowing {money(p)}: Personal Loan vs Credit Card', f'{money(p)}: Personal Loan or Credit Card?')
        facts = [f'Amount: {money(p)}, 24 months',
                 f'Personal loan APR: {apr:.2f}% (Federal Reserve, 24-month personal loans at commercial banks, {month_name(D["loan"]["date"])})',
                 f'Credit card APR: {capr:.2f}% (Federal Reserve, accounts assessed interest, {month_name(D["card"]["date"])})',
                 f'Loan: {money(pay0)}/month, {money(t0)} total', f'Card paid off in 24 months: {money(pc)}/month, {money(tc)} total']
        src = 'Rates: Federal Reserve G.19 via FRED'; cta = 'LOAN OR CARD?'
    elif f == 'home':
        price = key[1]; down = price * 0.2; P = price - down
        a30, a15 = D['m30']['value'], D['m15']['value']
        p30, p15 = pmt(P, a30, 360), pmt(P, a15, 180); t30, t15 = down + p30 * 360, down + p15 * 180
        v = dict(subject=f'{money(price)} HOUSE', tag=('LIST PRICE', money(price)),
                 chips=['20% DOWN', f'{a30:.2f}% · 30 YR', f'{money(p30)}/MO'], meter=('REAL COST · 30 YEARS', t30),
                 bars=[(f'30 YEARS · {money(p30)}/MO', price, t30 - price, money(t30)), (f'15 YEARS · {money(p15)}/MO', price, t15 - price, money(t15))])
        beats = [C(rnd, f'A {money(price)} house. Here is what it really costs with a mortgage.', f'The house is listed at {money(price)}. That is not what you pay.',
                   f'What does a {money(price)} home really cost? Let us do the math.', f'{money(price)} on the listing. Now add the mortgage.'),
                 C(rnd, f'20 percent down, 30 years at {a30:.2f} percent, the Freddie Mac average. That is {money(p30)} a month.',
                   f'Put 20 percent down. At {a30:.2f} percent for 30 years, the Freddie Mac average, you pay {money(p30)} a month.'),
                 C(rnd, f'Over 30 years you pay {say(t30)}, before taxes and insurance.', f'Thirty years later the total is {say(t30)}. Taxes and insurance not included.'),
                 C(rnd, f'A 15 year loan at {a15:.2f} percent is {money(p15)} a month, but {say(t15)} in total. You save {say(t30 - t15)}.',
                   f'Take 15 years at {a15:.2f} percent instead: {money(p15)} a month, {say(t15)} total. That is {say(t30 - t15)} less.'),
                 C(rnd, '15 or 30 years: which would you pick? Tell me below.', 'What is your mortgage rate? Comment below.',
                   'Would you rent or buy at these rates? Tell me below.')]
        title = C(rnd, f'The Real Cost of a {money(price)} House (30 vs 15 Year Mortgage)', f'{money(price)} House: What You Really Pay Over 30 Years',
                  f'What a {money(price)} Home Really Costs at Today\'s Rates')
        facts = [f'Price: {money(price)}, 20% down ({money(down)}), loan {money(P)}',
                 f'30-year rate: {a30:.2f}%, 15-year rate: {a15:.2f}% (Freddie Mac PMMS via FRED, week of {D["m30"]["date"]})',
                 f'30 years: {money(p30)}/month, {money(t30)} total incl. down payment', f'15 years: {money(p15)}/month, {money(t15)} total',
                 'Principal and interest only: property tax, insurance and HOA not included.']
        src = 'Rates: Freddie Mac PMMS via FRED'; cta = '15 OR 30 YEARS?'
    elif f == 'work':
        kind, amt = key[1], key[2]; wage = D['wage']['value']
        I, what, apr = interest_of(kind, amt, D); hp, hi = amt / wage, I / wage
        noun = {'car': f'{money(amt)} CAR', 'card': f'{money(amt)} CARD DEBT', 'home': f'{money(amt)} HOUSE', 'loan': f'{money(amt)} LOAN'}[kind]
        v = dict(subject=noun, tag=('INTEREST ALONE', money(I)), chips=[f'{apr:.2f}% APR', f'AVG PAY {money(wage)}/HR'],
                 meter=('HOURS OF WORK FOR THE INTEREST', hi, 'hrs'),
                 bars=[('THE PRICE IN HOURS', hp, 0, f'{hp:,.0f} HRS'), ('THE INTEREST IN HOURS', 0, hi, f'{hi:,.0f} HRS')])
        weeks = hi / 40
        beats = [C(rnd, f'How many hours do you work just to pay the interest on a {noun.lower()}?',
                   f'Interest is not just money. It is your time. Here is a {noun.lower()} in hours.',
                   f'Let us turn the interest on a {noun.lower()} into hours of your life.'),
                 C(rnd, f'With {what} at {apr:.2f} percent, the interest alone is {say(I)}.',
                   f'{what.capitalize()} at {apr:.2f} percent adds {say(I)} in interest.'),
                 C(rnd, f'The average American earns {money(wage)} an hour before taxes, per the Bureau of Labor Statistics. That is {hi:,.0f} hours of work.',
                   f'At the average pay of {money(wage)} an hour, that interest takes {hi:,.0f} hours to earn, before taxes.'),
                 (C(rnd, f'That is about {weeks:,.0f} full work weeks, just for the interest.', f'In 40 hour weeks, that is {weeks:,.0f} weeks of work.')
                  if weeks < 104 else C(rnd, f'That is about {hi / 2080:,.1f} years of full time work, just for the interest.',
                                        f'Full time, that is {hi / 2080:,.1f} years of work for the interest alone.')),
                 C(rnd, 'Was it worth the hours? Tell me below.', 'How many hours a week would you give up for this? Comment below.',
                   'Does thinking in hours change your mind? Tell me below.')]
        title = C(rnd, f'The Interest on a {noun.title()} in Hours of Work', f'How Many Hours You Work to Pay the Interest on a {noun.title()}')
        facts = [f'{noun.title()}: {what} at {apr:.2f}% APR = {money(I)} interest',
                 f'Average hourly earnings, all private employees: {money(wage)} (BLS via FRED, {month_name(D["wage"]["date"])}), before taxes',
                 f'Interest = {hi:,.0f} hours = {weeks:,.0f} forty-hour weeks ({hi / 2080:,.1f} years at 2,080 hours/year)']
        src = 'Rates: Fed / Freddie Mac · Pay: BLS, via FRED'; cta = 'WORTH THE HOURS?'
    elif f == 'savings':
        amt, y = key[1], key[2]; sr, inf = D['sav']['value'], D['cpi_yoy']['value']
        nom = amt * (1 + sr / 100) ** y; real = nom / (1 + inf / 100) ** y; lost = amt - real
        v = dict(subject=f'{money(amt)} IN SAVINGS', tag=('TODAY', money(amt)), chips=[f'{sr:.2f}% SAVINGS', f'{inf:.1f}% INFLATION'],
                 meter=(f'BUYING POWER IN {y} YEAR{"S" if y > 1 else ""}', real),
                 bars=[('ACCOUNT BALANCE', nom, 0, money(nom)), ('WHAT IT BUYS', real, 0, money(real))])
        beats = [C(rnd, f'{money(amt)} sitting in a savings account. Here is what it is really worth in {y} year{"s" if y > 1 else ""}.',
                   f'Your {money(amt)} in savings is shrinking. Here is how fast.', f'Does {money(amt)} in a savings account keep its value? Let us check.'),
                 C(rnd, f'The national average savings rate is {sr:.2f} percent, per the FDIC. Inflation over the last year was {inf:.1f} percent.',
                   f'Average savings rate: {sr:.2f} percent, from the FDIC. Prices rose {inf:.1f} percent in the last year.'),
                 C(rnd, f'If both stay the same, in {y} year{"s" if y > 1 else ""} your balance is {money(nom)}, but it only buys what {money(real)} buys today.',
                   f'After {y} year{"s" if y > 1 else ""}: {money(nom)} on the statement, {money(real)} in buying power.'),
                 C(rnd, f'That is {money(lost)} of buying power gone, without spending a cent.', f'You lost {money(lost)} of value just by waiting.'),
                 C(rnd, 'What rate does your savings account pay? Tell me below.', 'Did you know your bank rate? Comment below.')]
        title = C(rnd, f'{money(amt)} in Savings: What It Is Really Worth in {y} Year{"s" if y > 1 else ""}', f'The Real Cost of Keeping {money(amt)} in Savings')
        facts = [f'Starting amount: {money(amt)}', f'Savings rate: {sr:.2f}% (FDIC national rate, savings deposits, via FRED, {month_name(D["sav"]["date"])})',
                 f'Inflation: {inf:.1f}% (CPI-U, 12 months to {month_name(D["cpi_yoy"]["date"])}, BLS via FRED)',
                 f'Assumes both rates stay the same for {y} year(s). Rates vary by bank and over time.',
                 f'Balance after {y} year(s): {money(nom)} · buying power in today\'s dollars: {money(real)}']
        src = 'Data: FDIC and BLS via FRED'; cta = 'WHAT IS YOUR RATE?'
    else:
        cat = key[1]; sid, emo = CE[cat]; c = D['ce'][sid]; a = c['value']
        v = dict(subject=cat.upper(), tag=('PER YEAR', money(a)),
                 chips=[f'{money(a / 365)}/DAY', f'{money(a / 12)}/MONTH'], meter=('IN 10 YEARS', a * 10),
                 bars=[('10 YEARS', a * 10, 0, money(a * 10)), ('30 YEARS', a * 30, 0, money(a * 30))])
        beats = [C(rnd, f'The average American household spends {money(a)} a year on {cat}.',
                   f'How much does {cat} really cost? The average household spends {money(a)} a year.',
                   f'{cat.capitalize()} costs the average household {money(a)} every year.'),
                 C(rnd, f'That is {money(a / 365)} a day, or {money(a / 12)} a month, per the Bureau of Labor Statistics.',
                   f'Per day: {money(a / 365)}. Per month: {money(a / 12)}. Source: the Bureau of Labor Statistics.'),
                 C(rnd, f'Over 10 years that adds up to {money(a * 10)}, even if prices never went up.', f'Ten years: {money(a * 10)}, at today\'s prices.'),
                 C(rnd, f'Over 30 years it is {money(a * 30)}.', f'Thirty years: {money(a * 30)}.'),
                 C(rnd, f'Do you spend more or less than {money(a / 12)} a month on {cat}? Tell me below.', f'Is your {cat} bill above or below average? Comment below.')]
        title = C(rnd, f'The Real Cost of {cat.title()}: {money(a)} a Year {emo}', f'What {cat.title()} Really Costs Over 30 Years {emo}')
        facts = [f'Average annual spending per U.S. household (consumer unit) on {cat}: {money(a)} ({c["year"]})',
                 f'Per day: {money(a / 365)}, per month: {money(a / 12)}', f'10 years: {money(a * 10)}, 30 years: {money(a * 30)} (today\'s prices, no inflation)']
        src = f'Data: BLS Consumer Expenditure Survey ({c["year"]})'; cta = 'MORE OR LESS?'
    v.update(fmt=f, key=key, beats=beats, title=title[:95], src=src, cta=cta)
    v['desc'] = (title + '\n\n' + '\n'.join(facts) + '\n\nRun your own numbers: https://debtlabai.com\n\n'
                 + src + '\n' + DISCLAIMER + '\n\n#Shorts #realcost #personalfinance #money')
    v['tags'] = ['the real cost', 'real cost', 'personal finance', 'money', f, 'shorts']
    return v


# ---------------------------------------------------------------- çizim
_FC = {}


def font(path, sz, bold=True):
    k = (path, sz, bold)
    if k not in _FC:
        f = ImageFont.truetype(path, sz)
        if path == MONT:
            try: f.set_variation_by_name('Bold' if bold else 'Medium')
            except Exception: pass
        _FC[k] = f
    return _FC[k]


def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def background():
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    for y in range(0, H, 4):
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * y / H) for a, b in zip(BG, BG2)))
    d.text((W // 2, 150), 'T H E   R E A L   C O S T', font=font(MONT, 40), fill=ORANGE, anchor='mm')
    return img


def wrap(d, text, f, maxw):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) > maxw and cur: lines.append(cur); cur = w
        else: cur = t
    return lines + [cur] if cur else lines


def price_tag(text_top, text_val, swing):
    w, h = 620, 300
    t = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(t)
    d.polygon([(20, 20 + h // 2), (110, 20), (w + 20, 20), (w + 20, h + 20), (110, h + 20)], fill=TAG)
    d.ellipse([70, 20 + h // 2 - 18, 106, 20 + h // 2 + 18], fill=BG)
    d.text((w // 2 + 70, 95), text_top, font=font(MONT, 38), fill=GREY, anchor='mm')
    d.text((w // 2 + 70, 205), text_val, font=font(ANTON, 130), fill=BG, anchor='mm')
    return t.rotate(swing, expand=True, resample=Image.BICUBIC)


def frame(base, v, bi, t, beat_txt):
    img = base.copy(); d = ImageDraw.Draw(img)
    d.text((W // 2, 260), v['subject'], font=font(ANTON, 110 if len(v['subject']) < 16 else 88), fill=WHITE, anchor='mm')
    a = ease(t / 0.5) if bi == 0 else 1.0
    tag = price_tag(*v['tag'], swing=6 * math.sin(t * 2.2) * math.exp(-t * 0.8) if bi == 0 else 0)
    img.paste(tag, (W // 2 - tag.width // 2, int(360 - (1 - a) * 400)), tag)
    if bi >= 1:                                                      # çipler
        f = font(MONT, 40); ws = [d.textlength(c, font=f) + 56 for c in v['chips']]
        x = (W - sum(ws) - 20 * (len(ws) - 1)) / 2
        for i, (c, w) in enumerate(zip(v['chips'], ws)):
            if bi == 1 and t < 0.25 * i: break
            d.rounded_rectangle([x, 720, x + w, 800], radius=40, outline=DIM, width=3)
            d.text((x + w / 2, 760), c, font=f, fill=WHITE, anchor='mm'); x += w + 20
    if bi >= 2:                                                      # sayaç
        k = ease(t / 1.6) if bi == 2 else 1.0
        d.text((W // 2, 880), v['meter'][0], font=font(MONT, 40), fill=DIM, anchor='mm')
        d.text((W // 2, 1000), (f"{v['meter'][1] * k:,.0f} HRS" if len(v['meter']) > 2 else money(v['meter'][1] * k)), font=font(ANTON, 170), fill=ORANGE, anchor='mm')
    mx = max(b[1] + b[2] for b in v['bars'])
    for i, (lab, base_v, extra, right) in enumerate(v['bars']):      # çubuklar
        if bi < 2 + i: continue
        k = ease(t / 1.2) if bi == 2 + i else 1.0
        y = 1150 + i * 190; full = 920
        d.text((80, y), lab, font=font(MONT, 36), fill=WHITE)
        d.text((W - 80, y), right, font=font(ANTON, 52), fill=WHITE, anchor='ra')
        wb, we = full * base_v / mx * k, full * extra / mx * k
        if wb > 2: d.rounded_rectangle([80, y + 66, 80 + wb, y + 130], radius=10, fill=GREY)
        if we > 2: d.rounded_rectangle([80 + max(0, wb - 10), y + 66, 80 + wb + we, y + 130], radius=10, fill=ORANGE)
    if any(b[2] > 0 for b in v['bars']) and v['fmt'] != 'savings' and bi >= 2:                  # lejant
        d.rectangle([80, 1540, 110, 1570], fill=GREY); d.text((125, 1555), 'PRICE', font=font(MONT, 30), fill=DIM, anchor='lm')
        d.rectangle([300, 1540, 330, 1570], fill=ORANGE); d.text((345, 1555), 'INTEREST', font=font(MONT, 30), fill=DIM, anchor='lm')
    if bi == 4:
        d.rounded_rectangle([140, 1620, 940, 1750], radius=65, fill=ORANGE)
        d.text((W // 2, 1685), v['cta'], font=font(ANTON, 76), fill=BG, anchor='mm')
    else:                                                            # altyazı
        f = font(MONT, 40); ls = wrap(d, beat_txt, f, 940)[:4]
        for j, l in enumerate(ls):
            d.text((W // 2, 1625 + j * 52), l, font=f, fill=WHITE, anchor='mm')
    d.text((W // 2, 1850), v['src'], font=font(MONT, 28, bold=False), fill=GREY, anchor='mm')
    return img


# ---------------------------------------------------------------- ses + video
def render(v, mp4):
    os.environ.setdefault('TTS_SPEED', '1.15')
    import tts
    tmp = mp4.with_suffix(''); tmp.mkdir(parents=True, exist_ok=True)
    parts, durs, sr = [], [], 24000
    for i, b in enumerate(v['beats']):
        wav = tmp / f'b{i}.wav'; tts.synthesize(b, str(wav))
        a, sr = sf.read(str(wav), dtype='float32')
        a = np.concatenate([a, np.zeros(int(0.25 * sr), dtype=np.float32)])
        parts.append(a); durs.append(len(a) / sr)
    sf.write(str(tmp / 'voice.wav'), np.concatenate(parts), sr)
    base = background()
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-i', str(tmp / 'voice.wav'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                          '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(mp4)],
                         stdin=subprocess.PIPE)
    for i, dd in enumerate(durs):
        for k in range(int(dd * FPS)):
            p.stdin.write(frame(base, v, i, k / FPS, v['beats'][i]).tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError('ffmpeg hata')
    return mp4


def record(tid, vid, privacy, title, fmt):
    new = not PUBLISHED.exists()
    with PUBLISHED.open('a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['topic_id', 'date_utc', 'video_id', 'privacy', 'pillar', 'title', 'script_source'])
        if new: w.writeheader()
        w.writerow(dict(topic_id=tid, date_utc=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'), video_id=vid,
                        privacy=privacy, pillar=f'real_cost_{fmt}', title=title, script_source='realcost'))


def main():
    a = sys.argv[1:]
    fmt = a[a.index('--format') + 1] if '--format' in a else None
    n = int(a[a.index('--videos') + 1]) if '--videos' in a else 1
    privacy = os.environ.get('YT_PRIVACY', 'private')
    if not DRY:
        import upload
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        cnt = sum(1 for r in csv.DictReader(PUBLISHED.open(encoding='utf-8')) if r['date_utc'].startswith(today)) if PUBLISHED.exists() else 0
        if cnt >= int(os.environ.get('MAX_PER_DAY') or 1):
            log(f'günlük sınır dolu ({cnt})'); return
        log(f'kanal: {upload.check_channel()}')
    D = load_data(); rnd = random.Random()
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        # 2026-10-25: aynı başlık iki kez yüklenmez (tekrar eden başlıkları YouTube dağıtmıyor)
        seen = {tkey(r['title']) for r in csv.DictReader(PUBLISHED.open(encoding='utf-8'))} if PUBLISHED.exists() else set()
        for _ in range(25):
            key, tid = pick(rnd, fmt, D); v = build(key, D, rnd)
            if tkey(v['title']) not in seen: break
        else:
            raise SystemExit('25 denemede yeni başlık bulunamadı')
        log(f'[realcost] {tid} → {v["title"]}')
        import realcost_more as RM
        mp4 = (RM.render if 'scenes' in v else render)(v, OUT / f'{datetime.now(timezone.utc):%Y-%m-%d}_{i}.mp4')
        if DRY:
            log(f'  [dry-run] {mp4}\n{v["desc"]}'); continue
        vid = upload.upload(mp4, v['title'] + ' #Shorts', v['desc'], v['tags'], privacy)
        record(tid, vid, privacy, v['title'], v['fmt'])
        log(f'  ✓ https://youtu.be/{vid}')


if __name__ == '__main__':
    main()
