import type { MetadataRoute } from "next";
import { allPosts } from "@/lib/blog";
import { allSlugs } from "@/lib/payoffScenarios";
import { CALCULATORS, SITE_URL } from "@/lib/site";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: "weekly", priority: 1 },
    ...CALCULATORS.map((c) => ({ url: `${SITE_URL}${c.href}`, lastModified: now, changeFrequency: "monthly" as const, priority: 0.9 })),
    ...allSlugs().map((s) => ({ url: `${SITE_URL}/payoff/${s}/`, lastModified: now, changeFrequency: "monthly" as const, priority: 0.7 })),
    { url: `${SITE_URL}/free-debt-payoff-planner/`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${SITE_URL}/blog/`, lastModified: now, changeFrequency: "daily", priority: 0.8 },
    ...allPosts().map((p) => ({ url: `${SITE_URL}/blog/${p.slug}/`, lastModified: new Date(p.date), changeFrequency: "monthly" as const, priority: 0.7 })),
    ...["about", "privacy", "terms", "disclaimer"].map((p) => ({ url: `${SITE_URL}/${p}/`, changeFrequency: "yearly" as const, priority: 0.3 })),
  ];
}
