import Link from "next/link";
import Icon from "@/components/Icon";
import { AFFILIATE_NOTE, CALCULATORS, DISCLAIMER, LINKS } from "@/lib/site";

/** Empty until AdSense is approved; `.ad-slot:empty` hides it so there is no blank gap. */
export function AdSlot({ id }: { id: "ads-top" | "ads-in-content" }) {
  return <div id={id} className="ad-slot my-6" />;
}

export function Ctas() {
  const app = LINKS.play_store || LINKS.app_store;
  if (!app && !LINKS.affiliate_experian) return null;
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {app && (
        <a href={app} rel="noopener" className="card flex items-center gap-4 p-5 hover:border-brand">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-soft text-brand">
            <Icon name="phone" />
          </span>
          <span>
            <span className="block font-semibold">Get the App</span>
            <span className="text-sm text-muted">Track your plan and get payoff reminders.</span>
          </span>
        </a>
      )}
      {LINKS.affiliate_experian && (
        <a href={LINKS.affiliate_experian} rel="sponsored noopener" className="card flex items-center gap-4 p-5 hover:border-brand">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-green-soft text-green">
            <Icon name="shield" />
          </span>
          <span>
            <span className="block font-semibold">
              Check Your Real Credit Score{" "}
              <span className="ml-1 rounded bg-page px-1.5 py-0.5 text-[11px] font-medium text-muted">Affiliate link</span>
            </span>
            <span className="text-sm text-muted">{AFFILIATE_NOTE}</span>
          </span>
        </a>
      )}
    </div>
  );
}

const OFFERS = {
  balance_transfer: {
    url: LINKS.affiliate_balance_transfer,
    title: "Compare 0% balance transfer cards",
    text: "A promo rate could cut the interest while you pay the balance down. Check the fee and the rate after the promo.",
    icon: "card",
  },
  personal_loan: {
    url: LINKS.affiliate_personal_loan,
    title: "Check personal loan rates",
    text: "A fixed-rate loan below your card APR could lower the total cost. Checking rates is usually a soft pull.",
    icon: "avalanche",
  },
  debt_relief: {
    url: LINKS.affiliate_debt_relief,
    title: "Struggling to keep up?",
    text: "See if a debt relief program fits your situation. It can affect your credit, so read the terms first.",
    icon: "shield",
  },
} as const;

export type OfferKey = keyof typeof OFFERS;

/** Affiliate offers with a filled link in shared/links.json; renders nothing until one exists. */
export function Offers({ keys = ["balance_transfer", "personal_loan", "debt_relief"] }: { keys?: OfferKey[] }) {
  const items = keys.map((k) => OFFERS[k]).filter((o) => o.url);
  if (!items.length) return null;
  return (
    <div className="grid gap-4">
      {items.map((o) => (
        <a key={o.title} href={o.url} rel="sponsored noopener" target="_blank" className="card flex items-center gap-4 p-5 hover:border-brand">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand">
            <Icon name={o.icon} />
          </span>
          <span>
            <span className="block font-semibold">
              {o.title}{" "}
              <span className="ml-1 rounded bg-page px-1.5 py-0.5 text-[11px] font-medium text-muted">Affiliate link</span>
            </span>
            <span className="text-sm text-muted">{o.text}</span>
          </span>
        </a>
      ))}
      <p className="text-xs text-muted">{AFFILIATE_NOTE}</p>
    </div>
  );
}

export type QA = { q: string; a: string };

export function Faq({ items }: { items: QA[] }) {
  const schema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((i) => ({ "@type": "Question", name: i.q, acceptedAnswer: { "@type": "Answer", text: i.a } })),
  };
  return (
    <section className="mt-14">
      <h2 className="mb-5 text-2xl font-bold">Frequently asked questions</h2>
      <div className="divide-y divide-line card">
        {items.map((i) => (
          <details key={i.q} className="group p-5">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold">
              {i.q}
              <span className="text-brand transition group-open:rotate-45">
                <Icon name="plus" />
              </span>
            </summary>
            <p className="mt-3 leading-relaxed text-muted">{i.a}</p>
          </details>
        ))}
      </div>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
    </section>
  );
}

export function Disclaimer() {
  return <p className="mt-6 rounded-xl bg-white p-4 text-xs leading-relaxed text-muted ring-1 ring-line">{DISCLAIMER}</p>;
}

export function CalculatorGrid({ exclude }: { exclude?: string }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {CALCULATORS.filter((c) => c.href !== exclude).map((c) => (
        <Link key={c.href} href={c.href} className="card group flex flex-col gap-3 p-5 transition hover:-translate-y-0.5 hover:border-brand hover:shadow-lg hover:shadow-brand/5">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-soft text-brand">
            <Icon name={c.icon} className="h-6 w-6" />
          </span>
          <span className="font-semibold">{c.title}</span>
          <span className="text-sm text-muted">{c.blurb}</span>
          <span className="mt-auto flex items-center gap-1 text-sm font-semibold text-brand">
            Open calculator <Icon name="arrow" className="h-4 w-4 transition group-hover:translate-x-0.5" />
          </span>
        </Link>
      ))}
    </div>
  );
}

export function PageIntro({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="mb-8 max-w-3xl">
      {eyebrow && <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-brand">{eyebrow}</p>}
      <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1>
      {children && <div className="mt-3 text-lg leading-relaxed text-muted">{children}</div>}
    </div>
  );
}

export function Stat({ label, value, tone = "ink" }: { label: string; value: string; tone?: "ink" | "green" | "red" | "brand" }) {
  const color = { ink: "text-ink", green: "text-green", red: "text-red", brand: "text-brand" }[tone];
  return (
    <div className="rounded-xl bg-page p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-extrabold tracking-tight ${color}`}>{value}</div>
    </div>
  );
}
