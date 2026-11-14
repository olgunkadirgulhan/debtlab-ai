import type { Metadata } from "next";
import CalculatorPage from "@/components/CalculatorPage";
import DebtConsolidation from "@/components/DebtConsolidation";

const HREF = "/calculators/debt-consolidation/";

export const metadata: Metadata = {
  title: "Debt Consolidation Calculator: Will a Loan Save You Money?",
  description:
    "Free debt consolidation calculator. Compare paying your debts as they are with a personal consolidation loan, including the origination fee, new monthly payment and total interest.",
  alternates: { canonical: HREF },
};

export default function Page() {
  return (
    <CalculatorPage
      href={HREF}
      eyebrow="Debt consolidation"
      title="Debt Consolidation Calculator"
      intro="A consolidation loan rolls several debts into one fixed payment. See whether the lower rate beats the fee, and what happens to your monthly payment."
      calculator={<DebtConsolidation />}
      article={
        <>
          <h2>How debt consolidation works</h2>
          <p>
            You take a personal loan, use it to pay off credit cards or other debts, and then repay the loan in fixed monthly
            installments over a set term, often 2 to 5 years. You trade several variable payments for one predictable one.
          </p>
          <h2>When it saves money</h2>
          <ul>
            <li>The loan APR is clearly lower than the average APR you pay today.</li>
            <li>The origination fee (often 0% to 8%) does not cancel out the interest you save.</li>
            <li>You stop adding new charges to the cards you paid off.</li>
          </ul>
          <h2>When it does not</h2>
          <p>
            A long term can lower the monthly payment while raising total interest. If the calculator shows a lower payment but a
            higher total cost, a shorter term or a debt avalanche plan may be the better deal.
          </p>
        </>
      }
      faq={[
        { q: "Does debt consolidation hurt your credit?", a: "Applying adds a hard inquiry and a new loan, which can dip your score briefly. Paying off card balances lowers utilization, which often raises scores over the following months." },
        { q: "How is the origination fee handled?", a: "Most lenders take it out of the loan amount. To receive $15,000 with a 5% fee you would borrow about $15,789. The calculator includes this." },
        { q: "Is consolidation the same as debt settlement?", a: "No. Consolidation repays everything you owe with a new loan. Settlement negotiates to pay less than you owe and usually damages your credit." },
        { q: "What credit score do I need?", a: "It varies by lender. Better scores get lower APRs, which is what makes consolidation worthwhile." },
      ]}
    />
  );
}
