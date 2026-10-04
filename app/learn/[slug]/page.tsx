import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getAllCommodities } from "@/lib/data";
import { LEARN_ARTICLES, getLearnArticle } from "@/lib/learn-articles";
import LearnArticlePageClient from "@/components/LearnArticlePageClient";
import { OG_IMAGES } from "@/lib/og";

const SITE_URL = "https://taazabhav.com";

export async function generateStaticParams() {
  return LEARN_ARTICLES.map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const article = getLearnArticle(slug);
  if (!article) return {};

  const path = `/learn/${slug}`;
  return {
    title: article.title,
    description: article.description,
    alternates: { canonical: path },
    openGraph: { images: OG_IMAGES, title: article.title, description: article.description, url: path },
  };
}

export default async function LearnArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = getLearnArticle(slug);
  if (!article) notFound();

  const commodities = await getAllCommodities();

  const articleJsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: article.title,
    description: article.description,
    datePublished: article.datePublished,
    dateModified: article.dateModified ?? article.datePublished,
    author: { "@type": "Organization", name: "TaazaBhav", url: SITE_URL },
    publisher: { "@type": "Organization", name: "TaazaBhav", url: SITE_URL },
    mainEntityOfPage: `${SITE_URL}/learn/${slug}`,
    inLanguage: "en-IN",
  };

  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: article.faqs.map((f) => ({
      "@type": "Question",
      name: f.q,
      acceptedAnswer: { "@type": "Answer", text: f.a },
    })),
  };

  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "Learn", item: `${SITE_URL}/learn` },
      { "@type": "ListItem", position: 3, name: article.title, item: `${SITE_URL}/learn/${slug}` },
    ],
  };

  return (
    <>
      {/* eslint-disable-next-line react/no-danger */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd) }} />
      {/* eslint-disable-next-line react/no-danger */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }} />
      {/* eslint-disable-next-line react/no-danger */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }} />
      <LearnArticlePageClient
        commodities={commodities}
        slug={slug}
        title={article.title}
        hindiTitle={article.hindiTitle}
        dek={article.dek}
        dekHi={article.dekHi}
        body={article.body}
        bodyHi={article.bodyHi}
        faqs={article.faqs}
        faqsHi={article.faqsHi}
        related={article.related}
        relatedHi={article.relatedHi}
      />
    </>
  );
}
