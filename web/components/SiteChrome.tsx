import Link from "next/link";
import { CALCULATORS, DISCLAIMER, LINKS, OPERATOR, SITE_NAME } from "@/lib/site";

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 font-extrabold tracking-tight text-ink" aria-label="DebtLab home">
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
        <rect width="32" height="32" rx="9" fill="var(--brand)" />
        <path d="M8 22 13.5 15l4 3.5L24 10" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="24" cy="10" r="2.4" fill="#4ade80" />
      </svg>
      <span className="text-lg">
        Debt<span className="text-brand">Lab</span>
      </span>
    </Link>
  );
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
        <Logo />
        <nav className="flex items-center gap-1 text-sm font-medium text-muted sm:gap-2">
          <Link href="/#calculators" className="rounded-full px-3 py-2 hover:bg-brand-soft hover:text-brand">
            Calculators
          </Link>
          <Link href="/payoff/" className="hidden rounded-full px-3 py-2 hover:bg-brand-soft hover:text-brand sm:block">
            Payoff tables
          </Link>
          <Link href="/blog/" className="rounded-full px-3 py-2 hover:bg-brand-soft hover:text-brand">
            Blog
          </Link>
          <Link href="/about/" className="hidden rounded-full px-3 py-2 hover:bg-brand-soft hover:text-brand sm:block">
            About
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-20 border-t border-line bg-white">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-3">
          <Logo />
          <p className="text-sm text-muted">Free, private debt calculators. Everything runs in your browser; nothing you type is sent anywhere.</p>
        </div>
        <div>
          <h2 className="mb-3 text-sm font-semibold">Calculators</h2>
          <ul className="space-y-2 text-sm text-muted">
            {CALCULATORS.map((c) => (
              <li key={c.href}>
                <Link href={c.href} className="hover:text-brand">
                  {c.short}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="mb-3 text-sm font-semibold">DebtLab</h2>
          <ul className="space-y-2 text-sm text-muted">
            <li><Link href="/blog/" className="hover:text-brand">Blog</Link></li>
            <li><Link href="/about/" className="hover:text-brand">About</Link></li>
            {LINKS.youtube_channel && (
              <li><a href={LINKS.youtube_channel} className="hover:text-brand" rel="noopener">YouTube</a></li>
            )}
            {LINKS.play_store && (
              <li><a href={LINKS.play_store} className="hover:text-brand" rel="noopener">Android app</a></li>
            )}
          </ul>
        </div>
        <div>
          <h2 className="mb-3 text-sm font-semibold">Legal</h2>
          <ul className="space-y-2 text-sm text-muted">
            <li><Link href="/privacy/" className="hover:text-brand">Privacy Policy</Link></li>
            <li><Link href="/terms/" className="hover:text-brand">Terms of Use</Link></li>
            <li><Link href="/disclaimer/" className="hover:text-brand">Disclaimer</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-line">
        <p className="mx-auto max-w-6xl px-4 py-6 text-xs leading-relaxed text-muted">
          {DISCLAIMER} © {new Date().getFullYear()} {SITE_NAME}, operated by {OPERATOR}.
        </p>
      </div>
    </footer>
  );
}
