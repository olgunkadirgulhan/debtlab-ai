import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import BalanceChart from "@/components/BalanceChart";
import { AdSlot, CalculatorGrid, Ctas, Disclaimer, Faq, Offers, PageIntro, Stat } from "@/components/Blocks";
import { duration, money } from "@/lib/debtMath";
import { APRS, BALANCES, LOAN_APR, LOAN_MONTHS, PROMO_MONTHS, TRANSFER_FEE_PCT, allSlugs, buildScenario, parseSlug, slugFor } from "@/lib/payoffScenarios";

export const dynamicParams = false;

export function generateStaticParams() {
  return allSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const p = parseSlug((await params).slug);
  if (!p) return {};
  const s = buildScenario(p.balance, p.apr);
  const href = `/payoff/${slugFor(p.balance, p.apr)}/`;
  return {
    title: `Pay Off ${money(p.balance)} Credit Card Debt at ${p.apr}% APR`,
    description: `${money(p.balance)} at ${p.apr}% APR costs about ${money(s.monthlyInterest)} a month in interest. See the payment for 1-5 years, the minimum-payment trap, and balance transfer vs loan math.`,
    alternates: { canonical: href },
  };
}

function Table({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-muted">
            {head.map((h) => (
              <th key={h} className="py-2 pr-4 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-line last:border-0">
              {r.map((c, j) => (
                <td key={j} className={`py-2 pr-4 ${j === 0 ? "font-semibold" : ""}`}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const p = parseSlug((await params).slug);
  if (!p) notFound();
  const s = buildScenario(p.balance, p.apr);
  const { balance, apr, minimum, base, transfer, loan, loanPayment } = s;
  const fastest = s.byPayment[s.byPayment.length - 1];
  const transferCost = transfer ? transfer.totalInterest + transfer.fee : null;

  const faq = [
    {
      q: `How much interest does ${money(balance)} at ${apr}% APR cost per month?`,
      a: `About ${money(s.monthlyInterest)} in the first month (${apr}% divided by 12, times the balance). That amount shrinks as the balance goes down.`,
    },
    {
      q: `What payment pays off ${money(balance)} in 3 years?`,
      a: `About ${money(base.payment)} a month at ${apr}% APR, with roughly ${money(base.result.totalInterest)} of interest in total, assuming no new charges.`,
    },
    {
      q: "How long does it take with only minimum payments?",
      a: `With a minimum of 1% of the balance plus interest (at least $25), it could take ${duration(minimum.months)} and cost about ${money(minimum.totalInterest)} in interest. Your card's minimum formula may differ.`,
    },
    {
      q: "Is a balance transfer worth it here?",
      a: transferCost !== null
        ? `With a ${TRANSFER_FEE_PCT}% fee and 0% for ${PROMO_MONTHS} months, paying ${money(base.payment)} a month could cost about ${money(transferCost)} (fee plus interest) versus ${money(base.result.totalInterest)} staying at ${apr}%. It only helps if you qualify and avoid new charges.`
        : "It depends on the fee, the promo length and the rate after the promo. Use the balance transfer section above with your own offer.",
    },
  ];

  return (
    <div className="mx-auto max-w-6xl px-4 pt-8">
      <nav className="mb-6 text-sm text-muted" aria-label="Breadcrumb">
        <Link href="/" className="hover:text-brand">Home</Link>
        <span className="mx-2">/</span>
        <Link href="/payoff/" className="hover:text-brand">Payoff tables</Link>
      </nav>
      <PageIntro eyebrow="Credit card payoff" title={`How to pay off ${money(balance)} of credit card debt at ${apr}% APR`}>
        At {apr}% APR, {money(balance)} adds about {money(s.monthlyInterest)} of interest in the first month. Here is what different payments
        could change, using the same math as our calculators.
      </PageIntro>

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Interest, month 1" value={money(s.monthlyInterest)} tone="red" />
        <Stat label="Minimum payments only" value={duration(minimum.months)} tone="red" />
        <Stat label={`Paying ${money(base.payment)}/mo`} value="3 years" tone="green" />
      </div>

      <AdSlot id="ads-top" />

      <div className="mt-8 grid gap-10 lg:grid-cols-[1fr_300px]">
        <div className="space-y-10">
          <section className="card p-5 sm:p-6">
            <h2 className="mb-4 text-xl font-bold">Balance over time</h2>
            <BalanceChart
              series={[
                { name: "Minimum only", data: minimum.history, color: "#DC2626" },
                { name: `${money(base.payment)}/mo`, data: base.result.history, color: "#0F52BA" },
                { name: `${money(fastest.payment)}/mo`, data: fastest.result.history, color: "#16A34A" },
              ]}
            />
          </section>

          <section>
            <h2 className="mb-3 text-xl font-bold">Payment to be debt-free by a date</h2>
            <div className="card p-5">
              <Table
                head={["Debt-free in", "Monthly payment", "Total interest", "Total paid"]}
                rows={s.targets.map((t) => [duration(t.months), money(t.payment), money(t.result.totalInterest), money(balance + t.result.totalInterest)])}
              />
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-bold">What each monthly payment gets you</h2>
            <div className="card p-5">
              <Table
                head={["Monthly payment", "Time to pay off", "Total interest"]}
                rows={[
                  [`Minimum (starts at ${money(minimum.firstPayment)})`, duration(minimum.months), money(minimum.totalInterest)],
                  ...s.byPayment.map((o) => [money(o.payment), duration(o.result.months), money(o.result.totalInterest)]),
                ]}
              />
            </div>
            <p className="mt-3 text-sm text-muted">
              Minimum assumed as 1% of the balance plus that month&apos;s interest, at least $25. It shrinks as the balance shrinks, which is
              why it takes so long.
            </p>
          </section>

          <section className="prose max-w-none">
            <h2>Options that could lower the cost</h2>
            <h3>0% balance transfer</h3>
            {transfer && transferCost !== null ? (
              <p>
                Moving {money(balance)} to a card with 0% for {PROMO_MONTHS} months and a {TRANSFER_FEE_PCT}% fee ({money(transfer.fee)}),
                then paying the same {money(base.payment)} a month, could clear it in {duration(transfer.months)} for about{" "}
                {money(transferCost)} in fee plus interest, compared with {money(base.result.totalInterest)} staying at {apr}%. That assumes you
                qualify, make no new charges, and the rate after the promo is the same {apr}%.
              </p>
            ) : (
              <p>A transfer only helps if the promo is long enough for your payment to make real progress.</p>
            )}
            <h3>Consolidation loan</h3>
            <p>
              For illustration, a {LOAN_MONTHS}-month loan at {LOAN_APR}% APR on {money(balance)} would be about {money(loanPayment)} a month
              with {money(loan.totalInterest)} of interest, versus {money(base.result.totalInterest)} over the same 3 years at {apr}%. Real loan
              rates depend on your credit and may include origination fees.
            </p>
            <h3>Pay a fixed amount, not the minimum</h3>
            <p>
              Choosing a fixed payment and keeping it as the balance falls is the simplest change. Try your exact numbers in the{" "}
              <Link href="/calculators/credit-card-payoff/">Credit Card Payoff Calculator</Link>, or plan several cards with the{" "}
              <Link href="/calculators/debt-avalanche/">Debt Avalanche Calculator</Link>.
            </p>
          </section>

          <Disclaimer />
          <AdSlot id="ads-in-content" />

          <section>
            <h2 className="mb-3 text-xl font-bold">Same balance, other APRs</h2>
            <div className="flex flex-wrap gap-2">
              {APRS.filter((a) => a !== apr).map((a) => (
                <Link key={a} href={`/payoff/${slugFor(balance, a)}/`} className="rounded-full border border-line px-3 py-1.5 text-sm hover:border-brand hover:text-brand">
                  {money(balance)} at {a}%
                </Link>
              ))}
            </div>
            <h2 className="mb-3 mt-6 text-xl font-bold">Same APR, other balances</h2>
            <div className="flex flex-wrap gap-2">
              {BALANCES.filter((b) => b !== balance).map((b) => (
                <Link key={b} href={`/payoff/${slugFor(b, apr)}/`} className="rounded-full border border-line px-3 py-1.5 text-sm hover:border-brand hover:text-brand">
                  {money(b)} at {apr}%
                </Link>
              ))}
            </div>
          </section>
        </div>
        <aside className="space-y-4 lg:sticky lg:top-24 lg:h-fit">
          <Link href="/calculators/credit-card-payoff/" className="block rounded-2xl bg-brand p-5 text-white hover:bg-brand-dark">
            <p className="text-lg font-bold">Try it with your numbers</p>
            <p className="mt-1 text-sm text-white/80">Credit Card Payoff Calculator →</p>
          </Link>
          <Offers keys={["balance_transfer", "personal_loan", "debt_relief"]} />
          <Ctas />
        </aside>
      </div>

      <Faq items={faq} />
      <section className="mt-14">
        <h2 className="mb-5 text-2xl font-bold">Free calculators</h2>
        <CalculatorGrid />
      </section>
    </div>
  );
}
