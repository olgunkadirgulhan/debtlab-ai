import type { Metadata } from "next";
import LegalPage from "@/components/LegalPage";
import { AFFILIATE_NOTE, DISCLAIMER } from "@/lib/site";

export const metadata: Metadata = { title: "Disclaimer", description: "DebtLab is educational only: calculator results are estimates based on your inputs, not financial, legal or credit advice. Affiliate links are disclosed.", alternates: { canonical: "/disclaimer/" } };

export default function Page() {
  return (
    <LegalPage title="Disclaimer" updated="September 23, 2026">
      <blockquote>{DISCLAIMER}</blockquote>
      <h2>Not financial advice</h2>
      <p>
        DebtLab&apos;s calculators, articles and videos are for general education. They do not consider your full financial situation and
        are not a recommendation to take any action. Before making financial decisions, consider speaking with a qualified professional,
        such as a nonprofit credit counselor or a licensed financial advisor.
      </p>
      <h2>Estimates, not guarantees</h2>
      <p>
        Payoff times, interest totals and savings are estimates. Real results depend on your lender&apos;s interest calculation, fees,
        rate changes, new charges and whether payments are made on time. Words like &quot;could&quot; and &quot;may&quot; are used on
        purpose: no outcome is guaranteed.
      </p>
      <h2>Credit score estimates</h2>
      <p>
        The credit score simulator gives an educational estimate from your answers. It is not a FICO® Score or VantageScore® and is not
        provided by or affiliated with Experian, Equifax, TransUnion, FICO or VantageScore Solutions. FICO is a registered trademark of Fair
        Isaac Corporation. VantageScore is a registered trademark of VantageScore Solutions, LLC.
      </p>
      <h2>Affiliate disclosure</h2>
      <p>{AFFILIATE_NOTE} This does not change the results our calculators show.</p>
      <h2>AI-assisted content</h2>
      <p>
        Some articles and video scripts are drafted with the help of AI tools. Every number in them comes from our own payoff calculations,
        not from the AI, and content is reviewed for accuracy.
      </p>
    </LegalPage>
  );
}
