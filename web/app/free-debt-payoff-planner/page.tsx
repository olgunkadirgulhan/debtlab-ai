import type { Metadata } from "next";
import Link from "next/link";
import { CalculatorGrid, PageIntro } from "@/components/Blocks";
import Icon from "@/components/Icon";
import { LINKS } from "@/lib/site";

const HREF = "/free-debt-payoff-planner/";

export const metadata: Metadata = {
  title: "Free Printable Debt Payoff Tracker (PDF)",
  description:
    "Download a free printable debt payoff tracker: a debt list, a 100-circle debt-free coloring chart and a 60-month countdown. Letter size PDF, no sign-up.",
  alternates: { canonical: HREF },
};

const FREE = [
  ["My Debts list", "Every balance, APR, minimum and due day in one place."],
  ["Debt payoff coloring chart", "100 circles, 1% each, with 25/50/75% milestones."],
  ["Debt-free countdown", "60 months to cross off, one payment at a time."],
];

const FULL = [
  "Snowball and avalanche order worksheets",
  "Monthly budget to find your extra payment",
  "6 debt trackers and a monthly check-in log",
  "Interest cheat sheet with real payoff math",
  "Emergency fund tracker, milestones and notes",
  "Letter and A4 sizes",
];

export default function Page() {
  return (
    <div className="mx-auto max-w-5xl px-4 pt-10">
      <PageIntro eyebrow="Free printable" title="Free debt payoff tracker (PDF)">
        Print it, fill in your debts, and color your way to zero. No email, no sign-up.
      </PageIntro>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="card p-6">
          <h2 className="text-xl font-bold">Free sample · 3 pages</h2>
          <ul className="mt-4 space-y-3">
            {FREE.map(([t, d]) => (
              <li key={t} className="flex gap-3">
                <span className="mt-0.5 text-green"><Icon name="check" className="h-5 w-5" /></span>
                <span><strong>{t}.</strong> <span className="text-muted">{d}</span></span>
              </li>
            ))}
          </ul>
          <a href="/downloads/free-debt-payoff-tracker.pdf" download className="mt-6 inline-flex items-center gap-2 rounded-full bg-brand px-5 py-3 font-semibold text-white hover:bg-brand-dark">
            Download free PDF <Icon name="arrow" className="h-4 w-4" />
          </a>
        </div>
        <div className="card p-6">
          <h2 className="text-xl font-bold">Full planner · 15 pages</h2>
          <ul className="mt-4 space-y-3">
            {FULL.map((t) => (
              <li key={t} className="flex gap-3">
                <span className="mt-0.5 text-brand"><Icon name="check" className="h-5 w-5" /></span>
                <span>{t}</span>
              </li>
            ))}
          </ul>
          {LINKS.planner_shop ? (
            <a href={LINKS.planner_shop} rel="noopener" target="_blank" className="mt-6 inline-flex items-center gap-2 rounded-full border border-brand px-5 py-3 font-semibold text-brand hover:bg-brand-soft">
              Get the full planner <Icon name="arrow" className="h-4 w-4" />
            </a>
          ) : (
            <p className="mt-6 text-sm text-muted">Coming soon.</p>
          )}
        </div>
      </div>
      <div className="prose mt-10 max-w-none">
        <h2>How to use it</h2>
        <p>
          List every debt with its balance and APR. Pick an order: smallest balance first (snowball) or highest APR first (avalanche). Pay
          the minimum on everything and put every extra dollar on the first debt. Each time the total falls by 1%, color a circle. Not sure
          what payment gets you there? The <Link href="/payoff/">payoff tables</Link> show the monthly payment for 1 to 5 years at common
          APRs.
        </p>
      </div>
      <section className="mt-12">
        <h2 className="mb-5 text-2xl font-bold">Free calculators</h2>
        <CalculatorGrid />
      </section>
    </div>
  );
}
