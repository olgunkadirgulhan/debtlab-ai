"use client";

import { useMemo, useState } from "react";
import NumberField from "@/components/Field";
import { Stat } from "@/components/Blocks";
import { duration, money, payoff, round2 } from "@/lib/debtMath";

/** Fixed payment; promo APR for `promoMonths`, then `afterApr`. null = never paid off. */
function transfer(balance: number, promoApr: number, promoMonths: number, afterApr: number, payment: number) {
  let b = balance, months = 0, interest = 0;
  while (b > 0.005 && months < 600) {
    const rate = (months < promoMonths ? promoApr : afterApr) / 100 / 12;
    const i = b * rate;
    if (months >= promoMonths && payment <= i) return null;
    interest += i; b = Math.max(0, b + i - payment); months++;
  }
  return months >= 600 ? null : { months, totalInterest: round2(interest) };
}

export default function BalanceTransfer() {
  const [balance, setBalance] = useState(6000);
  const [apr, setApr] = useState(24.99);
  const [payment, setPayment] = useState(300);
  const [promoApr, setPromoApr] = useState(0);
  const [promoMonths, setPromoMonths] = useState(18);
  const [fee, setFee] = useState(3);
  const [afterApr, setAfterApr] = useState(24.99);

  const r = useMemo(() => {
    const stay = payoff(balance, apr, payment);
    const feeAmt = round2((balance * fee) / 100);
    const moved = transfer(balance + feeAmt, promoApr, promoMonths, afterApr, payment);
    const clearIn = promoMonths > 0 ? Math.ceil((balance + feeAmt) / promoMonths) : 0;
    const stayCost = stay ? stay.totalInterest : null;
    const movedCost = moved ? moved.totalInterest + feeAmt : null;
    return { stay, moved, feeAmt, clearIn, stayCost, movedCost, save: stayCost !== null && movedCost !== null ? stayCost - movedCost : null };
  }, [balance, apr, payment, promoApr, promoMonths, fee, afterApr]);

  return (
    <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
      <div className="card h-fit space-y-4 p-5">
        <h2 className="font-semibold">Current card</h2>
        <NumberField label="Balance" prefix="$" value={balance} onChange={setBalance} step={100} />
        <NumberField label="Current APR" suffix="%" value={apr} onChange={setApr} step={0.1} />
        <NumberField label="Monthly payment" prefix="$" value={payment} onChange={setPayment} step={10} />
        <h2 className="pt-2 font-semibold">Transfer offer</h2>
        <NumberField label="Intro APR" suffix="%" value={promoApr} onChange={setPromoApr} step={0.1} />
        <NumberField label="Intro period (months)" value={promoMonths} onChange={setPromoMonths} step={1} />
        <NumberField label="Transfer fee" suffix="%" value={fee} onChange={setFee} step={0.5} />
        <NumberField label="APR after intro" suffix="%" value={afterApr} onChange={setAfterApr} step={0.1} />
      </div>
      <div className="card p-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Keep current card" value={r.stayCost === null ? "Never paid off" : money(r.stayCost)} tone="red" />
          <Stat label="Transfer (interest + fee)" value={r.movedCost === null ? "Never paid off" : money(r.movedCost)} tone="brand" />
          <Stat label={r.save !== null && r.save < 0 ? "Transfer costs more" : "You could save"} value={r.save === null ? "—" : money(Math.abs(r.save))} tone={r.save !== null && r.save < 0 ? "red" : "green"} />
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <Stat label="Payoff now" value={r.stay ? duration(r.stay.months) : "—"} />
          <Stat label="Payoff after transfer" value={r.moved ? duration(r.moved.months) : "—"} />
          <Stat label="Transfer fee" value={money(r.feeAmt)} />
        </div>
        <div className="mt-6 rounded-xl bg-page p-5 text-sm">
          {r.moved && r.moved.months <= promoMonths ? (
            <p>At {money(payment)} a month you clear the balance <b>before the intro rate ends</b>.</p>
          ) : (
            <p>To clear the transferred balance before the intro rate ends, pay about <b>{money(r.clearIn)}</b> a month.</p>
          )}
        </div>
      </div>
    </div>
  );
}
