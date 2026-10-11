// Static "pay off $X at Y% APR" pages. Every number on these pages comes from
// the same math as the calculators (lib/debtMath.ts, shared/debt_math.py).
import { payoff, round2 } from "@/lib/debtMath";

export const BALANCES = [1000, 2000, 3000, 5000, 7500, 10000, 12000, 15000, 20000, 25000, 30000, 50000];
export const APRS = [18, 20, 22, 24, 26, 29];

export const PROMO_MONTHS = 18;
export const TRANSFER_FEE_PCT = 3;
// Illustrative loan rate for the "consolidate" comparison; the page says so.
export const LOAN_APR = 12;
export const LOAN_MONTHS = 36;

export function slugFor(balance: number, apr: number) {
  return `${balance}-at-${apr}-apr`;
}

export function parseSlug(slug: string) {
  const m = /^(\d+)-at-(\d+)-apr$/.exec(slug);
  if (!m) return null;
  const balance = Number(m[1]);
  const apr = Number(m[2]);
  return BALANCES.includes(balance) && APRS.includes(apr) ? { balance, apr } : null;
}

export function allSlugs() {
  return BALANCES.flatMap((b) => APRS.map((a) => slugFor(b, a)));
}

/** Fixed monthly payment that clears `balance` in `months` (rounded up to the dollar). */
export function paymentFor(balance: number, apr: number, months: number) {
  const r = apr / 100 / 12;
  return Math.ceil((balance * r) / (1 - Math.pow(1 + r, -months)));
}

/** Port of debt_math.payoff_minimum: pct% of balance + interest, at least `floor`. */
export function payoffMinimum(balance: number, apr: number, pct = 1, floor = 25, maxMonths = 600) {
  const r = apr / 100 / 12;
  let months = 0;
  let interest = 0;
  let first = 0;
  const history = [round2(balance)];
  while (balance > 0.005 && months < maxMonths) {
    const i = balance * r;
    const pay = Math.min(balance + i, Math.max(floor, (balance * pct) / 100 + i));
    if (!months) first = round2(pay);
    interest += i;
    balance = Math.max(0, balance + i - pay);
    months++;
    history.push(round2(balance));
  }
  return { months, totalInterest: round2(interest), firstPayment: first, history };
}

/** Port of facts.promo_payoff: fee added to the balance, 0% for `promoMonths`, then `apr`. */
export function payoffPromo(balance: number, apr: number, payment: number, promoMonths = PROMO_MONTHS, feePct = TRANSFER_FEE_PCT) {
  const fee = round2((balance * feePct) / 100);
  let b = balance + fee;
  let months = 0;
  let interest = 0;
  const history = [round2(b)];
  while (b > 0.005 && months < 600) {
    const i = months < promoMonths ? 0 : (b * apr) / 100 / 12;
    if (payment <= i) return null;
    interest += i;
    b = Math.max(0, b + i - payment);
    months++;
    history.push(round2(b));
  }
  return { months, totalInterest: round2(interest), fee, history };
}

export function buildScenario(balance: number, apr: number) {
  const monthlyInterest = round2((balance * apr) / 100 / 12);
  const minimum = payoffMinimum(balance, apr);

  // Payment options: % of the balance, rounded to a clean amount, always above the interest.
  const step = balance >= 10000 ? 50 : balance >= 3000 ? 25 : 10;
  const options = [...new Set([0.03, 0.04, 0.05, 0.075, 0.1].map((p) => Math.max(Math.ceil((balance * p) / step) * step, Math.ceil(monthlyInterest + step))))];
  const byPayment = options.map((payment) => ({ payment, result: payoff(balance, apr, payment)! }));

  const targets = [12, 24, 36, 48, 60].map((months) => {
    const payment = paymentFor(balance, apr, months);
    return { months, payment, result: payoff(balance, apr, payment)! };
  });

  const base = targets.find((t) => t.months === 36)!;
  const transfer = payoffPromo(balance, apr, base.payment);
  const loanPayment = paymentFor(balance, LOAN_APR, LOAN_MONTHS);
  const loan = payoff(balance, LOAN_APR, loanPayment)!;

  return { balance, apr, monthlyInterest, minimum, byPayment, targets, base, transfer, loanPayment, loan };
}

export type Scenario = ReturnType<typeof buildScenario>;
