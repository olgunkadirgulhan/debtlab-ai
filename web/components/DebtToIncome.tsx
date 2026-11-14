"use client";

import { useMemo, useState } from "react";
import NumberField from "@/components/Field";
import { Stat } from "@/components/Blocks";
import { money } from "@/lib/debtMath";

const BANDS = [
  { max: 35, label: "Healthy", tone: "green" as const, note: "Most lenders see this as a comfortable level of debt for your income." },
  { max: 43, label: "Manageable", tone: "brand" as const, note: "Many mortgage programs still approve borrowers up to about 43%, but there is less room for surprises." },
  { max: 49, label: "Stretched", tone: "red" as const, note: "Approval gets harder and rates are often higher. Paying down a balance or two can move you back under 43%." },
  { max: Infinity, label: "High", tone: "red" as const, note: "Half or more of your income goes to debt payments. A payoff plan or lower-payment option should come first." },
];

export default function DebtToIncome() {
  const [income, setIncome] = useState(5500);
  const [housing, setHousing] = useState(1600);
  const [car, setCar] = useState(450);
  const [student, setStudent] = useState(250);
  const [cards, setCards] = useState(200);
  const [other, setOther] = useState(0);

  const r = useMemo(() => {
    const debt = housing + car + student + cards + other;
    const dti = income > 0 ? (debt / income) * 100 : 0;
    const front = income > 0 ? (housing / income) * 100 : 0;
    const band = BANDS.find((b) => dti <= b.max)!;
    const to36 = Math.max(0, debt - income * 0.36);
    const to43 = Math.max(0, debt - income * 0.43);
    return { debt, dti, front, band, to36, to43 };
  }, [income, housing, car, student, cards, other]);

  return (
    <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
      <div className="card h-fit space-y-4 p-5">
        <h2 className="font-semibold">Monthly numbers</h2>
        <NumberField label="Gross monthly income" prefix="$" value={income} onChange={setIncome} step={100} />
        <NumberField label="Rent or mortgage" prefix="$" value={housing} onChange={setHousing} step={50} />
        <NumberField label="Car loan payment" prefix="$" value={car} onChange={setCar} step={25} />
        <NumberField label="Student loan payment" prefix="$" value={student} onChange={setStudent} step={25} />
        <NumberField label="Credit card minimums" prefix="$" value={cards} onChange={setCards} step={25} />
        <NumberField label="Other debt payments" prefix="$" value={other} onChange={setOther} step={25} />
        <p className="text-xs text-muted">Use income before taxes. Leave out utilities, groceries and insurance.</p>
      </div>
      <div className="card p-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Debt-to-income" value={`${r.dti.toFixed(1)}%`} tone={r.band.tone} />
          <Stat label="Housing ratio" value={`${r.front.toFixed(1)}%`} />
          <Stat label="Monthly debt" value={money(r.debt)} />
        </div>
        <div className="mt-6 rounded-xl bg-page p-5">
          <p className="font-semibold">{r.band.label}</p>
          <p className="mt-1 text-sm text-muted">{r.band.note}</p>
        </div>
        <div className="mt-6 h-3 w-full overflow-hidden rounded-full bg-page">
          <div className="h-full rounded-full bg-brand" style={{ width: `${Math.min(100, r.dti)}%` }} />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted"><span>0%</span><span>36%</span><span>43%</span><span>50%+</span></div>
        {(r.to36 > 0 || r.to43 > 0) && (
          <ul className="mt-6 space-y-2 text-sm">
            {r.to43 > 0 && <li>To get under <b>43%</b>, lower monthly debt payments by about <b>{money(r.to43)}</b>.</li>}
            {r.to36 > 0 && <li>To get under <b>36%</b>, lower monthly debt payments by about <b>{money(r.to36)}</b>.</li>}
          </ul>
        )}
      </div>
    </div>
  );
}
