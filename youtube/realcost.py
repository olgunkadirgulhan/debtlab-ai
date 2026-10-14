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
import subprocess
import sys
from datetime import datetime, timezone
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
FRED = {'card': 'TERMCBCCINTNS', 'car': 'TERMCBAUTO48NS', 'loan': 'TERMCBPER24NS', 'm30': 'MORTGAGE30US', 'm15': 'MORTGAGE15US'}
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
    return {'value': rows[-1][1], 'date': rows[-1][0]}


def bls_ce():
    ids = [s for s, _ in CE.values()]
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
    try: new['ce'] = {**old.get('ce', {}), **bls_ce()}
    except Exception as e: log(f'  BLS CE çekilemedi ({e}); eski değer')
    DATA.write_text(json.dumps(new, indent=1))
    return new


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
def done_keys():
    if not PUBLISHED.exists(): return set()
    with PUBLISHED.open(encoding='utf-8') as f:
        return {r['topic_id'] for r in csv.DictReader(f)}


def pick(rnd, fmt=None):
    done = done_keys()
    last = []
    if PUBLISHED.exists():
        with PUBLISHED.open(encoding='utf-8') as f:
            last = [r['topic_id'].split(':')[1] for r in csv.DictReader(f) if r['topic_id'].startswith('rc:')][-3:]
    fmts = ['card', 'card', 'car', 'home', 'loan', 'spend', 'spend']
    for _ in range(500):
        f = fmt or rnd.choice([x for x in fmts if x not in last[-1:]] or fmts)
        if f == 'card': key = [f, rnd.choice([1500, 2500, 3000, 4000, 5000, 6500, 8000, 10000, 12000, 15000]), rnd.choice([1.5, 2, 3])]
        elif f == 'car': key = [f, rnd.choice(range(22000, 58000, 3000)), rnd.choice([60, 72, 84])]
        elif f == 'home': key = [f, rnd.choice(range(250000, 650000, 25000))]
        elif f == 'loan': key = [f, rnd.choice([3000, 5000, 7500, 10000, 12000, 15000, 20000])]
        else: key = [f, rnd.choice(list(CE))]
        tid = 'rc:' + ':'.join(str(k) for k in key)
        if tid not in done:
            return key, tid
    raise RuntimeError('yeni konu kalmadı')


def build(key, D, rnd):
    f = key[0]
    src_rate = lambda k: f"{D[k]['value']:.2f}%"
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
        hook = rnd.choice([f'{money(bal)} on a credit card. Here is what it really costs if you only pay the minimum.',
                           f'You owe {money(bal)} on a credit card. The minimum payment looks small. Watch what it really costs.'])
        beats = [hook,
                 f'Average card rate: {apr:.2f} percent, per the Federal Reserve. First minimum: about {money(first)}.',
                 f'Paying only the minimum takes {yrs(m1)}, and you pay {say(p1)} in total.',
                 f'Pay a fixed {money(fixed)} a month instead and it is gone in {yrs(m2)}, for {money(p2)}. '
                 f'That saves {money(p1 - p2)}.',
                 rnd.choice(['How much do you pay on your card each month? Tell me below.',
                             'Minimum or fixed: which one are you doing right now? Comment below.'])]
        title = rnd.choice([f'{money(bal)} on a Credit Card, Minimum Payments Only: The Real Cost',
                            f'The Real Cost of {money(bal)} in Credit Card Debt'])
        facts = [f'Balance: {money(bal)}', f'APR: {apr:.2f}% (Federal Reserve, accounts assessed interest, {month_name(D["card"]["date"])})',
                 f'Minimum payment: interest + 1% of balance, at least $35 (a common card formula)',
                 f'Minimum only: {yrs(m1)}, {money(p1)} paid in total', f'Fixed {money(fixed)}/month: {yrs(m2)}, {money(p2)} paid in total',
                 'No new purchases assumed.']
        src = 'Rate: Federal Reserve G.19 via FRED'
        cta = 'MINIMUM OR FIXED?'
    elif f in ('car', 'loan'):
        p = key[1]; apr = D[f]['value']; n0 = 48 if f == 'car' else 24
        n1 = key[2] if f == 'car' else n0
        pay0 = pmt(p, apr, n0); t0 = pay0 * n0
        if f == 'car':
            pay1 = pmt(p, apr, n1); t1 = pay1 * n1
            v = dict(subject=f'{money(p)} CAR LOAN', tag=('STICKER PRICE', money(p)),
                     chips=[f'{apr:.2f}% APR', f'{n0} MONTHS', f'{money(pay0)}/MO'], meter=(f'REAL COST · {n0} MONTHS', t0),
                     bars=[(f'{n0} MONTHS · {money(pay0)}/MO', p, t0 - p, money(t0)), (f'{n1} MONTHS · {money(pay1)}/MO', p, t1 - p, money(t1))])
            beats = [rnd.choice([f'A {money(p)} car. That is the sticker price. Here is the real cost.',
                                 f'You finance a {money(p)} car. Here is what you really pay.']),
                     f'Average new car loan rate: {apr:.2f} percent, per the Federal Reserve. Over {n0} months: {money(pay0)} a month.',
                     f'In total you pay {money(t0)}. That is {money(t0 - p)} just in interest.',
                     f'Stretch it to {n1} months and the payment drops to {money(pay1)}, but the total climbs to {money(t1)}. '
                     f'That is {money(t1 - t0)} more.',
                     f'Would you take {n0} or {n1} months? Tell me below.']
            title = rnd.choice([f'The Real Cost of a {money(p)} Car Loan ({n0} vs {n1} Months)',
                                f'{money(p)} Car: {n0} vs {n1} Month Loan, Real Cost'])
            facts = [f'Price financed: {money(p)}', f'APR: {apr:.2f}% (Federal Reserve, new car loans at commercial banks, 48 months, '
                     f'{month_name(D["car"]["date"])}); the same rate is used for {n1} months for comparison',
                     f'{n0} months: {money(pay0)}/month, {money(t0)} total', f'{n1} months: {money(pay1)}/month, {money(t1)} total']
            src = 'Rate: Federal Reserve G.19 via FRED'; cta = f'{n0} OR {n1} MONTHS?'
        else:
            capr = D['card']['value']; pc = pmt(p, capr, n0); tc = pc * n0
            v = dict(subject=f'{money(p)} LOAN', tag=('YOU BORROW', money(p)),
                     chips=[f'{apr:.2f}% APR', f'{n0} MONTHS', f'{money(pay0)}/MO'], meter=('REAL COST', t0),
                     bars=[(f'PERSONAL LOAN · {apr:.1f}%', p, t0 - p, money(t0)), (f'CREDIT CARD · {capr:.1f}%', p, tc - p, money(tc))])
            beats = [rnd.choice([f'You borrow {money(p)}. Here is what it really costs.',
                                 f'{money(p)} borrowed for two years. Here is the real cost.']),
                     f'Average two year personal loan rate: {apr:.2f} percent, per the Federal Reserve. That is {money(pay0)} a month.',
                     f'You pay back {money(t0)} in total, so {money(t0 - p)} is interest.',
                     f'Put the same {money(p)} on a credit card at {capr:.2f} percent and pay it off in 24 months, and it costs '
                     f'{money(tc)}. That is {money(tc - t0)} more.',
                     'Have you ever used a loan to pay off a card? Tell me below.']
            title = f'The Real Cost of Borrowing {money(p)}: Personal Loan vs Credit Card'
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
        beats = [rnd.choice([f'A {money(price)} house. Here is what it really costs with a mortgage.',
                             f'The house is listed at {money(price)}. That is not what you pay.']),
                 f'20 percent down, 30 years at {a30:.2f} percent, the Freddie Mac average. That is {money(p30)} a month.',
                 f'Over 30 years you pay {say(t30)}, before taxes and insurance.',
                 f'A 15 year loan at {a15:.2f} percent is {money(p15)} a month, but {say(t15)} in total. You save {say(t30 - t15)}.',
                 '15 or 30 years: which would you pick? Tell me below.']
        title = rnd.choice([f'The Real Cost of a {money(price)} House (30 vs 15 Year Mortgage)',
                            f'{money(price)} House: What You Really Pay Over 30 Years'])
        facts = [f'Price: {money(price)}, 20% down ({money(down)}), loan {money(P)}',
                 f'30-year rate: {a30:.2f}%, 15-year rate: {a15:.2f}% (Freddie Mac PMMS via FRED, week of {D["m30"]["date"]})',
                 f'30 years: {money(p30)}/month, {money(t30)} total incl. down payment', f'15 years: {money(p15)}/month, {money(t15)} total',
                 'Principal and interest only: property tax, insurance and HOA not included.']
        src = 'Rates: Freddie Mac PMMS via FRED'; cta = '15 OR 30 YEARS?'
    else:
        cat = key[1]; sid, emo = CE[cat]; c = D['ce'][sid]; a = c['value']
        v = dict(subject=cat.upper(), tag=('PER YEAR', money(a)),
                 chips=[f'{money(a / 365)}/DAY', f'{money(a / 12)}/MONTH'], meter=('IN 10 YEARS', a * 10),
                 bars=[('10 YEARS', a * 10, 0, money(a * 10)), ('30 YEARS', a * 30, 0, money(a * 30))])
        beats = [rnd.choice([f'The average American household spends {money(a)} a year on {cat}.',
                             f'How much does {cat} really cost? The average household spends {money(a)} a year.']),
                 f'That is {money(a / 365)} a day, or {money(a / 12)} a month, per the Bureau of Labor Statistics.',
                 f'Over 10 years that adds up to {money(a * 10)}, even if prices never went up.',
                 f'Over 30 years it is {money(a * 30)}.',
                 f'Do you spend more or less than {money(a / 12)} a month on {cat}? Tell me below.']
        title = f'The Real Cost of {cat.title()}: {money(a)} a Year {emo}'
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
        d.text((W // 2, 1000), money(v['meter'][1] * k), font=font(ANTON, 170), fill=ORANGE, anchor='mm')
    mx = max(b[1] + b[2] for b in v['bars'])
    for i, (lab, base_v, extra, right) in enumerate(v['bars']):      # çubuklar
        if bi < 2 + i: continue
        k = ease(t / 1.2) if bi == 2 + i else 1.0
        y = 1150 + i * 190; full = 920
        d.text((80, y), lab, font=font(MONT, 36), fill=WHITE)
        d.text((W - 80, y), right, font=font(ANTON, 52), fill=WHITE, anchor='ra')
        wb, we = full * base_v / mx * k, full * extra / mx * k
        d.rounded_rectangle([80, y + 66, 80 + max(wb, 2), y + 130], radius=10, fill=GREY)
        if we > 2: d.rounded_rectangle([80 + wb - 10, y + 66, 80 + wb + we, y + 130], radius=10, fill=ORANGE)
    if any(b[2] > 0 for b in v['bars']) and bi >= 2:                  # lejant
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
        key, tid = pick(rnd, fmt); v = build(key, D, rnd)
        log(f'[realcost] {tid} → {v["title"]}')
        mp4 = render(v, OUT / f'{datetime.now(timezone.utc):%Y-%m-%d}_{i}.mp4')
        if DRY:
            log(f'  [dry-run] {mp4}\n{v["desc"]}'); continue
        vid = upload.upload(mp4, v['title'] + ' #Shorts', v['desc'], v['tags'], privacy)
        record(tid, vid, privacy, v['title'], v['fmt'])
        log(f'  ✓ https://youtu.be/{vid}')


if __name__ == '__main__':
    main()
