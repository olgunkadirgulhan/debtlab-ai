import type { Metadata } from "next";
import Link from "next/link";
import LegalPage from "@/components/LegalPage";
import { OPERATOR } from "@/lib/site";

export const metadata: Metadata = { title: "Terms of Use", alternates: { canonical: "/terms/" } };

export default function Page() {
  return (
    <LegalPage title="Terms of Use" updated="October 11, 2026">
      <p>By using DebtLab you agree to these terms. If you do not agree, please do not use the site.</p>
      <h2>Educational use only</h2>
      <p>
        DebtLab provides general educational information and calculators. Nothing on this site is financial, legal, tax or credit advice,
        and no advisor-client relationship is created. See our <Link href="/disclaimer/">Disclaimer</Link>.
      </p>
      <h2>Accuracy</h2>
      <p>
        Results are estimates based on the numbers you enter and simplified assumptions (for example fixed payments, monthly interest and
        no new charges). Your lender&apos;s figures may differ. We do not guarantee that any result is accurate, complete or suitable for
        your situation.
      </p>
      <h2>Acceptable use</h2>
      <p>
        Do not misuse the site, attempt to disrupt it, scrape it at a volume that affects other users, or use it for any unlawful purpose.
      </p>
      <h2>Intellectual property</h2>
      <p>
        The site&apos;s content, design and code are owned by DebtLab or its licensors. You may share links and short quotes with
        attribution.
      </p>
      <h2>Third-party links</h2>
      <p>
        We link to other websites, including affiliate partners. We are not responsible for their content, products or policies.
      </p>
      <h2>Limitation of liability</h2>
      <p>
        To the fullest extent permitted by law, DebtLab is not liable for any loss or damage arising from your use of the site or reliance
        on its content. The site is provided &quot;as is&quot; without warranties of any kind.
      </p>
      <h2>Operator</h2>
      <p>DebtLab is operated by {OPERATOR}.</p>
      <h2>Changes</h2>
      <p>We may update these terms at any time. Continued use of the site means you accept the updated terms.</p>
    </LegalPage>
  );
}
