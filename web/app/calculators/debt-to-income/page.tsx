import type { Metadata } from "next";
import CalculatorPage from "@/components/CalculatorPage";
import DebtToIncome from "@/components/DebtToIncome";

const HREF = "/calculators/debt-to-income/";

export const metadata: Metadata = {
  title: "Debt-to-Income Ratio Calculator (DTI): What Lenders See",
  description:
    "Free debt-to-income ratio calculator. Add your monthly income and debt payments to see your DTI, your housing ratio, and how much to pay down to get under 43% or 36%.",
  alternates: { canonical: HREF },
};

export default function Page() {
  return (
    <CalculatorPage
      href={HREF}
      eyebrow="Debt-to-income"
      title="Debt-to-Income Ratio Calculator"
      intro="Your debt-to-income ratio (DTI) is the share of your gross monthly income that goes to debt payments. Lenders use it to decide how much more you can borrow. Enter your numbers to see where you stand."
      calculator={<DebtToIncome />}
      article={
        <>
          <h2>How DTI is calculated</h2>
          <p>
            Add up every monthly debt payment: rent or mortgage, car loan, student loans, credit card minimums and any other loans.
            Divide by your gross monthly income (before taxes) and multiply by 100. If you earn $5,500 a month and pay $2,500 toward
            debts, your DTI is about 45%.
          </p>
          <h2>What counts as a good DTI</h2>
          <ul>
            <li><b>35% or less:</b> comfortable for most lenders.</li>
            <li><b>36% to 43%:</b> often still approved, especially for mortgages, but with less margin.</li>
            <li><b>44% to 49%:</b> approvals get harder and offered rates are usually higher.</li>
            <li><b>50% or more:</b> half your income is already committed to debt.</li>
          </ul>
          <h2>How to lower your DTI</h2>
          <p>
            Paying off a small balance removes its whole payment from the ratio, so the debt snowball often lowers DTI fastest.
            Refinancing to a longer term or lower rate also reduces the monthly payment, though it can raise total interest.
            Raising income works too: a side income that shows up on your tax return counts.
          </p>
        </>
      }
      faq={[
        { q: "Is DTI based on gross or net income?", a: "Lenders almost always use gross income, meaning before taxes and deductions. That is what this calculator uses." },
        { q: "Do utilities and groceries count?", a: "No. DTI only includes debt payments that appear on your credit report plus your housing payment. Utilities, phone bills, insurance and food are left out." },
        { q: "What is a front-end ratio?", a: "It is your housing payment alone divided by gross income. Many mortgage lenders like to see it at or below about 28% to 31%." },
        { q: "Does DTI affect my credit score?", a: "Not directly. Credit scores do not include income. DTI matters when a lender reviews an application." },
      ]}
    />
  );
}
