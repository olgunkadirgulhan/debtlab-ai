import type { Metadata } from "next";
import Link from "next/link";
import { Disclaimer, PageIntro } from "@/components/Blocks";
import { duration, money } from "@/lib/debtMath";
import { APRS, BALANCES, paymentFor, slugFor } from "@/lib/payoffScenarios";

export const metadata: Metadata = {
  title: "Credit Card Payoff Tables by Balance and APR",
  description:
    "Find your balance and APR to see the monthly payment for 1-5 years, how long minimum payments take, and balance transfer vs loan math.",
  alternates: { canonical: "/payoff/" },
};

export default function Page() {
  return (
    <div className="mx-auto max-w-6xl px-4 pt-8">
      <PageIntro eyebrow="Payoff tables" title="Credit card payoff tables">
        Pick the balance and APR closest to yours. Each cell shows the monthly payment to be debt-free in {duration(36)}; open it for the
        full breakdown.
      </PageIntro>
      <div className="card overflow-x-auto p-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-muted">
              <th className="py-2 pr-4 font-medium">Balance</th>
              {APRS.map((a) => (
                <th key={a} className="py-2 pr-4 font-medium">{a}% APR</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {BALANCES.map((b) => (
              <tr key={b} className="border-b border-line last:border-0">
                <td className="py-2 pr-4 font-semibold">{money(b)}</td>
                {APRS.map((a) => (
                  <td key={a} className="py-2 pr-4">
                    <Link href={`/payoff/${slugFor(b, a)}/`} className="text-brand hover:underline">
                      {money(paymentFor(b, a, 36))}/mo
                    </Link>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Disclaimer />
    </div>
  );
}
