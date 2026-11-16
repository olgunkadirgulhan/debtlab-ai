import type { Metadata } from "next";
import Link from "next/link";
import { PageIntro } from "@/components/Blocks";
import { OPERATOR } from "@/lib/site";

export const metadata: Metadata = {
  title: "Contact DebtLab",
  description: "How to reach DebtLab: questions about our debt payoff calculators, corrections, feedback and partnership requests.",
  alternates: { canonical: "/contact/" },
};

const CONTACT = process.env.NEXT_PUBLIC_CONTACT_EMAIL;

export default function Page() {
  return (
    <div className="mx-auto max-w-4xl px-4 pt-10">
      <PageIntro eyebrow="Contact" title="Get in touch">
        Questions, corrections or ideas for a new calculator? We read every message.
      </PageIntro>
      <div className="prose card p-6 sm:p-8">
        <h2>Email</h2>
        <p>
          {CONTACT ? <>Write to <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.</> : "Reach us through our YouTube channel's About page."} We usually
          reply within 2 business days (Monday to Friday).
        </p>
        <h2>What we can help with</h2>
        <ul>
          <li><strong>Calculator questions.</strong> If a result looks wrong, send the numbers you entered (balance, APR, payment) and we will check the math.</li>
          <li><strong>Corrections.</strong> Spotted an error in an article or payoff table? Tell us the page and we will fix it and note the update.</li>
          <li><strong>Feedback and ideas.</strong> Suggestions for new calculators, printables or guides are welcome.</li>
          <li><strong>Partnerships and press.</strong> We only work with partners that fit our readers; sponsored content is always labeled.</li>
        </ul>
        <h2>What we can't do</h2>
        <p>
          DebtLab provides educational information only. We are not financial advisors, credit counselors or lenders, so we can't give personal
          financial advice, review your credit report or negotiate with creditors. For one-on-one help, consider a nonprofit credit counseling
          agency approved by the U.S. Department of Justice or accredited by the NFCC.
        </p>
        <h2>Privacy</h2>
        <p>
          Our calculators run in your browser and we never see the numbers you type. If you email us, we use your message only to reply. See our{" "}
          <Link href="/privacy/">Privacy Policy</Link> for details.
        </p>
        <p className="text-sm text-muted">DebtLab is operated by {OPERATOR}.</p>
      </div>
    </div>
  );
}
