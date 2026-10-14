#!/usr/bin/env python3
"""The Real Cost — ek kurgular (2026-10-14, kullanıcı: kurgular 5 katı). realcost.py'deki 7 kurguya 28 yeni (toplam 35):

ratechange, mortgageyearago, ratebump, downpay, extra50, extramortgage, carbudget, homebudget, payoffgoal, perday,
firstpayment, halfway, fourways, mattress, spendhours, spendshare, spendvs, yearsofwork, mintimequiz, aprquiz,
mortgagequiz, truefalse, higherlower, aprladder, termladder, paymentladder, doubletime, halflife

Sahneler: tag (fiyat etiketi), meter (büyük turuncu rakam), bars (gri+turuncu çubuklar), opts (şıklar), tf (doğru/yanlış),
split (tek ödemenin faiz/anapara bölünmesi). Rakamlar realcost.load_data() ile aynı resmi kaynaklardan; gerisi aritmetik.
"""
import math

import numpy as np
import soundfile as sf
from PIL import ImageDraw

import realcost as R
from realcost import money, say, pmt, card_payoff, yrs, month_name, C

KURGU = ['ratechange', 'mortgageyearago', 'ratebump', 'downpay', 'extra50', 'extramortgage', 'carbudget', 'homebudget',
         'payoffgoal', 'perday', 'firstpayment', 'halfway', 'fourways', 'mattress', 'spendhours', 'spendshare', 'spendvs',
         'yearsofwork', 'mintimequiz', 'aprquiz', 'mortgagequiz', 'truefalse', 'higherlower', 'aprladder', 'termladder',
         'paymentladder', 'doubletime', 'halflife']
W, H = R.W, R.H
GREEN = (60, 190, 110)


def amort(P, apr, n, extra=0.0):
    """(ay, toplam faiz) — sabit taksit + ek ödeme."""
    r = apr / 1200; pay = pmt(P, apr, n) + extra; bal = P; m = 0; I = 0.0
    while bal > 0.01 and m < n:
        i = bal * r; I += i; bal = bal + i - pay; m += 1
    return m, I


def bal_after(P, apr, n, k):
    r = apr / 1200; pay = pmt(P, apr, n)
    return P * (1 + r) ** k - pay * ((1 + r) ** k - 1) / r


def key_for(k, rnd, D):
    pick = rnd.choice
    if k in ('ratechange',): return [k, pick(R.CARD_BAL)] if D['card'].get('year_ago') else None
    if k == 'mortgageyearago': return [k, pick(R.HOME_P)] if D['m30'].get('year_ago') else None
    if k in ('ratebump', 'downpay', 'extramortgage', 'firstpayment', 'halfway', 'yearsofwork'): return [k, pick(R.HOME_P)]
    if k in ('extra50', 'perday', 'paymentladder', 'mintimequiz'): return [k, pick(R.CARD_BAL)]
    if k == 'carbudget': return [k, pick([300, 350, 400, 450, 500, 600, 700, 800])]
    if k == 'homebudget': return [k, pick([1500, 1800, 2000, 2200, 2500, 3000, 3500, 4000])]
    if k == 'payoffgoal': return [k, pick(R.CARD_BAL)]
    if k in ('fourways', 'aprladder', 'termladder'): return [k, pick([5000, 10000, 15000, 20000, 25000])]
    if k in ('mattress', 'doubletime', 'halflife'): return [k, pick([1000, 5000, 10000, 25000, 50000, 100000])]
    if k in ('spendhours', 'spendshare'): return [k, pick(list(R.CE))]
    if k == 'spendvs':
        a, b = rnd.sample(list(R.CE), 2); return [k] + sorted([a, b])
    if k in ('aprquiz', 'mortgagequiz'): return [k, D[('card' if k == 'aprquiz' else 'm30')]['date'][:7]]   # yeni veri gelince bir kez
    if k == 'truefalse': return [k, pick(R.CARD_BAL), pick([2, 3, 5, 10])]
    if k == 'higherlower': return [k, pick(R.CAR_P), pick(R.CARD_BAL)]
    return None


def build(key, D, rnd):
    k = key[0]; B = []; facts = []; src = 'Rates: Federal Reserve G.19 / Freddie Mac via FRED'
    card, car, loan, m30, m15 = (D[x]['value'] for x in ('card', 'car', 'loan', 'm30', 'm15'))
    wage, sav, inf = D['wage']['value'], D['sav']['value'], D['cpi_yoy']['value']
    if k == 'ratechange':
        bal = key[1]; a0 = D['card']['year_ago']; m1, t1, f1 = card_payoff(bal, card); m0, t0, f0 = card_payoff(bal, a0)
        B = [(f'Credit card rates changed this year. Here is what that means for a {money(bal)} balance.', dict(t='tag', top='BALANCE', v=money(bal), sub=f'{money(bal)} CARD')),
             (f'A year ago the average card rate was {a0:.2f} percent. Today it is {card:.2f} percent, per the Federal Reserve.', dict(t='bars', rows=[('A YEAR AGO', a0, 0, f'{a0:.2f}%'), ('TODAY', 0, card, f'{card:.2f}%')], n=2, unit='%')),
             (f'Paying only the minimum, the total was {money(t0)} at last year\'s rate.', dict(t='meter', lab='LAST YEAR\'S RATE', v=t0)),
             (f'At today\'s rate it is {money(t1)}. ' + (f'That is {money(t1 - t0)} more.' if t1 > t0 else f'That is {money(t0 - t1)} less.'), dict(t='meter', lab='TODAY\'S RATE', v=t1)),
             (C(rnd, 'Did your card rate go up or down? Comment below.', 'Do you know your card APR? Tell me below.'), dict(t='meter', lab='TODAY\'S RATE', v=t1, cta='YOUR CARD APR?'))]
        title = f'Card Rates a Year Ago vs Today: What It Means for {money(bal)} of Debt'
        facts = [f'APR {a0:.2f}% a year earlier vs {card:.2f}% now (Federal Reserve, accounts assessed interest, {month_name(D["card"]["date"])})', 'Minimum: interest + 1% of balance, at least $35']
    elif k == 'mortgageyearago':
        price = key[1]; P = price * 0.8; a0 = D['m30']['year_ago']; p0, p1 = pmt(P, a0, 360), pmt(P, m30, 360)
        B = [(f'Same {money(price)} house, bought a year ago versus today.', dict(t='tag', top='LIST PRICE', v=money(price), sub=f'{money(price)} HOUSE')),
             (f'A year ago the 30 year average was {a0:.2f} percent. This week it is {m30:.2f} percent, per Freddie Mac.', dict(t='bars', rows=[('A YEAR AGO', a0, 0, f'{a0:.2f}%'), ('THIS WEEK', 0, m30, f'{m30:.2f}%')], n=2, unit='%')),
             (f'With 20 percent down, the payment was {money(p0)} a month. Now it is {money(p1)}.', dict(t='bars', rows=[('A YEAR AGO', p0, 0, money(p0)), ('THIS WEEK', 0, p1, money(p1))], n=2)),
             (f'Over 30 years that difference is {say(abs(p1 - p0) * 360)}.', dict(t='meter', lab='DIFFERENCE OVER 30 YEARS', v=abs(p1 - p0) * 360)),
             ('Are you waiting for rates to drop? Comment below.', dict(t='meter', lab='DIFFERENCE OVER 30 YEARS', v=abs(p1 - p0) * 360, cta='WAIT OR BUY?'))]
        title = f'{money(price)} House: Mortgage Payment a Year Ago vs Today'
        facts = [f'30-year rate {a0:.2f}% a year earlier vs {m30:.2f}% (Freddie Mac PMMS via FRED, week of {D["m30"]["date"]})', 'Principal and interest only, 20% down']
    elif k == 'ratebump':
        price = key[1]; P = price * 0.8; t0 = pmt(P, m30, 360) * 360; t1 = pmt(P, m30 + 1, 360) * 360
        B = [(f'How much does one percentage point on a mortgage really cost? Let us try it on a {money(price)} home.', dict(t='tag', top='LIST PRICE', v=money(price), sub=f'{money(price)} HOUSE')),
             (f'At today\'s {m30:.2f} percent, 30 years, 20 percent down: {money(pmt(P, m30, 360))} a month.', dict(t='meter', lab=f'{m30:.2f}% · MONTHLY', v=pmt(P, m30, 360))),
             (f'At {m30 + 1:.2f} percent: {money(pmt(P, m30 + 1, 360))} a month.', dict(t='meter', lab=f'{m30 + 1:.2f}% · MONTHLY', v=pmt(P, m30 + 1, 360))),
             (f'Over the full loan, one point costs {say(t1 - t0)}.', dict(t='bars', rows=[(f'{m30:.2f}%', P, t0 - P, money(t0)), (f'{m30 + 1:.2f}%', P, t1 - P, money(t1))], n=2)),
             ('Would one point change your decision? Comment below.', dict(t='meter', lab='ONE POINT COSTS', v=t1 - t0, cta='DOES 1% MATTER?'))]
        title = f'What 1% More on a Mortgage Costs on a {money(price)} House'
        facts = [f'30-year rate {m30:.2f}% (Freddie Mac PMMS via FRED) vs +1 point for comparison']
    elif k == 'downpay':
        price = key[1]
        rows = []
        for dp in (0.05, 0.10, 0.20):
            P = price * (1 - dp); p = pmt(P, m30, 360); rows.append((f'{dp:.0%} DOWN · {money(p)}/MO', P, p * 360 - P, money(price * dp + p * 360), dp, p))
        B = [(f'5, 10 or 20 percent down on a {money(price)} house. What changes?', dict(t='tag', top='LIST PRICE', v=money(price), sub=f'{money(price)} HOUSE'))]
        for r in rows:
            B.append((f'{r[4]:.0%} down is {money(price * r[4])} up front, then {money(r[5])} a month.'.replace('%', ' percent'), dict(t='bars', rows=[x[:4] for x in rows], n=rows.index(r) + 1)))
        B.append((f'Total paid ranges from {say(price * 0.2 + rows[2][5] * 360)} to {say(price * 0.05 + rows[0][5] * 360)}, before mortgage insurance. How much did you put down? Comment below.', dict(t='bars', rows=[x[:4] for x in rows], n=3, cta='HOW MUCH DOWN?')))
        title = f'{money(price)} House: 5% vs 10% vs 20% Down, Real Cost'
        facts = [f'30-year rate {m30:.2f}% for all three (Freddie Mac via FRED)', 'Mortgage insurance (PMI), taxes and insurance not included; PMI would raise the low-down-payment totals']
    elif k == 'extra50':
        bal = key[1]; m0, t0, f0 = card_payoff(bal, card)
        # asgari + $50: her ay asgari formülü + 50
        r = card / 1200; b = bal; m = 0; t = 0.0
        while b > 0.01 and m < 1200:
            i = b * r; pay = min(max(35, i + b * 0.01) + 50, b + i); b = b + i - pay; t += pay; m += 1
        B = [(f'You owe {money(bal)} on a card. What happens if you add just 50 dollars to the minimum?', dict(t='tag', top='BALANCE', v=money(bal), sub='+$50 A MONTH')),
             (f'Minimum only: {yrs(m0)} and {say(t0)} in total.', dict(t='bars', rows=[(f'MINIMUM · {yrs(m0).upper()}', bal, t0 - bal, money(t0))], n=1)),
             (f'Minimum plus 50 dollars: {yrs(m)} and {money(t)}.', dict(t='bars', rows=[(f'MINIMUM · {yrs(m0).upper()}', bal, t0 - bal, money(t0)), (f'+$50 · {yrs(m).upper()}', bal, t - bal, money(t))], n=2)),
             (f'Fifty dollars a month saves {money(t0 - t)} and {yrs(m0 - m)}.', dict(t='meter', lab='SAVED WITH $50 MORE', v=t0 - t)),
             ('Could you add 50 dollars a month? Comment below.', dict(t='meter', lab='SAVED WITH $50 MORE', v=t0 - t, cta='COULD YOU ADD $50?'))]
        title = f'{money(bal)} Card Debt: What $50 More a Month Saves'
        facts = [f'APR {card:.2f}% (Federal Reserve)', 'Minimum: interest + 1% of balance, at least $35; no new purchases']
    elif k == 'extramortgage':
        price = key[1]; P = price * 0.8; n0, i0 = amort(P, m30, 360); n1, i1 = amort(P, m30, 360, extra=100)
        B = [(f'A home listed at {money(price)}, with a 30 year mortgage. What does 100 extra dollars a month do?', dict(t='tag', top='LIST PRICE', v=money(price), sub='+$100 A MONTH')),
             (f'Normal payment: {money(pmt(P, m30, 360))} a month, {say(i0)} in interest over 30 years.', dict(t='meter', lab='INTEREST · NORMAL', v=i0)),
             (f'Add 100 dollars a month and you finish in {yrs(n1)} with {say(i1)} in interest.', dict(t='meter', lab='INTEREST · +$100/MO', v=i1)),
             (f'That is {yrs(360 - n1)} sooner and {say(i0 - i1)} saved.', dict(t='bars', rows=[('NORMAL · 30 YEARS', P, i0, money(P + i0)), (f'+$100 · {yrs(n1).upper()}', P, i1, money(P + i1))], n=2)),
             ('Do you pay extra on your mortgage? Comment below.', dict(t='meter', lab='SAVED', v=i0 - i1, cta='DO YOU PAY EXTRA?'))]
        title = f'$100 Extra a Month on a {money(price)} Mortgage: Years Saved'
        facts = [f'30-year rate {m30:.2f}% (Freddie Mac via FRED), 20% down']
    elif k == 'carbudget':
        b = key[1]; rows = [(f'{n} MONTHS', b * (1 - (1 + car / 1200) ** -n) / (car / 1200), 0, money(b * (1 - (1 + car / 1200) ** -n) / (car / 1200))) for n in (48, 60, 72)]
        B = [(f'Your budget is {money(b)} a month for a car. How much car does that buy?', dict(t='tag', top='MONTHLY BUDGET', v=money(b), sub='CAR PAYMENT')),
             (f'At the {car:.2f} percent average, 48 months buys a {rows[0][3]} car.', dict(t='bars', rows=rows, n=1)),
             (f'60 months: {rows[1][3]}. 72 months: {rows[2][3]}.', dict(t='bars', rows=rows, n=3)),
             (f'But the 72 month loan costs {money(b * 72 - rows[2][1])} in interest.', dict(t='meter', lab='INTEREST · 72 MONTHS', v=b * 72 - rows[2][1])),
             ('What is your car payment? Comment below.', dict(t='meter', lab='INTEREST · 72 MONTHS', v=b * 72 - rows[2][1], cta='YOUR CAR PAYMENT?'))]
        title = f'How Much Car Does {money(b)} a Month Buy?'
        facts = [f'APR {car:.2f}% (Federal Reserve, new car loans), same rate for all terms; no down payment, taxes or fees']
    elif k == 'homebudget':
        b = key[1]; P = b * (1 - (1 + m30 / 1200) ** -360) / (m30 / 1200); price = P / 0.8
        B = [(f'You can pay {money(b)} a month for a mortgage. What house does that buy at today\'s rate?', dict(t='tag', top='MONTHLY BUDGET', v=money(b), sub='PRINCIPAL + INTEREST')),
             (f'At {m30:.2f} percent for 30 years, it covers a {money(P)} loan.', dict(t='meter', lab='LOAN AMOUNT', v=P)),
             (f'With 20 percent down, that is a home of {say(price)}.', dict(t='meter', lab='HOME PRICE', v=price)),
             (f'You would pay {say(b * 360 - P)} in interest over 30 years.', dict(t='bars', rows=[('LOAN', P, 0, money(P)), ('INTEREST', 0, b * 360 - P, money(b * 360 - P))], n=2)),
             ('Is that enough house where you live? Comment below.', dict(t='meter', lab='HOME PRICE', v=price, cta='ENOUGH WHERE YOU LIVE?'))]
        title = f'What House Can {money(b)} a Month Buy at Today\'s Rates?'
        facts = [f'30-year rate {m30:.2f}% (Freddie Mac via FRED); principal and interest only; taxes, insurance and HOA would lower the price you can afford']
    elif k == 'payoffgoal':
        bal = key[1]; rows = []
        for n in (12, 24, 36):
            p = pmt(bal, card, n); rows.append((f'{n} MONTHS · {money(p)}/MO', bal, p * n - bal, money(p * n)))
        B = [(f'Want {money(bal)} of card debt gone? Here is the monthly payment for one, two or three years.', dict(t='tag', top='BALANCE', v=money(bal), sub='PAYOFF GOAL'))] + \
            [(f'{r[0].split(" ·")[0].title()}: {r[0].split("· ")[1].replace("/MO", " a month")}, {r[3]} in total.', dict(t='bars', rows=rows, n=i + 1)) for i, r in enumerate(rows)] + \
            [('Which plan would you pick? Comment below.', dict(t='bars', rows=rows, n=3, cta='1, 2 OR 3 YEARS?'))]
        title = f'How to Pay Off {money(bal)} of Card Debt in 1, 2 or 3 Years'
        facts = [f'APR {card:.2f}% (Federal Reserve); no new purchases']
    elif k == 'perday':
        bal = key[1]; d = bal * card / 100 / 365
        B = [(f'How much does a {money(bal)} credit card balance cost you every day?', dict(t='tag', top='BALANCE', v=money(bal), sub='COST PER DAY')),
             (f'At the average rate of {card:.2f} percent, about {money(d)} a day.', dict(t='meter', lab='INTEREST PER DAY', v=d)),
             (f'That is {money(d * 30.4)} a month, and {money(d * 365)} a year, if the balance stays the same.', dict(t='meter', lab='INTEREST PER YEAR', v=d * 365)),
             (f'At the average wage of {money(wage)} an hour, that is {d * 365 / wage:,.0f} hours of work a year.', dict(t='meter', lab='HOURS OF WORK A YEAR', v=d * 365 / wage, hrs=True)),
             ('Did you know the daily cost? Comment below.', dict(t='meter', lab='INTEREST PER DAY', v=d, cta='DID YOU KNOW?'))]
        title = f'What a {money(bal)} Card Balance Costs You Every Day'
        facts = [f'APR {card:.2f}% (Federal Reserve), simple daily estimate on a steady balance; average hourly earnings {money(wage)} (BLS via FRED)']
    elif k == 'firstpayment':
        price = key[1]; P = price * 0.8; p = pmt(P, m30, 360); i = P * m30 / 1200
        B = [(f'Your first mortgage payment on a {money(price)} home. Where does the money go?', dict(t='tag', top='FIRST PAYMENT', v=money(p), sub=f'{money(price)} HOUSE')),
             (f'The payment is {money(p)}.', dict(t='split', tot=p, i=i, show=0)),
             (f'{money(i)} goes to interest.', dict(t='split', tot=p, i=i, show=1)),
             (f'Only {money(p - i)} pays down the loan. That is {(p - i) / p * 100:.0f} percent.', dict(t='split', tot=p, i=i, show=2)),
             ('Did you expect that? Comment below.', dict(t='split', tot=p, i=i, show=2, cta='DID YOU EXPECT IT?'))]
        title = f'Where Your First Mortgage Payment Goes ({money(price)} House)'
        facts = [f'30-year rate {m30:.2f}% (Freddie Mac via FRED), 20% down; principal and interest only']
    elif k == 'halfway':
        price = key[1]; P = price * 0.8; m = next(k_ for k_ in range(1, 361) if bal_after(P, m30, 360, k_) <= P / 2)
        B = [(f'You borrow {money(P)} for 30 years. When have you paid off half the loan?', dict(t='tag', top='LOAN', v=money(P), sub='HALF PAID OFF WHEN?')),
             ('Most people guess 15 years.', dict(t='meter', lab='GUESS', v=15, hrs='YEARS')),
             (f'At {m30:.2f} percent, it is year {m / 12:.0f}.', dict(t='meter', lab='HALF THE LOAN PAID', v=m / 12, hrs='YEARS')),
             ('Early payments are mostly interest, so the balance falls slowly at first.', dict(t='split', tot=pmt(P, m30, 360), i=P * m30 / 1200, show=2)),
             ('What did you guess? Comment below.', dict(t='meter', lab='HALF THE LOAN PAID', v=m / 12, hrs='YEARS', cta='WHAT DID YOU GUESS?'))]
        title = f'When Is Half Your Mortgage Paid Off? (Not Year 15)'
        facts = [f'30-year rate {m30:.2f}% (Freddie Mac via FRED), standard amortization']
    elif k == 'fourways':
        amt = key[1]; opts = [('CREDIT CARD', card), ('PERSONAL LOAN', loan), ('CAR LOAN', car), ('MORTGAGE RATE', m30)]
        rows = [(f'{n} · {a:.1f}%', amt, pmt(amt, a, 60) * 60 - amt, money(pmt(amt, a, 60) * 60)) for n, a in opts]
        B = [(f'Borrow {money(amt)} for five years. Same money, four different average rates.', dict(t='tag', top='YOU BORROW', v=money(amt), sub='5 YEARS'))] + \
            [(f'{n.title()} rate, {a:.2f} percent: {r[3]} in total.', dict(t='bars', rows=rows, n=i + 1)) for i, ((n, a), r) in enumerate(zip(opts, rows))] + \
            [('The rate is the whole story. Which rate do you pay? Comment below.', dict(t='bars', rows=rows, n=4, cta='WHICH RATE DO YOU PAY?'))]
        title = f'The Same {money(amt)} at 4 Different Rates: Real Cost'
        facts = ['Federal Reserve G.19 (card, 24-month personal loan, new car) and Freddie Mac 30-year rates via FRED, all applied to a 5-year payoff for comparison']
    elif k == 'mattress':
        amt = key[1]; v10 = amt / (1 + inf / 100) ** 10
        B = [(f'{money(amt)} in cash, kept at home for ten years. What is it worth?', dict(t='tag', top='CASH TODAY', v=money(amt), sub='10 YEARS AT HOME')),
             (f'Prices rose {inf:.1f} percent over the last year, per the Bureau of Labor Statistics.', dict(t='meter', lab='INFLATION, LAST 12 MONTHS', v=inf, hrs='%')),
             (f'If that rate held, in ten years your {money(amt)} would buy what {money(v10)} buys today.', dict(t='bars', rows=[('TODAY', amt, 0, money(amt)), ('IN 10 YEARS', v10, 0, money(v10))], n=2)),
             (f'That is {money(amt - v10)} of buying power gone.', dict(t='meter', lab='BUYING POWER LOST', v=amt - v10)),
             ('Do you keep cash at home? Comment below.', dict(t='meter', lab='BUYING POWER LOST', v=amt - v10, cta='CASH AT HOME?'))]
        title = f'{money(amt)} Cash at Home for 10 Years: What It Is Really Worth'
        facts = [f'Inflation {inf:.1f}% (CPI-U, 12 months to {month_name(D["cpi_yoy"]["date"])}, BLS via FRED), assumed constant']
        src = 'Data: BLS via FRED'
    elif k in ('spendhours', 'spendshare', 'spendvs'):
        ce = D['ce']
        if k == 'spendvs':
            a, b = key[1], key[2]; va, vb = ce[R.CE[a][0]]['value'], ce[R.CE[b][0]]['value']; yr = ce[R.CE[a][0]]['year']
            rows = [(a.upper(), va, 0, money(va)), (b.upper(), vb, 0, money(vb))]
            B = [(f'{a.capitalize()} or {b}: where does the average household spend more?', dict(t='opts', o=[a.upper(), b.upper()])),
                 ('Pick one.', dict(t='opts', o=[a.upper(), b.upper()])),
                 (f'{a.capitalize()}: {money(va)} a year. {b.capitalize()}: {money(vb)} a year.', dict(t='bars', rows=rows, n=2)),
                 (f'{(a if va > vb else b).capitalize()} wins by {money(abs(va - vb))}. Over 30 years that gap is {say(abs(va - vb) * 30)}.', dict(t='opts', o=[a.upper(), b.upper()], r=0 if va > vb else 1)),
                 ('Did you guess right? Comment below.', dict(t='opts', o=[a.upper(), b.upper()], r=0 if va > vb else 1, cta='DID YOU GUESS?'))]
            title = f'{a.title()} vs {b.title()}: Where Households Spend More'
        else:
            c = key[1]; v = ce[R.CE[c][0]]['value']; yr = ce[R.CE[c][0]]['year']
            if k == 'spendhours':
                B = [(f'How many hours a year does the average household work just to pay for {c}?', dict(t='tag', top='PER YEAR', v=money(v), sub=c.upper())),
                     (f'Spending on {c} is {money(v)} a year, per the Bureau of Labor Statistics.', dict(t='meter', lab=c.upper() + ' · PER YEAR', v=v)),
                     (f'At the average wage of {money(wage)} an hour, that is {v / wage:,.0f} hours, before taxes.', dict(t='meter', lab='HOURS OF WORK', v=v / wage, hrs=True)),
                     (f'About {v / wage / 40:,.1f} full work weeks every year.', dict(t='meter', lab='WORK WEEKS', v=v / wage / 40, hrs='WEEKS')),
                     ('Worth it? Comment below.', dict(t='meter', lab='HOURS OF WORK', v=v / wage, hrs=True, cta='WORTH IT?'))]
                title = f'Hours of Work a Year to Pay for {c.title()}'
            else:
                tot = ce.get('CXUTOTALEXPLB0101M', {}).get('value')
                if not tot: tot = 78535.0
                B = [(f'Out of every 100 dollars the average household spends, how much goes to {c}?', dict(t='tag', top='OUT OF', v='$100', sub=c.upper())),
                     ('Guess first.', dict(t='meter', lab=c.upper(), v=0, hrs='?')),
                     (f'{v / tot * 100:.1f} dollars. That is {money(v)} out of {money(tot)} a year.', dict(t='meter', lab=f'{c.upper()} PER $100', v=v / tot * 100)),
                     (f'Over a 40 year working life, {c} adds up to {say(v * 40)} at today\'s prices.', dict(t='meter', lab='40 YEARS', v=v * 40)),
                     ('How close was your guess? Comment below.', dict(t='meter', lab=f'{c.upper()} PER $100', v=v / tot * 100, cta='YOUR GUESS?'))]
                title = f'How Much of Every $100 Goes to {c.title()}?'
        facts = [f'BLS Consumer Expenditure Survey ({yr}), average per household (consumer unit)'] + ([f'Average hourly earnings {money(wage)} (BLS via FRED)'] if k == 'spendhours' else [])
        src = f'Data: BLS Consumer Expenditure Survey ({yr})'
    elif k == 'yearsofwork':
        price = key[1]; P = price * 0.8; tot = price * 0.2 + pmt(P, m30, 360) * 360; yrs_w = tot / (wage * 2080)
        B = [(f'How many years of full time work does a {money(price)} house really cost?', dict(t='tag', top='LIST PRICE', v=money(price), sub=f'{money(price)} HOUSE')),
             (f'With 20 percent down and a 30 year mortgage at {m30:.2f} percent, you pay {say(tot)} in total.', dict(t='meter', lab='TOTAL PAID', v=tot)),
             (f'The average full time wage is about {money(wage * 2080)} a year before taxes.', dict(t='meter', lab='AVERAGE YEARLY PAY', v=wage * 2080)),
             (f'So the house costs {yrs_w:.1f} years of gross pay. Without the interest, it would be {price / (wage * 2080):.1f}.', dict(t='meter', lab='YEARS OF WORK', v=yrs_w, hrs='YEARS')),
             ('How many years would your house take? Comment below.', dict(t='meter', lab='YEARS OF WORK', v=yrs_w, hrs='YEARS', cta='YOUR NUMBER?'))]
        title = f'A {money(price)} House in Years of Work'
        facts = [f'30-year rate {m30:.2f}% (Freddie Mac via FRED), 20% down', f'Average hourly earnings {money(wage)} x 2,080 hours (BLS via FRED), before taxes']
    elif k in ('mintimequiz', 'aprquiz', 'mortgagequiz'):
        if k == 'mintimequiz':
            bal = key[1]; m, t, _ = card_payoff(bal, card); right = yrs(m)
            wrong = [yrs(max(6, int(m * f))) for f in (0.35, 0.6)]
            q = f'Paying only the minimum on {money(bal)}, how long until it is gone?'; ans = right; tail = f'You pay {say(t)} in total.'
            title = f'Minimum Payments on {money(bal)}: How Long? Most People Guess Wrong'
        elif k == 'aprquiz':
            right = f'{card:.1f}%'; wrong = rnd.choice([[f'{card - 8:.1f}%', f'{card - 4:.1f}%'], [f'{card - 6:.1f}%', f'{card + 4:.1f}%']])
            q = 'What is the average interest rate on credit cards that charge interest?'; ans = f'{card:.2f} percent'; tail = f'On a 5,000 dollar balance that is about {money(5000 * card / 100)} a year in interest.'
            title = 'What Is the Average Credit Card Interest Rate Right Now?'
        else:
            right = f'{m30:.2f}%'; wrong = rnd.choice([[f'{m30 - 1.5:.2f}%', f'{m30 + 1.0:.2f}%'], [f'{m30 - 2.5:.2f}%', f'{m30 - 0.75:.2f}%']])
            q = 'What is the average 30 year mortgage rate this week?'; ans = f'{m30:.2f} percent'; tail = f'On a 300,000 dollar loan that is {money(pmt(300000, m30, 360))} a month.'
            title = 'What Is the Average 30-Year Mortgage Rate This Week?'
        o = [right] + wrong; rnd.shuffle(o); r = o.index(right)
        B = [(q, dict(t='opts', o=o)), (f'A: {o[0]}. B: {o[1]}. C: {o[2]}.'.replace('%', ' percent'), dict(t='opts', o=o)),
             (f'It is {"ABC"[r]}: {ans}.', dict(t='opts', o=o, r=r)), (tail, dict(t='opts', o=o, r=r)),
             ('Did you get it? Comment your answer.', dict(t='opts', o=o, r=r, cta='DID YOU GET IT?'))]
        facts = [f'Card APR {card:.2f}% (Federal Reserve, {month_name(D["card"]["date"])}); 30-year rate {m30:.2f}% (Freddie Mac, week of {D["m30"]["date"]})']
    elif k == 'truefalse':
        bal, ny = key[1], key[2]; m, t, _ = card_payoff(bal, card); tr = m <= ny * 12
        claim = f'Paying only the minimum, a {money(bal)} card balance is gone within {ny} years.'
        B = [(f'True or false? {claim}', dict(t='tf', q=claim)), ('Think about it.', dict(t='tf', q=claim)),
             (f'{"True" if tr else "False"}. It takes {yrs(m)}, and {say(t)} in total.', dict(t='tf', q=claim, r=0 if tr else 1)),
             ('Did you get it right? Comment true or false.', dict(t='tf', q=claim, r=0 if tr else 1, cta='TRUE OR FALSE?'))]
        title = f'True or False: {money(bal)} at the Minimum Is Paid Off in {ny} Years'
        facts = [f'APR {card:.2f}% (Federal Reserve); minimum = interest + 1% of balance, at least $35']
    elif k == 'higherlower':
        cp, bal = key[1], key[2]; ic = pmt(cp, car, 72) * 72 - cp; m, t, _ = card_payoff(bal, card); icd = t - bal
        o = [f'{money(cp)} CAR · 72 MO', f'{money(bal)} CARD · MIN']
        B = [(f'Which costs more interest: a {money(cp)} car loan over 72 months, or a {money(bal)} card paid at the minimum?', dict(t='opts', o=o)),
             ('Pick one.', dict(t='opts', o=o)),
             (f'The car loan: {money(ic)} in interest. The card: {money(icd)}.', dict(t='bars', rows=[('CAR LOAN', 0, ic, money(ic)), ('CARD, MINIMUM', 0, icd, money(icd))], n=2)),
             (f'So the {"car loan" if ic > icd else "card"} costs more.', dict(t='opts', o=o, r=0 if ic > icd else 1)),
             ('Did you guess right? Comment below.', dict(t='opts', o=o, r=0 if ic > icd else 1, cta='DID YOU GUESS?'))]
        title = f'More Interest: {money(cp)} Car Loan or {money(bal)} on a Card?'
        facts = [f'Car APR {car:.2f}%, card APR {card:.2f}% (Federal Reserve)', 'Card minimum: interest + 1% of balance, at least $35']
    elif k in ('aprladder', 'termladder', 'paymentladder'):
        amt = key[1]
        if k == 'aprladder':
            rates = [0, 6, 12, 18, card]; rows = [(f'{a:.1f}% APR', amt, pmt(amt, a, 36) * 36 - amt, money(pmt(amt, a, 36) * 36)) for a in rates]
            intro = f'Borrow {money(amt)} for three years. Watch what the rate does.'; lab = lambda i, r: f'{rates[i]:.0f} percent: {r[3]}.' if i < 4 else f'And the average card rate, {card:.2f} percent: {r[3]}.'
            title = f'{money(amt)} for 3 Years at 0% to {card:.0f}% APR'
            facts = [f'Average card APR {card:.2f}% (Federal Reserve); other rates for comparison']
        elif k == 'termladder':
            ns = [12, 24, 36, 48, 60]; rows = [(f'{n} MONTHS · {money(pmt(amt, loan, n))}/MO', amt, pmt(amt, loan, n) * n - amt, money(pmt(amt, loan, n) * n)) for n in ns]
            intro = f'A {money(amt)} personal loan at the {loan:.2f} percent average. One year or five?'; lab = lambda i, r: f'{ns[i]} months: {r[3]}.'
            title = f'{money(amt)} Personal Loan: 12 vs 24 vs 36 vs 48 vs 60 Months'
            facts = [f'Personal loan APR {loan:.2f}% (Federal Reserve, 24-month loans) applied to every term for comparison']
        else:
            bal = amt if amt <= 20000 else 15000; m0, t0, f0 = card_payoff(bal, card); pays = [math.ceil(f0 * x / 10) * 10 for x in (1.5, 2, 3, 4)]
            rows = [(f'MINIMUM · {yrs(m0).upper()}', bal, t0 - bal, money(t0))] + [(f'{money(p)}/MO · {yrs(card_payoff(bal, card, p)[0]).upper()}', bal, card_payoff(bal, card, p)[1] - bal, money(card_payoff(bal, card, p)[1])) for p in pays]
            intro = f'{money(bal)} on a card. Five ways to pay it.'; lab = lambda i, r: ('Minimum only' if i == 0 else f'{r[0].split(" ·")[0].replace("/MO", "")} a month') + f': {r[3]}.'
            title = f'{money(bal)} Card Debt: 5 Monthly Payments Compared'
            facts = [f'Card APR {card:.2f}% (Federal Reserve); minimum = interest + 1% of balance, at least $35']
        B = [(intro, dict(t='tag', top='AMOUNT', v=money(rows[0][1]), sub=title.split(':')[0].upper()[:24]))] + \
            [(lab(i, r), dict(t='bars', rows=rows, n=i + 1)) for i, r in enumerate(rows)] + \
            [('Which one would you choose? Comment below.', dict(t='bars', rows=rows, n=len(rows), cta='WHICH ONE?'))]
    else:                       # doubletime / halflife
        amt = key[1]
        if k == 'doubletime':
            yd = math.log(2) / math.log(1 + sav / 100)
            B = [(f'{money(amt)} in a savings account at the national average rate. How long until it doubles?', dict(t='tag', top='SAVINGS', v=money(amt), sub='DOUBLES WHEN?')),
                 (f'The average savings rate is {sav:.2f} percent, per the FDIC.', dict(t='meter', lab='AVERAGE SAVINGS RATE', v=sav, hrs='%')),
                 (f'At that rate, it takes about {yd:,.0f} years to double.', dict(t='meter', lab='YEARS TO DOUBLE', v=yd, hrs='YEARS')),
                 (f'Meanwhile prices rose {inf:.1f} percent last year. At that pace, prices double in about {math.log(2) / math.log(1 + inf / 100):,.0f} years.', dict(t='bars', rows=[('MONEY DOUBLES', yd, 0, f'{yd:,.0f} YRS'), ('PRICES DOUBLE', 0, math.log(2) / math.log(1 + inf / 100), f'{math.log(2) / math.log(1 + inf / 100):,.0f} YRS')], n=2)),
                 ('What rate does your bank pay? Comment below.', dict(t='meter', lab='YEARS TO DOUBLE', v=yd, hrs='YEARS', cta='YOUR BANK RATE?'))]
            title = f'How Long Until {money(amt)} Doubles in an Average Savings Account?'
        else:
            yh = math.log(2) / math.log(1 + inf / 100)
            B = [(f'How long until inflation cuts the buying power of {money(amt)} in half?', dict(t='tag', top='TODAY', v=money(amt), sub='HALF WHEN?')),
                 (f'Prices rose {inf:.1f} percent over the last year.', dict(t='meter', lab='INFLATION', v=inf, hrs='%')),
                 (f'If that continued, {money(amt)} would buy half as much in about {yh:,.0f} years.', dict(t='meter', lab='YEARS TO HALF', v=yh, hrs='YEARS')),
                 (f'In an account paying the {sav:.2f} percent national average, it still loses value every year.', dict(t='bars', rows=[('SAVINGS RATE', sav, 0, f'{sav:.2f}%'), ('INFLATION', 0, inf, f'{inf:.1f}%')], n=2)),
                 ('Did you expect it to be that fast? Comment below.', dict(t='meter', lab='YEARS TO HALF', v=yh, hrs='YEARS', cta='THAT FAST?'))]
            title = f'How Long Until Inflation Halves {money(amt)}?'
        facts = [f'Savings rate {sav:.2f}% (FDIC national rate via FRED, {month_name(D["sav"]["date"])})', f'Inflation {inf:.1f}% (CPI-U, 12 months, BLS via FRED), assumed constant']
        src = 'Data: FDIC and BLS via FRED'
    beats = [b for b, _ in B]; scenes = [s for _, s in B]
    desc = (title + '\n\n' + '\n'.join(facts) + '\n\nRun your own numbers: https://debtlabai.com\n\n' + src + '\n' + R.DISCLAIMER + '\n\n#Shorts #realcost #personalfinance #money')
    return dict(fmt=k, key=key, title=title[:95], desc=desc, beats=beats, scenes=scenes, src=src,
                tags=['the real cost', 'personal finance', 'money', 'interest', k, 'shorts'])


# ---------------------------------------------------------------- sahneler
F = R.font


def frame(base, v, bi, t, dur):
    img = base.copy(); d = ImageDraw.Draw(img); sc = v['scenes'][bi]; T = sc['t']; a = R.ease(t / 1.2)
    if T == 'tag':
        d.text((W // 2, 420), sc['sub'], font=F(R.ANTON, 96 if len(sc['sub']) < 18 else 70), fill=R.WHITE, anchor='mm')
        tg = R.price_tag(sc['top'], sc['v'], 6 * math.sin(t * 2.2) * math.exp(-t * 0.8)); img.paste(tg, (W // 2 - tg.width // 2, 600), tg)
    elif T == 'meter':
        d.text((W // 2, 680), sc['lab'], font=F(R.MONT, 44), fill=R.DIM, anchor='mm')
        val = sc['v'] * a; u = sc.get('hrs')
        txt = (f'{val:,.0f} HRS' if u is True else f'{val:,.1f}%' if u == '%' else f'{val:,.0f} {u}' if u == 'YEARS' or u == 'WEEKS' else '?' if u == '?' else money(val))
        if u == 'YEARS' and sc['v'] < 100: txt = f'{val:,.1f} YEARS'.replace('.0 ', ' ')
        d.text((W // 2, 900), txt, font=F(R.ANTON, 200 if len(txt) < 9 else 150), fill=R.ORANGE, anchor='mm')
    elif T == 'bars':
        rows = sc['rows']; mx = max(b + e for _, b, e, _ in rows) or 1; n = sc['n']
        for i, (lab, b, e, right) in enumerate(rows[:n]):
            k = a if i == n - 1 and not sc.get('cta') else 1.0
            y = 1000 - len(rows) * 105 + i * 210; full = 920
            d.text((80, y), lab, font=F(R.MONT, 38), fill=R.WHITE)
            d.text((W - 80, y), right, font=F(R.ANTON, 56), fill=R.WHITE, anchor='ra')
            wb, we = full * b / mx * k, full * e / mx * k
            if wb > 2: d.rounded_rectangle([80, y + 70, 80 + wb, y + 140], radius=10, fill=R.GREY)
            if we > 2: d.rounded_rectangle([80 + max(0, wb - 10), y + 70, 80 + wb + we, y + 140], radius=10, fill=R.ORANGE)
    elif T == 'opts':
        for i, o in enumerate(sc['o']):
            y = 980 - len(sc['o']) * 105 + i * 210; on = sc.get('r') == i
            d.rounded_rectangle([110, y, 970, y + 160], radius=80, fill=R.ORANGE if on else R.BG2, outline=R.WHITE if not on else R.ORANGE, width=4)
            d.text((W // 2, y + 80), (f'{"ABC"[i]}   ' if len(sc['o']) == 3 else '') + o, font=F(R.ANTON, 76 if len(o) < 16 else 54), fill=R.BG if on else R.WHITE, anchor='mm')
    elif T == 'tf':
        for j, l in enumerate(R.wrap(d, sc['q'], F(R.MONT, 56), 880)[:5]):
            d.text((W // 2, 420 + j * 74), l, font=F(R.MONT, 56), fill=R.WHITE, anchor='mm')
        for i, o in enumerate(['TRUE', 'FALSE']):
            x = 110 + i * 440; on = sc.get('r') == i
            d.rounded_rectangle([x, 900, x + 420, 1060], radius=80, fill=(GREEN if on else R.BG2), outline=R.WHITE, width=4)
            d.text((x + 210, 980), o, font=F(R.ANTON, 90), fill=R.WHITE, anchor='mm')
    elif T == 'split':
        tot, i = sc['tot'], sc['i']; d.text((W // 2, 420), f'ONE PAYMENT: {money(tot)}', font=F(R.ANTON, 90), fill=R.WHITE, anchor='mm')
        x0, x1 = 80, 1000; xi = x0 + (x1 - x0) * i / tot
        d.rounded_rectangle([x0, 560, x1, 760], radius=20, fill=R.GREY)
        if sc['show'] >= 1:
            d.rounded_rectangle([x0, 560, x0 + (xi - x0) * (a if sc['show'] == 1 else 1), 760], radius=20, fill=R.ORANGE)
            d.text((x0 + 20, 820), f'INTEREST {money(i)}', font=F(R.MONT, 44), fill=R.ORANGE, anchor='lm')
        if sc['show'] >= 2: d.text((x1 - 20, 900), f'LOAN {money(tot - i)}', font=F(R.MONT, 44), fill=R.DIM, anchor='rm')
    if sc.get('cta'):
        d.rounded_rectangle([140, 1620, 940, 1750], radius=65, fill=R.ORANGE)
        d.text((W // 2, 1685), sc['cta'], font=F(R.ANTON, 70 if len(sc['cta']) < 18 else 56), fill=R.BG, anchor='mm')
    else:
        f = F(R.MONT, 40); ls = R.wrap(d, v['beats'][bi], f, 940)
        groups = [ls[i:i + 3] for i in range(0, len(ls), 3)] or [[]]
        for j, l in enumerate(groups[min(len(groups) - 1, int(t / max(dur, 0.1) * len(groups)))]):
            d.text((W // 2, 1625 + j * 52), l, font=f, fill=R.WHITE, anchor='mm')
    d.text((W // 2, 1850), v['src'], font=F(R.MONT, 28, bold=False), fill=R.GREY, anchor='mm')
    return img


def render(v, mp4):
    import os, subprocess
    os.environ.setdefault('TTS_SPEED', '1.15')
    import tts
    tmp = mp4.with_suffix(''); tmp.mkdir(parents=True, exist_ok=True)
    parts, durs, sr = [], [], 24000
    for i, b in enumerate(v['beats']):
        wav = tmp / f'b{i}.wav'; tts.synthesize(b, str(wav))
        x, sr = sf.read(str(wav), dtype='float32')
        pad = 1.8 if b in ('Pick one.', 'Think about it.', 'Guess first.') else 0.25
        x = np.concatenate([x, np.zeros(int(pad * sr), dtype=np.float32)]); parts.append(x); durs.append(len(x) / sr)
    sf.write(str(tmp / 'voice.wav'), np.concatenate(parts), sr)
    base = R.background()
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(R.FPS), '-i', '-',
                          '-i', str(tmp / 'voice.wav'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
                          '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(mp4)], stdin=subprocess.PIPE)
    for i, dd in enumerate(durs):
        for k in range(int(dd * R.FPS)):
            p.stdin.write(frame(base, v, i, k / R.FPS, dd).tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError('ffmpeg hata')
    return mp4
