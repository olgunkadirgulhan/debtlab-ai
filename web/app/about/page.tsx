import type { Metadata } from "next";
import Link from "next/link";
import { CalculatorGrid, PageIntro } from "@/components/Blocks";
import { LINKS, OPERATOR } from "@/lib/site";

export const metadata: Metadata = {
  title: "About DebtLab",
  description: "DebtLab builds free, private debt payoff calculators and short videos that show the real math behind paying off debt.",
  alternates: { canonical: "/about/" },
};

const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL;

export default function Page() {
  return (
    <div className="mx-auto max-w-4xl px-4 pt-10">
      <PageIntro eyebrow="About" title="Debt is math. We show the math.">
        DebtLab makes free tools that turn a pile of balances into a clear plan with a date on it.
      </PageIntro>
      <div className="prose card p-6 sm:p-8">
        <h2>What we do</h2>
        <p>
          Most people in debt are not short on motivation; they are short on a clear picture. How long will this take? What is it costing
          me? Does an extra $100 a month matter? Our calculators answer those questions in seconds, using the same monthly interest math
          lenders use.
        </p>
        <h2>How we work</h2>
        <ul>
          <li><strong>Private by design.</strong> Calculators run in your browser. We never see your numbers.</li>
          <li><strong>Real numbers.</strong> Every figure in our articles and videos comes from an actual calculation, not a guess.</li>
          <li><strong>No hype.</strong> We avoid promises and guarantees. Your results depend on your situation.</li>
          <li><strong>Free.</strong> The site is supported by ads and clearly labeled affiliate links.</li>
        </ul>
        <h2>Where to find us</h2>
        <p>
          We post short debt-math videos on{" "}
          {LINKS.youtube_channel ? <a href={LINKS.youtube_channel} rel="noopener">YouTube</a> : "YouTube"}
          {LINKS.play_store && (
            <>
              {" "}and have a free <a href={LINKS.play_store} rel="noopener">Android app</a>
            </>
          )}
          . New guides appear on the <Link href="/blog/">blog</Link> every week.
        </p>
        <h2>Contact</h2>
        <p>{CONTACT ? <>Email us at <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.</> : "Reach us through our YouTube channel's About page."}</p>
        <p className="text-sm text-muted">DebtLab is operated by {OPERATOR}.</p>
        <p className="text-sm text-muted">DebtLab provides educational information only and is not a financial advisor.</p>
      </div>
      <section className="mt-12">
        <h2 className="mb-5 text-2xl font-bold">Our calculators</h2>
        <CalculatorGrid />
      </section>
    </div>
  );
}
