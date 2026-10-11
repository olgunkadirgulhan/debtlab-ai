import Link from "next/link";
import { AdSlot, CalculatorGrid, Ctas, Disclaimer, Faq, Offers, PageIntro, QA } from "@/components/Blocks";

type Props = {
  href: string;
  eyebrow: string;
  title: string;
  intro: React.ReactNode;
  calculator: React.ReactNode;
  article: React.ReactNode;
  faq: QA[];
};

export default function CalculatorPage({ href, eyebrow, title, intro, calculator, article, faq }: Props) {
  return (
    <div className="mx-auto max-w-6xl px-4 pt-8">
      <nav className="mb-6 text-sm text-muted" aria-label="Breadcrumb">
        <Link href="/" className="hover:text-brand">Home</Link>
        <span className="mx-2">/</span>
        <Link href="/#calculators" className="hover:text-brand">Calculators</Link>
      </nav>
      <PageIntro eyebrow={eyebrow} title={title}>{intro}</PageIntro>
      <AdSlot id="ads-top" />
      {calculator}
      <Disclaimer />
      <AdSlot id="ads-in-content" />
      <div className="mt-12 grid gap-10 lg:grid-cols-[1fr_300px]">
        <article className="prose max-w-none">{article}</article>
        <aside className="space-y-4">
          <Offers />
          <Ctas />
        </aside>
      </div>
      <Faq items={faq} />
      <section className="mt-14">
        <h2 className="mb-5 text-2xl font-bold">More free calculators</h2>
        <CalculatorGrid exclude={href} />
      </section>
    </div>
  );
}
