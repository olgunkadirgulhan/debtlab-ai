import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AdSlot, Ctas, Disclaimer, Faq, Offers } from "@/components/Blocks";
import Icon from "@/components/Icon";
import ShortCard from "@/components/ShortCard";
import { allPosts, formatDate, getPost } from "@/lib/blog";
import { CALCULATORS, SITE_NAME, SITE_URL } from "@/lib/site";

export const dynamicParams = false;

export function generateStaticParams() {
  const posts = allPosts();
  // Static export needs at least one param; the placeholder 404s via notFound().
  return posts.length ? posts.map((p) => ({ slug: p.slug })) : [{ slug: "_" }];
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const post = getPost((await params).slug);
  if (!post) return {};
  return {
    title: post.title,
    description: post.description,
    alternates: { canonical: `/blog/${post.slug}/` },
    openGraph: { type: "article", title: post.title, description: post.description, publishedTime: post.date },
  };
}

export default async function PostPage({ params }: { params: Promise<{ slug: string }> }) {
  const post = getPost((await params).slug);
  if (!post) notFound();
  const calc = CALCULATORS.find((c) => c.href === post.calculator);

  const schema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.description,
    datePublished: post.date,
    author: { "@type": "Organization", name: SITE_NAME, url: SITE_URL },
    publisher: { "@type": "Organization", name: SITE_NAME, url: SITE_URL },
    mainEntityOfPage: `${SITE_URL}/blog/${post.slug}/`,
  };

  return (
    <div className="mx-auto max-w-6xl px-4 pt-8">
      <nav className="mb-6 text-sm text-muted" aria-label="Breadcrumb">
        <Link href="/" className="hover:text-brand">Home</Link>
        <span className="mx-2">/</span>
        <Link href="/blog/" className="hover:text-brand">Blog</Link>
      </nav>
      <div className="grid gap-10 lg:grid-cols-[1fr_300px]">
        <article>
          <p className="text-sm text-muted">{formatDate(post.date)} · {post.minutes} min read</p>
          <h1 className="mt-2 text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl">{post.title}</h1>
          <p className="mt-4 text-lg leading-relaxed text-muted">{post.description}</p>
          <AdSlot id="ads-top" />
          <div className="prose mt-8 max-w-none" dangerouslySetInnerHTML={{ __html: post.html }} />
          <AdSlot id="ads-in-content" />
          <Disclaimer />
          {post.faq && post.faq.length > 0 && <Faq items={post.faq} />}
        </article>
        <aside className="space-y-4 lg:sticky lg:top-24 lg:h-fit">
          {calc && (
            <Link href={calc.href} className="block rounded-2xl bg-brand p-5 text-white hover:bg-brand-dark">
              <Icon name={calc.icon} className="h-7 w-7" />
              <p className="mt-3 text-lg font-bold">Try it with your numbers</p>
              <p className="mt-1 text-sm text-white/80">{calc.title} →</p>
            </Link>
          )}
          {post.video && (
            <div className="mx-auto max-w-[220px]">
              <ShortCard id={post.video} title="Watch the 60-second version" />
            </div>
          )}
          <Offers />
          <Ctas />
        </aside>
      </div>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
    </div>
  );
}
