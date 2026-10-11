import type { Metadata } from "next";
import LegalPage from "@/components/LegalPage";
import { OPERATOR } from "@/lib/site";

export const metadata: Metadata = { title: "Privacy Policy", alternates: { canonical: "/privacy/" } };

export default function Page() {
  return (
    <LegalPage title="Privacy Policy" updated="October 11, 2026">
      <p>
        This policy explains what information DebtLab (&quot;we&quot;, &quot;us&quot;) collects when you use this website and our related
        apps, and how it is used.
      </p>
      <h2>Calculator data stays on your device</h2>
      <p>
        The numbers you enter into our calculators (balances, rates, payments, answers to the score simulator) are processed entirely in
        your browser. We do not receive, store or sell them.
      </p>
      <h2>Information collected automatically</h2>
      <p>
        Like most websites, our hosting provider may log basic technical information such as IP address, browser type, pages visited and
        the time of your visit. We use aggregated data to keep the site secure and understand which pages are useful.
      </p>
      <p>
        We may use Cloudflare Web Analytics to count page views. It does not use cookies or track you across websites.
      </p>
      <h2>Cookies and advertising</h2>
      <p>
        We may show ads served by Google. Google and its partners use cookies to serve ads based on your prior visits to this and other
        websites. Google&apos;s use of advertising cookies enables it and its partners to serve ads based on your visits to this site
        and/or other sites on the Internet.
      </p>
      <p>
        You can opt out of personalized advertising by visiting{" "}
        <a href="https://adssettings.google.com" rel="noopener">Google Ads Settings</a>, or opt out of some third-party vendors&apos; use of
        cookies for personalized advertising at <a href="https://www.aboutads.info/choices/" rel="noopener">aboutads.info</a>. Where
        required by law (for example in the EEA, UK and some US states), we will ask for your consent before using such cookies.
      </p>
      <h2>Affiliate links</h2>
      <p>
        Some links on this site are affiliate links. If you sign up for a product through them, we may earn a commission at no extra cost
        to you. The partner may use cookies to track the referral. Affiliate links are labeled.
      </p>
      <h2>Embedded videos</h2>
      <p>
        Links to our YouTube videos take you to YouTube, which is governed by Google&apos;s privacy policy. We show a thumbnail image
        instead of an embedded player so no YouTube scripts load until you choose to watch.
      </p>
      <h2>Children</h2>
      <p>This site is intended for adults and is not directed to children under 13. We do not knowingly collect data from children.</p>
      <h2>Your rights</h2>
      <p>
        Depending on where you live, you may have the right to access, correct or delete personal information and to opt out of its sale
        or sharing. Because our calculators do not collect personal data, there is usually nothing for us to return or delete, but you can
        contact us with any request.
      </p>
      <h2>Changes</h2>
      <p>We may update this policy. The date at the top shows when it last changed.</p>
      <h2>Who we are</h2>
      <p>DebtLab is operated by {OPERATOR}, who is responsible for this website and the information described in this policy.</p>
      <h2>Contact</h2>
      <p>Questions about this policy can be sent through the contact details on our About page.</p>
    </LegalPage>
  );
}
