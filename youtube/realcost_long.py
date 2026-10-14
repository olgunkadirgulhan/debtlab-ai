#!/usr/bin/env python3
"""The Real Cost — uzun video (16:9, 3-5 dk): "bir şeyi ödemenin bütün yolları" (2026-10-14).

Konu türleri: car_all (peşin, 36…84 ay), card_all (asgari, sabit ödemeler, kredi ile kapatma), home_all (peşinat %5/10/20,
15/30 yıl), loan_all (kişisel kredi vs kart vs asgari), household (BLS harcama kalemlerinin hepsi).
Rakamlar realcost.py ile aynı resmi kaynaklardan; Short'larla aynı konu kimliği kullanılmaz (published_long.csv).

  python youtube/realcost_long.py --dry-run [--kind car_all]
"""
import csv
import re
import os
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import realcost as R  # noqa: E402
from realcost import C, money, say, pmt, card_payoff, yrs, month_name  # noqa: E402

W, H, FPS = 1920, 1080, 30
DRY = '--dry-run' in sys.argv
LONG_LOG = R.LONG_LOG
F = R.font


def pick(rnd, kind=None):
    done = R.done_keys()
    for _ in range(500):
        k = kind or rnd.choice(['car_all', 'card_all', 'home_all', 'loan_all', 'car_all', 'card_all', 'home_all', 'household'])
        amt = {'car_all': R.CAR_P, 'card_all': R.CARD_BAL, 'home_all': R.HOME_P, 'loan_all': R.LOAN_P, 'household': [0]}[k]
        key = [k, rnd.choice(amt)]
        tid = 'rcl:' + ':'.join(str(x) for x in key)
        if tid not in done:
            return key, tid
    raise RuntimeError('yeni uzun konu kalmadı')


def build(key, D, rnd):
    k, amt = key; wage = D['wage']['value']; rows = []
    hrs = lambda i: f'That interest alone is about {i / wage:,.0f} hours of work at the average wage.'
    if k == 'car_all':
        apr = D['car']['value']; subject = f'{money(amt)} CAR'
        rows.append(dict(label='PAY CASH', price=amt, extra=0, sub='no interest', n=0,
                         say=C(rnd, f'Option one: pay cash. {money(amt)}, and not a cent more.', f'Start with cash. The car costs exactly {money(amt)}.')))
        for n in (36, 48, 60, 72, 84):
            p = pmt(amt, apr, n); t = p * n
            rows.append(dict(label=f'{n} MONTHS', price=amt, extra=t - amt, sub=f'{money(p)}/mo', n=n, first_int=amt * apr / 1200,
                             say=C(rnd, f'{n} months: {money(p)} a month, {money(t)} in total. ', f'Now {n} months. The payment is {money(p)}, and the total is {money(t)}. ',
                                   f'At {n} months you pay {money(p)} a month. Add it up and it is {money(t)}. ') + hrs(t - amt)))
        intro = C(rnd, f'A {money(amt)} car can cost you very different amounts depending on how you pay. Let us go through every option, from cash to an 84 month loan.',
                  f'Same car, same {money(amt)} price, six ways to pay for it. Some of them cost thousands more. Here is every option.')
        context = f'We use the Federal Reserve average new car loan rate, {apr:.2f} percent, for every term so the comparison is fair.' + (f' A year ago, new car loans averaged {D["car"]["year_ago"]:.2f} percent.' if D["car"].get("year_ago") else '')
        outro = C(rnd, 'Longer loans lower the payment, but every extra year adds interest. Which term did you pick on your last car? Tell me in the comments.',
                  'The monthly payment is the number dealers show you. The total is the number that matters. What would you choose? Let me know below.')
        title = C(rnd, f'Every Way to Pay for a {money(amt)} Car (Cash vs 36 to 84 Months)', f'The Real Cost of a {money(amt)} Car: Every Loan Term Compared')
        facts = [f'Price: {money(amt)}; APR {apr:.2f}% for every term (Federal Reserve G.19 via FRED, new car loans, {month_name(D["car"]["date"])})']
    elif k == 'card_all':
        apr = D['card']['value']; subject = f'{money(amt)} CARD DEBT'
        m, t, first = card_payoff(amt, apr)
        rows.append(dict(label='MINIMUM ONLY', price=amt, extra=t - amt, sub=yrs(m), n=m,
                         say=C(rnd, f'The minimum payment starts around {money(first)}. Paying only that takes {yrs(m)} and costs {say(t)}. ',
                               f'Minimum payments only: {yrs(m)}, {say(t)} in total. ') + hrs(t - amt)))
        for mult in (1.5, 2, 3, 5):
            fx = R.math.ceil(first * mult / 10) * 10; mm, tt, _ = card_payoff(amt, apr, fx)
            rows.append(dict(label=f'${fx:,.0f}/MO FIXED', price=amt, extra=tt - amt, sub=yrs(mm), n=mm,
                             say=C(rnd, f'A fixed ${fx:,.0f} a month: {yrs(mm)}, {money(tt)} total. ', f'Now ${fx:,.0f} every month. Done in {yrs(mm)}, for {money(tt)}. ') + hrs(tt - amt)))
        la = D['loan']['value']; lp = pmt(amt, la, 24); lt = lp * 24
        rows.append(dict(label='24-MO LOAN', price=amt, extra=lt - amt, sub=f'{money(lp)}/mo', n=24,
                         say=f'Last option: move it to a two year personal loan at the {la:.2f} percent average. {money(lp)} a month, {money(lt)} total. ' + hrs(lt - amt)))
        intro = C(rnd, f'You owe {money(amt)} on a credit card. There are many ways to pay it off, and the cost goes from painful to manageable. Here are six of them.',
                  f'{money(amt)} of credit card debt. Minimum payments, fixed payments, or a loan? Let us compare every option side by side.')
        context = f'The card rate is the Federal Reserve average for accounts that pay interest: {apr:.2f} percent. No new purchases.' + (f' A year ago, card rates averaged {D["card"]["year_ago"]:.2f} percent.' if D["card"].get("year_ago") else '')
        outro = C(rnd, 'The minimum payment is designed to keep you paying. What is your plan for your card? Tell me in the comments.',
                  'Small changes in the monthly payment change the total a lot. Which option would you choose? Let me know below.')
        title = C(rnd, f'Every Way to Pay Off {money(amt)} in Credit Card Debt, Compared', f'{money(amt)} Credit Card Debt: Minimum vs Fixed vs Loan, Real Cost')
        facts = [f'Balance {money(amt)}; card APR {apr:.2f}% (Fed, {month_name(D["card"]["date"])}); minimum = interest + 1% of balance, at least $35',
                 f'Personal loan APR {la:.2f}% (Fed, 24-month, {month_name(D["loan"]["date"])})']
    elif k == 'home_all':
        a30, a15 = D['m30']['value'], D['m15']['value']; subject = f'{money(amt)} HOUSE'
        for dp, yrs_, a in ((0.05, 30, a30), (0.10, 30, a30), (0.20, 30, a30), (0.20, 15, a15)):
            P = amt * (1 - dp); p = pmt(P, a, yrs_ * 12); t = amt * dp + p * yrs_ * 12
            rows.append(dict(label=f'{dp:.0%} DOWN · {yrs_} YR', price=amt, extra=t - amt, sub=f'{money(p)}/mo', n=yrs_ * 12, first_int=P * a / 1200,
                             say=C(rnd, f'{dp:.0%} down, {yrs_} years at {a:.2f} percent: {money(p)} a month, {say(t)} in total. ',
                                   f'With {dp:.0%} down over {yrs_} years, you pay {money(p)} a month and {say(t)} overall. ').replace('%', ' percent') + hrs(t - amt)))
        intro = C(rnd, f'The listing says {money(amt)}. What you really pay depends on your down payment and your loan. Here are four common ways to buy it.',
                  f'A {money(amt)} home. Four ways to finance it, and the totals are very different. Let us go through them.')
        context = f'We use the Freddie Mac weekly averages: {a30:.2f} percent for 30 years and {a15:.2f} percent for 15 years. Principal and interest only; taxes, insurance and mortgage insurance are not included.' + (f' A year ago, the 30 year rate averaged {D["m30"]["year_ago"]:.2f} percent.' if D["m30"].get("year_ago") else '')
        outro = C(rnd, 'A bigger down payment and a shorter loan save the most, but they need more cash up front. What would you choose? Tell me below.',
                  'Would you go 15 or 30 years at these rates? Let me know in the comments.')
        title = C(rnd, f'The Real Cost of a {money(amt)} Home: 4 Ways to Finance It', f'{money(amt)} House: 5%, 10%, 20% Down and 15 vs 30 Years Compared')
        facts = [f'Rates: 30-year {a30:.2f}%, 15-year {a15:.2f}% (Freddie Mac PMMS via FRED, week of {D["m30"]["date"]})',
                 'Principal and interest only; property tax, insurance, PMI and HOA not included.']
    elif k == 'loan_all':
        la, ca = D['loan']['value'], D['card']['value']; subject = f'BORROW {money(amt)}'
        for lab, a, n in (('LOAN · 24 MO', la, 24), ('CARD · 24 MO', ca, 24), ('CARD · 36 MO', ca, 36), ('CARD · 60 MO', ca, 60)):
            p = pmt(amt, a, n); t = p * n
            rows.append(dict(label=lab, price=amt, extra=t - amt, sub=f'{money(p)}/mo', n=n,
                             say=C(rnd, f'{lab.split(" ·")[0].title()} at {a:.2f} percent over {n} months: {money(p)} a month, {money(t)} total. ',
                                   f'Next, {n} months at {a:.2f} percent. {money(p)} a month, {money(t)} in the end. ') + hrs(t - amt)))
        m, t, first = card_payoff(amt, ca)
        rows.append(dict(label='CARD · MINIMUM', price=amt, extra=t - amt, sub=yrs(m), n=m,
                         say=f'And the minimum payment on a card: {yrs(m)}, {say(t)} total. ' + hrs(t - amt)))
        intro = C(rnd, f'You need {money(amt)}. Where you borrow it and how fast you pay it back can double the cost. Here are five ways.',
                  f'Borrowing {money(amt)}: personal loan or credit card, short or long. Let us compare the real cost of each.')
        context = f'Rates are Federal Reserve averages: personal loans {la:.2f} percent, credit cards {ca:.2f} percent.' + (f' A year ago, personal loans averaged {D["loan"]["year_ago"]:.2f} percent.' if D["loan"].get("year_ago") else '')
        outro = 'Have you ever used a personal loan or a card for a big expense? Tell me how it went in the comments.'
        title = C(rnd, f'Borrowing {money(amt)}: Personal Loan vs Credit Card, Every Option', f'The Real Cost of Borrowing {money(amt)}, 5 Ways Compared')
        facts = [f'Personal loan APR {la:.2f}%, card APR {ca:.2f}% (Federal Reserve G.19 via FRED)']
    else:
        subject = 'THE AVERAGE HOUSEHOLD'; yr = None
        items = sorted(((c, D['ce'][s]) for c, (s, _) in R.CE.items() if s in D['ce']), key=lambda x: -x[1]['value'])
        for c, d in items:
            a = d['value']; yr = d['year']
            rows.append(dict(label=c.upper(), price=a * 30, extra=0, sub=f'{money(a)}/yr', n=0, yearly=a,
                             say=C(rnd, f'{c.capitalize()}: {money(a)} a year. That is {money(a / 12)} a month, and {say(a * 30)} over 30 years.',
                                   f'Next, {c}. The average household spends {money(a)} a year, about {money(a / 365)} a day. Over 30 years: {say(a * 30)}.')))
        intro = 'Where does the average American household\'s money go? Here is the real 30 year cost of nine everyday categories, from groceries to pets.'
        context = f'All numbers come from the Bureau of Labor Statistics Consumer Expenditure Survey for {yr}, at today\'s prices with no inflation added.'
        outro = 'Which of these surprised you the most? Tell me in the comments.'
        title = f'The Real 30-Year Cost of Everyday Spending (BLS Data)'
        facts = [f'BLS Consumer Expenditure Survey {yr}, average per consumer unit (household); 30-year totals at today\'s prices.']
    for r in rows:
        t_ = r['label'].lower().replace('24-mo loan', 'the two year loan').replace(' · ', ', ').replace('/mo', ' a month').replace('% down', ' percent down')
        r['spk'] = re.sub(r'\byr\b', 'years', re.sub(r'\bmo\b', 'months', t_))
    best = min(rows, key=lambda r: r['price'] + r['extra']); worst = max(rows, key=lambda r: r['price'] + r['extra'])
    for r in rows:
        tot = r['price'] + r['extra']
        if k == 'household':
            r['say'] += ' ' + C(rnd, f'At the average wage, that is about {r["yearly"] / wage:,.0f} hours of work every year.',
                                f'That takes roughly {r["yearly"] / wage:,.0f} hours of work a year to pay for, before taxes.')
            continue
        if r is not best:
            r['say'] += ' ' + C(rnd, f'Compared with {best["spk"]}, that is {money(tot - best["price"] - best["extra"])} more.',
                                f'That is {money(tot - best["price"] - best["extra"])} more than {best["spk"]}.')
        if r.get('first_int'):
            r['say'] += ' ' + C(rnd, f'On the very first payment, {money(r["first_int"])} goes to interest.',
                                f'Of the first payment, {money(r["first_int"])} is pure interest.')
        if r['n'] and r['extra'] > 0:
            r['say'] += ' ' + C(rnd, f'The interest works out to about {money(r["extra"] / (r["n"] * 30.4))} for every day of the loan.',
                                f'Spread over the loan, the interest is about {money(r["extra"] / (r["n"] * 30.4))} a day.')
    gap = (worst['price'] + worst['extra']) - (best['price'] + best['extra'])
    if k == 'household':
        tot30 = sum(r['price'] for r in rows)
        summary = f'Add these nine together and it is {say(tot30)} over 30 years, about {say(tot30 / 30)} every year, and that is before rent or a mortgage.'
        extra_beats = [summary]
    else:
        summary = C(rnd, f'So the cheapest option is {best["spk"]} at {say(best["price"] + best["extra"])}. The most expensive is {worst["spk"]} at {say(worst["price"] + worst["extra"])}. '
                    f'The gap is {say(gap)}, or about {gap / wage:,.0f} hours of work.',
                    f'Line them up: {best["spk"]} costs {say(best["price"] + best["extra"])}, {worst["spk"]} costs {say(worst["price"] + worst["extra"])}. '
                    f'Same {"house" if k == "home_all" else "debt" if k == "card_all" else "money" if k == "loan_all" else "car"}, {money(gap)} apart.')
        mid = [r for r in rows if r['n'] and r['extra'] > 0][len([r for r in rows if r['n'] and r['extra'] > 0]) // 2]
        base_rate = {'car_all': D['car']['value'], 'home_all': D['m30']['value'] if '30' in mid['label'] else D['m15']['value'],
                     'loan_all': D['loan']['value'] if 'LOAN' in mid['label'] else D['card']['value'], 'card_all': D['card']['value']}[k]
        P = mid['price'] if k != 'home_all' else mid['price'] * (1 - float(mid['label'].split('%')[0]) / 100)
        n = mid['n']
        if k == 'card_all' and 'MINIMUM' not in mid['label']:
            fx = float(mid['label'].split('/')[0].replace('$', '').replace(',', ''))
            up = card_payoff(P, base_rate + 1, fx)[1] - card_payoff(P, base_rate, fx)[1]
        else:
            up = (pmt(P, base_rate + 1, n) - pmt(P, base_rate, n)) * n
        sens = C(rnd, f'One more thing: rates move. If the rate on the {mid["spk"]} option were just one percentage point higher, you would pay about {money(up)} more.',
                 f'And rates matter. One extra percentage point on the {mid["spk"]} option adds about {money(up)} to the total.')
        why = {'car_all': C(rnd, 'Why do longer loans cost more? Each month you pay interest on what you still owe. A longer loan keeps the balance high for longer, so interest has more months to add up.',
                            'Here is why the total grows: interest is charged every month on the remaining balance. Smaller payments shrink that balance slowly, so you pay interest for more months.'),
               'home_all': C(rnd, 'Why is the 30 year total so high? In the early years, most of each payment is interest. The balance falls slowly at first, and interest is charged on it every month for 360 months.',
                             'Mortgages are front loaded. In the first years, most of the payment goes to interest, and only a small part pays down the loan.'),
               'card_all': C(rnd, 'Why is the minimum so expensive? The minimum shrinks as the balance shrinks, so the payment keeps getting smaller and the debt lasts for years.',
                             'The minimum payment is mostly interest at the start. Because it falls as the balance falls, the payoff drags on for years.'),
               'loan_all': C(rnd, 'Two things set the cost: the rate and the time. A card rate is usually much higher than a personal loan rate, and a longer payoff gives that rate more months to work.',
                             'The cost comes down to rate times time. Higher rate, more interest each month. Longer payoff, more months of interest.')}[k]
        extra_beats = [why, summary, sens]
    beats = [intro, context] + [r['say'] for r in rows] + extra_beats + [outro]
    desc = (title + '\n\n' + '\n'.join(facts) + '\n\n' + '\n'.join(f'{r["label"].title()}: {money(r["price"] + r["extra"])} total ({r["sub"]})' for r in rows)
            + '\n\nRun your own numbers: https://debtlabai.com\n\n' + R.DISCLAIMER + '\n\n#realcost #personalfinance #money')
    return dict(key=key, subject=subject, rows=rows, beats=beats, title=title[:95], desc=desc,
                tags=['the real cost', 'personal finance', 'money', 'interest', k.replace('_all', '')])


def background():
    img = Image.new('RGB', (W, H), R.BG); d = ImageDraw.Draw(img)
    for y in range(0, H, 4):
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * y / H) for a, b in zip(R.BG, R.BG2)))
    d.text((80, 70), 'T H E   R E A L   C O S T', font=F(R.MONT, 34), fill=R.ORANGE, anchor='lm')
    return img


def frame(base, v, bi, t):
    img = base.copy(); d = ImageDraw.Draw(img)
    d.text((80, 150), v['subject'], font=F(R.ANTON, 90), fill=R.WHITE, anchor='lm')
    rows = v['rows']; shown = bi - 2                                  # 0..len(rows)
    mx = max(r['price'] + r['extra'] for r in rows)
    rh = min(100, 620 // len(rows)); y0 = 250 if rh >= 85 else 230
    for i, r in enumerate(rows):
        if i > shown or bi < 2: break
        k = R.ease(t / 1.0) if i == shown and bi == i + 2 else 1.0
        y = y0 + i * rh; cur = (i == shown and bi < len(rows) + 2)
        d.text((80, y + (rh * 0.35 if rh >= 85 else rh * 0.45)), r['label'], font=F(R.MONT, 34), fill=R.WHITE if cur else R.DIM, anchor='lm')
        if rh >= 85: d.text((80, y + rh * 0.72), r['sub'], font=F(R.MONT, 26, bold=False), fill=R.GREY, anchor='lm')
        x0, full = 520, 1050
        wb, we = full * r['price'] / mx * k, full * r['extra'] / mx * k
        if wb > 2: d.rounded_rectangle([x0, y + 14, x0 + wb, y + rh - 22], radius=8, fill=R.GREY)
        if we > 2: d.rounded_rectangle([x0 + max(0, wb - 8), y + 14, x0 + wb + we, y + rh - 22], radius=8, fill=R.ORANGE)
        d.text((W - 80, y + rh * 0.45), money((r['price'] + r['extra']) * k), font=F(R.ANTON, 50), fill=R.ORANGE if cur else R.WHITE, anchor='rm')
    if bi < 2:
        a = R.ease(t / 0.6)
        d.text((W // 2, 520), {'card_all': 'SAME DEBT.', 'loan_all': 'SAME LOAN.', 'household': 'WHERE THE MONEY GOES'}.get(v['key'][0], 'SAME PRICE.'), font=F(R.ANTON, int(120 * a) + 1), fill=R.WHITE, anchor='mm')
        if v['key'][0] != 'household':
            d.text((W // 2, 660), f'{len(rows)} WAYS TO PAY.', font=F(R.ANTON, int(120 * a) + 1), fill=R.ORANGE, anchor='mm')
    if any(r['extra'] > 0 for r in rows) and bi >= 2:
        d.rectangle([520, 885, 548, 913], fill=R.GREY); d.text((560, 899), 'PRICE', font=F(R.MONT, 26), fill=R.DIM, anchor='lm')
        d.rectangle([700, 885, 728, 913], fill=R.ORANGE); d.text((740, 899), 'INTEREST', font=F(R.MONT, 26), fill=R.DIM, anchor='lm')
    f = F(R.MONT, 36); allx = R.wrap(d, v['beats'][bi], f, 1700)
    groups = [allx[i:i + 2] for i in range(0, len(allx), 2)] or [[]]
    dur = v.get('durs', [0] * (bi + 1))[bi] or 1
    ls = groups[min(len(groups) - 1, int(t / dur * len(groups)))]
    for j, l in enumerate(ls):
        d.text((W // 2, 960 + j * 46), l, font=f, fill=R.WHITE, anchor='mm')
    return img


def render(v, mp4):
    os.environ.setdefault('TTS_SPEED', '1.08')
    import tts
    tmp = mp4.with_suffix(''); tmp.mkdir(parents=True, exist_ok=True)
    parts, durs, sr = [], [], 24000
    for i, b in enumerate(v['beats']):
        wav = tmp / f'b{i}.wav'; tts.synthesize(b, str(wav))
        a, sr = sf.read(str(wav), dtype='float32')
        a = np.concatenate([a, np.zeros(int(0.6 * sr), dtype=np.float32)]); parts.append(a); durs.append(len(a) / sr)
    sf.write(str(tmp / 'voice.wav'), np.concatenate(parts), sr)
    base = background()
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-i', str(tmp / 'voice.wav'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p',
                          '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(mp4)], stdin=subprocess.PIPE)
    v['durs'] = durs
    for i, dd in enumerate(durs):
        cache = {}
        for k in range(int(dd * FPS)):
            t = k / FPS
            ck = int(t / dd * 50)                                  # altyazı parçası değişince yeniden çiz
            if t > 1.2 and ck in cache:                            # animasyon bitti: aynı kareyi tekrar yaz (hız)
                p.stdin.write(cache[ck]); continue
            fr = frame(base, v, i, t).tobytes()
            if t > 1.15: cache = {ck: fr}
            p.stdin.write(fr)
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError('ffmpeg hata')
    return mp4


def main():
    a = sys.argv[1:]
    kind = a[a.index('--kind') + 1] if '--kind' in a else None
    privacy = os.environ.get('YT_PRIVACY', 'private')
    if not DRY:
        import upload
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        cnt = sum(1 for r in csv.DictReader(LONG_LOG.open(encoding='utf-8')) if r['date_utc'].startswith(today)) if LONG_LOG.exists() else 0
        if cnt >= int(os.environ.get('LONG_PER_DAY') or 1):
            print(f'günlük uzun video sınırı dolu ({cnt})'); return
        print('kanal:', upload.check_channel())
    D = R.load_data(); rnd = random.Random()
    key, tid = pick(rnd, kind); v = build(key, D, rnd)
    print(f'[realcost-long] {tid} → {v["title"]}', flush=True)
    R.OUT.mkdir(parents=True, exist_ok=True)
    mp4 = render(v, R.OUT / f'long_{datetime.now(timezone.utc):%Y-%m-%d_%H%M}.mp4')
    if DRY:
        print(f'  [dry-run] {mp4}\n{v["desc"]}'); return
    vid = upload.upload(mp4, v['title'], v['desc'], v['tags'], privacy)
    new = not LONG_LOG.exists()
    with LONG_LOG.open('a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['topic_id', 'date_utc', 'video_id', 'privacy', 'pillar', 'title', 'script_source'])
        if new: w.writeheader()
        w.writerow(dict(topic_id=tid, date_utc=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'), video_id=vid, privacy=privacy,
                        pillar='real_cost_long', title=v['title'], script_source='realcost_long'))
    print(f'  ✓ https://youtu.be/{vid}')


if __name__ == '__main__':
    main()
