import type { Metadata } from "next";
import CalculatorPage from "@/components/CalculatorPage";
import BalanceTransfer from "@/components/BalanceTransfer";

const HREF = "/calculators/balance-transfer/";

export const metadata: Metadata = {
  title: "Balance Transfer Calculator: Is a 0% APR Card Worth the Fee?",
  description:
    "Free balance transfer calculator. Compare keeping your card with a 0% intro APR offer, including the transfer fee and the rate after the promo ends, and see the payment that clears it in time.",
  alternates: { canonical: HREF },
};

export default function Page() {
  return (
    <CalculatorPage
      href={HREF}
      eyebrow="Balance transfer"
      title="Balance Transfer Calculator"
      intro="A 0% intro APR can save hundreds, but only if the fee and the rate after the promo do not eat the savings. Compare both paths with your own numbers."
      calculator={<BalanceTransfer />}
      article={
        <>
          <h2>How a balance transfer saves money</h2>
          <p>
            You move a balance from a high-interest card to a new card with a low or 0% intro APR. During the intro period almost every
            dollar you pay reduces the balance instead of covering interest. Most offers charge a one-time fee of 3% to 5% of the amount moved.
          </p>
          <h2>The two numbers that decide it</h2>
          <ul>
            <li><b>The fee:</b> 3% of $6,000 is $180, added to the new balance on day one.</li>
            <li><b>What is left when the promo ends:</b> any remaining balance starts charging the regular APR, often 20% or more.</li>
          </ul>
          <p>
            The simplest rule: divide the transferred balance (including the fee) by the number of intro months. If you can pay that each
            month, a transfer almost always wins. The calculator shows that payment for your numbers.
          </p>
          <h2>Before you apply</h2>
          <ul>
            <li>You usually need good credit to qualify for the longest 0% periods.</li>
            <li>New purchases on the card may not get the intro rate.</li>
            <li>Keep paying the old card until the transfer posts.</li>
          </ul>
        </>
      }
      faq={[
        { q: "Is a balance transfer worth it with a 3% fee?", a: "Usually yes if your current APR is high and you can pay most of the balance during the intro period. The calculator compares total interest plus fee against keeping your card." },
        { q: "What happens when the 0% period ends?", a: "Any remaining balance starts accruing interest at the card's regular APR. Some store cards use deferred interest instead, which can charge interest back to the start date, so read the terms." },
        { q: "Does a balance transfer hurt my credit score?", a: "Applying adds a hard inquiry and a new account, which can lower your score slightly at first. Paying the balance down lowers your utilization, which often helps over time." },
        { q: "Can I transfer a balance between cards from the same bank?", a: "Usually not. Most issuers only accept transfers from other banks' cards." },
      ]}
    />
  );
}
