"use client";

import { useMemo, useState } from "react";
import NumberField from "@/components/Field";
import { Stat } from "@/components/Blocks";
import { duration, money, payoff, round2 } from "@/lib/debtMath";

function loanPayment(principal: number, apr: number, months: number) {
  const r = apr / 100 / 12;
  return r === 0 ? principal / months : (principal * r) / (1 - Math.pow(1 + r, -months));
}

export default function DebtConsolidation() {
  const [balance, setBalance] = useState(15000);
  const [apr, setApr] = useState(23.5);
  const [payment, setPayment] = useState(450);
  const [loanApr, setLoanApr] = useState(12.9);
  const [term, setTerm] = useState(48);
  const [fee, setFee] = useState(5);

  const r = useMemo(() => {
    const now = payoff(balance, apr, payment);
    const principal = fee < 100 ? balance / (1 - fee / 100) : balance;   // origination fee comes out of the loan
    const pay = loanPayment(principal, loanApr, term);
    const loanCost = round2(pay * term - balance);
    const nowCost = now ? now.totalInterest : null;
    return { now, pay: round2(pay), principal: round2(principal), loanCost, nowCost, save: nowCost === null ? null : nowCost - loanCost };
  }, [balance, apr, payment, loanApr, term, fee]);

  return (
    <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
      <div className="card h-fit space-y-4 p-5">
        <h2 className="font-semibold">Your debts today</h2>
        <NumberField label="Total balance" prefix="$" value={balance} onChange={setBalance} step={500} />
        <NumberField label="Average APR" suffix="%" value={apr} onChange={setApr} step={0.1} />
        <NumberField label="Total monthly payment" prefix="$" value={payment} onChange={setPayment} step={10} />
        <h2 className="pt-2 font-semibold">Consolidation loan</h2>
        <NumberField label="Loan APR" suffix="%" value={loanApr} onChange={setLoanApr} step={0.1} />
        <NumberField label="Term (months)" value={term} onChange={setTerm} step={6} />
        <NumberField label="Origination fee" suffix="%" value={fee} onChange={setFee} step={0.5} />
      </div>
      <div className="card p-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="New monthly payment" value={money(r.pay)} tone="brand" />
          <Stat label="Change per month" value={`${r.pay <= payment ? "−" : "+"}${money(Math.abs(payment - r.pay))}`} tone={r.pay <= payment ? "green" : "red"} />
          <Stat label="Debt-free in" value={duration(term)} />
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <Stat label="Cost today (interest)" value={r.nowCost === null ? "Never paid off" : money(r.nowCost)} tone="red" />
          <Stat label="Loan cost (interest + fee)" value={money(r.loanCost)} />
          <Stat label={r.save !== null && r.save < 0 ? "Loan costs more" : "You could save"} value={r.save === null ? "—" : money(Math.abs(r.save))} tone={r.save !== null && r.save < 0 ? "red" : "green"} />
        </div>
        <div className="mt-6 rounded-xl bg-page p-5 text-sm">
          <p>
            With a {fee}% fee you borrow about <b>{money(r.principal)}</b> to receive {money(balance)}.
            {r.now ? <> Paying {money(payment)} a month without a loan takes <b>{duration(r.now.months)}</b>.</> : <> Your current payment does not cover the interest, so the balance would never fall.</>}
          </p>
        </div>
      </div>
    </div>
  );
}
