import { packRows } from "@/lib/packed-rows";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getAllCommodities, getPricesForCommodity, computeRadar, getCommodityHistory, getMarketTranslations } from "@/lib/data";
import { summarizePrices, longDate, shortDate, byDateThenPrice } from "@/lib/price-stats";
import { commodityToSlug, slugToCommodity } from "@/lib/slug";
import { getMsp } from "@/lib/msp";
import { timeAgo, formatUpdatedStamp } from "@/lib/time";
import { getPrimaryHindiAlias, getHindiAliases } from "@/lib/aliases";
import { buildCommodityFaqs } from "@/lib/faq-commodity";
import { getComparePairs } from "@/lib/compare";
import { getCategory, categoryToSlug } from "@/lib/categories";
import { LEARN_ARTICLES } from "@/lib/learn-articles";
import CommodityPageClient from "@/components/CommodityPageClient";
import { OG_IMAGES } from "@/lib/og";

// Egress fix (24 Sep 2026): 6h instead of 1h. Fresh prices still appear
// right after each 3×-daily fetch via the /api/revalidate hook (needs
// REVALIDATE_SECRET set in Vercel + GitHub). This mainly stops crawler
// visits from re-querying Supabase every hour on 1,500+ URLs.
export const revalidate = 21600;

// Same local-const pattern as app/layout.tsx and app/sitemap.ts — not
// worth a shared module for one string used in a handful of places.
const SITE_URL = "https://taazabhav.com";

function fmt(n: number) {
  return "₹" + Math.round(n).toLocaleString("en-IN");
}

// Pre-renders one static page per commodity at build/revalidate time —
// this is what makes each one a real, independently indexable URL rather
// than a client-side filter of the homepage.
// Build-time fix #2 (24 Sep 2026): even after the commodity+state and
// compare pages moved to on-demand rendering, deploys still took ~15 min —
// every remaining page type was still being rendered (with its database
// queries) at build. Now no data page is rendered at deploy time: each one
// renders on its first visit and is cached (see `revalidate`). Deploys stop
// touching Supabase at all, which also saves egress on every deploy.
export async function generateStaticParams() {
  return [];
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ commodity: string }>;
}): Promise<Metadata> {
  const { commodity: slug } = await params;
  const allCommodities = await getAllCommodities();
  const commodity = slugToCommodity(slug, allCommodities);
  if (!commodity) return {};

  // Scoped to this one commodity at the database level — see
  // getPricesForCommodity's comment in lib/data.ts for why this matters
  // (this used to fetch every commodity's rows just to filter one out).
  const rows = await getPricesForCommodity(commodity);
  // Headline numbers from the shared summarizePrices() — latest date's
  // usable rows only. dateLabel used to be rows[0]?.priceDate, i.e. the
  // date of whichever row happened to come first, which is how titles
  // ended up dated a day behind the data (see lib/price-stats.ts).
  const summary = summarizePrices(rows);
  const { lo, hi } = summary;
  const dateLabel = summary.latestDate;

  // Romanized Hindi alias ("Pyaj" for "Onion") pushed into the title/meta so
  // a Hindi-phonetic search actually has a chance of matching this page's
  // own text, not just the on-site search box — see lib/aliases.ts.
  const hindiAlias = getPrimaryHindiAlias(commodity);
  // Devanagari name too ("प्याज़") — most Hindi searches are typed in
  // Devanagari, and the title is what Google matches first.
  const dv = rows.find((r) => r.dv)?.dv;
  const aliasParts = [hindiAlias, dv].filter(Boolean);
  const aliasSuffix = aliasParts.length ? ` (${aliasParts.join(" / ")})` : "";

  // Kept near Google's ~60-character title limit (26 Sep 2026): the old
  // "— Live Price Across India" tail was always cut off in results.
  const title = `${commodity}${aliasSuffix} Mandi Bhav Today, ${shortDate(dateLabel)} ${dateLabel.slice(0, 4)}`;
  const description = `${commodity}${aliasSuffix} mandi rate today: ₹${lo}–₹${hi} per quintal (₹${Math.round(lo / 100)}–₹${Math.round(hi / 100)}/kg) across ${summary.count} APMC markets, sourced live from Agmarknet. Updated 3× daily on TaazaBhav.`;

  return {
    title,
    description,
    alternates: { canonical: `/mandi-bhav/${slug}` },
    openGraph: { images: OG_IMAGES, title, description, url: `/mandi-bhav/${slug}` },
  };
}

export default async function CommodityPage({
  params,
}: {
  params: Promise<{ commodity: string }>;
}) {
  const { commodity: slug } = await params;
  const allCommodities = await getAllCommodities();
  const commodity = slugToCommodity(slug, allCommodities);
  if (!commodity) notFound();

  // Scoped to this one commodity — see getPricesForCommodity's comment in
  // lib/data.ts. computeRadar below only ever needs this commodity's own
  // rows anyway (it groups by commodity+variety internally), so nothing
  // downstream on this page actually needed the other 15 commodities.
  // Latest reporting date first, then highest price first — most visitors
  // are deciding where to sell today. Every row is still listed (unusual /
  // earlier-date rows carry a visible tag); headline numbers come from
  // summarizePrices() — see lib/price-stats.ts.
  const rows = (await getPricesForCommodity(commodity)).sort(byDateThenPrice);
  const summary = summarizePrices(rows);
  const { lo, hi } = summary;
  const dv = rows[0]?.dv;
  const dateLabel = summary.latestDate;
  const latestFetchedAt = rows.reduce((max, r) => (r.fetchedAt > max ? r.fetchedAt : max), "");
  const freshnessLabel = latestFetchedAt ? timeAgo(latestFetchedAt) : "";
  const updatedStamp = latestFetchedAt ? formatUpdatedStamp(latestFetchedAt) : "";

  // Romanized Hindi alias(es) — see lib/aliases.ts. hindiAlias is the single
  // most-common spelling for the H1; hindiAliases is the full list for the
  // JSON-LD alternateName (search engines can match any of them, so no
  // reason to only expose one there).
  const hindiAlias = getPrimaryHindiAlias(commodity);
  const hindiAliases = getHindiAliases(commodity);

  const radarEntry = computeRadar(rows).find((r) => r.commodity === commodity);

  // A plain wa.me deep link, no API/app integration needed — this is the
  // whole audience's actual distribution channel (see Phase 3's "Bhav Bot"
  // idea, which this is a free, zero-infrastructure preview of). Built
  // server-side since this is a server component; encodeURIComponent is a
  // standard global in Node, not just the browser.
  const shareText = `${commodity} Mandi Bhav — ${longDate(dateLabel)}: typical ${fmt(summary.typical)} / quintal (range ${fmt(lo)}–${fmt(hi)}) across ${summary.count} markets. Full list: ${SITE_URL}/mandi-bhav/${slug}`;
  const shareUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;

  // 21-day price trend — a small sparkline over the daily average modal
  // price. Naturally sparse for the first few weeks after launch (one
  // point per day the fetcher actually ran); the chart and summary line
  // both just quietly say less the fewer points there are.
  const history = await getCommodityHistory(commodity, 21);
  const trendStats =
    history.length >= 2
      ? (() => {
          const first = history[0].avgModal;
          const last = history[history.length - 1].avgModal;
          const pctChange = ((last - first) / first) * 100;
          const values = history.map((h) => h.avgModal);
          return {
            pctChange,
            windowLo: Math.min(...values),
            windowHi: Math.max(...values),
            days: history.length,
          };
        })()
      : null;

  // MSP comparison — only ~23 crops nationwide carry a government Minimum
  // Support Price at all; most commodities here (onion, potato, tomato...)
  // simply don't, and that absence is itself useful information for a
  // visitor who assumes every crop has a floor price.
  const msp = getMsp(commodity);
  const mspStats = msp
    ? (() => {
        // modalPrice is typed as `number`, but Postgres NUMERIC columns
        // come back through the `pg` driver as strings — Number() guards
        // against "+" silently string-concatenating instead of summing.
        // Also drop any row whose price doesn't parse at all (a bad/missing
        // value in one of potentially hundreds of national market rows)
        // rather than letting a single bad entry NaN the entire average.
        // Since 24 Sep 2026: typical (median) price of the headline rows,
        // and the below-MSP count out of those same markets — so "X of N
        // markets" uses the same N as the hero line.
        const validModals = summary.headlineRows.map((r) => Number(r.modalPrice)).filter(Number.isFinite);
        if (validModals.length === 0) return null;
        const avgModal = summary.typical;
        const belowMspCount = validModals.filter((n) => n < msp.pricePerQuintal).length;
        const diffPct = ((avgModal - msp.pricePerQuintal) / msp.pricePerQuintal) * 100;
        return { avgModal, belowMspCount, diffPct };
      })()
    : null;

  // "Explain this price" (lib/explain-price.ts) and the visible FAQ section
  // both now render inside CommodityPageClient below, since both need to
  // react to the Hindi/English toggle — see that component's own comment
  // for why. Nothing here computes them anymore; trendStats/mspStats/
  // radarEntry (all already computed above) are just passed down as props.

  // Compare tool links — same-category pairs involving this commodity (see
  // lib/compare.ts). Pure JS over the already-fetched `allCommodities`
  // list, no new query, and gives the new Compare pages at least one
  // internal inbound link per commodity from day one.
  const comparePairs = getComparePairs(allCommodities).filter(
    (p) => p.commodityA === commodity || p.commodityB === commodity
  );

  // Knowledge Graph — the category this commodity belongs to (see
  // lib/categories.ts), used both in the Product JSON-LD below and to link
  // up to the new /category/[category] hub page. "Other" is deliberately
  // excluded from CATEGORIES/hub pages, so a commodity that falls into
  // "Other" simply gets no hub link — same pattern as the homepage pills.
  const category = getCategory(commodity);
  const categorySlug = category !== "Other" ? categoryToSlug(category) : null;

  // Per-state breakdown, for the "By state" links below — this is what
  // makes each /mandi-bhav/[commodity]/[state] page discoverable by
  // crawlers (and by visitors) instead of relying on the sitemap alone.
  const byState = new Map<string, typeof rows>();
  for (const r of rows) {
    if (!byState.has(r.state)) byState.set(r.state, []);
    byState.get(r.state)!.push(r);
  }
  const stateBreakdown = [...byState.entries()]
    .map(([s, stateRows]) => {
      const st = summarizePrices(stateRows);
      return { state: s, count: st.count, lo: st.lo, hi: st.hi };
    })
    .sort((a, b) => a.state.localeCompare(b.state));

  // Hindi names for every (state, market) pair shown on this page — the
  // price table rows plus the Mandi Spread Radar's from/to markets, which
  // are themselves always drawn from `rows` (see computeRadar). Looked up
  // once, server-side, from the pre-filled market_translations cache — see
  // getMarketTranslations' comment in lib/data.ts for why this is never a
  // live translation call.
  const marketPairs = [...new Map(rows.map((r) => [`${r.state}::${r.market}`, { state: r.state, market: r.market }])).values()];
  const marketDict = await getMarketTranslations(marketPairs);

  // Structured data so search engines can parse this as pricing
  // information tied to a specific date, not just prose — Product +
  // AggregateOffer is the closest fit schema.org offers for "a range of
  // real prices for one commodity, across many sellers, on one day."
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: `${commodity} (Mandi)`,
    ...(hindiAliases.length > 0 && {
      alternateName: hindiAliases.map((a) => a.charAt(0).toUpperCase() + a.slice(1)),
    }),
    ...(categorySlug && { category }),
    description: `${commodity} mandi price across Indian APMC markets on ${dateLabel}`,
    offers: {
      "@type": "AggregateOffer",
      priceCurrency: "INR",
      lowPrice: lo,
      highPrice: hi,
      offerCount: summary.count,
      // priceValidUntil removed 4 Oct 2026 (fix33): it was set to the price
      // date itself, which is always in the past for Google → invalid offer.
    },
  };

  // FAQPage structured data — Tier A/B item from the SEO competitor-analysis
  // doc ("no confirmed competitor has robust FAQ schema here"). Every answer
  // is built from real values already computed above for this same page
  // (rows is sorted ascending by modalPrice, so rows[0]/rows[last] are the
  // genuine cheapest/priciest reporting markets today) — nothing invented.
  // Google requires FAQ rich-result content to actually be visible on the
  // page, not just present in the JSON-LD, so this also renders as a real
  // <details> section below, not a hidden-only block.
  // FAQ content for the JSON-LD is always English, regardless of what a
  // visitor's UI toggle is set to on the client (see lib/faq-commodity.ts's
  // top comment) — search engines index this markup, not the client-side
  // toggle state. The same function is called again inside
  // CommodityPageClient with the active toggle language for the visible
  // <details> section, so the two can never drift apart in content, only
  // in which language they're rendered.
  const cheapest = summary.cheapest ?? rows[rows.length - 1];
  const priciest = summary.priciest ?? rows[0];
  const faqs = buildCommodityFaqs("en", {
    commodity,
    lo,
    hi,
    rowsCount: summary.count,
    dateLabel,
    cheapest: { market: cheapest.market, state: cheapest.state, modalPrice: cheapest.modalPrice },
    priciest: { market: priciest.market, state: priciest.state, modalPrice: priciest.modalPrice },
    msp: msp ? { season: msp.season, marketingYear: msp.marketingYear, pricePerQuintal: msp.pricePerQuintal } : null,
    mspStats: mspStats ? { avgModal: mspStats.avgModal, diffPct: mspStats.diffPct } : null,
    trendStats: trendStats
      ? { days: trendStats.days, pctChange: trendStats.pctChange, windowLo: trendStats.windowLo, windowHi: trendStats.windowHi }
      : null,
  });
  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((f) => ({
      "@type": "Question",
      name: f.q,
      acceptedAnswer: { "@type": "Answer", text: f.a },
    })),
  };

  // BreadcrumbList — a real, confirmed technical-SEO gap found 21 Sep 2026
  // (no BreadcrumbList schema existed anywhere on the site until now). Gives
  // Google the Home > Commodity hierarchy for the breadcrumb rich-result
  // trail under this page's search listing.
  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: commodity, item: `${SITE_URL}/mandi-bhav/${slug}` },
    ],
  };

  return (
    <>
      {/* eslint-disable-next-line react/no-danger */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      {/* eslint-disable-next-line react/no-danger */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }} />
      {/* eslint-disable-next-line react/no-danger */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }} />

      {/* Everything a visitor actually sees renders in this Client
          Component (including the outer .wrap div) so it can carry the
          Hindi/English toggle — see components/CommodityPageClient.tsx's
          top comment. Next.js still server-renders its initial HTML, so
          this is not a client-only page: a crawler (and a JS-disabled
          visitor) sees the same English-default content as before this
          batch. */}
      <CommodityPageClient
        typical={summary.typical}
        commodity={commodity}
        slug={slug}
        dv={dv}
        hindiAlias={hindiAlias}
        dateLabel={dateLabel}
        packedRows={packRows(rows)}
        lo={lo}
        hi={hi}
        marketCount={summary.count}
        cheapest={cheapest}
        priciest={priciest}
        updatedStamp={updatedStamp}
        freshnessLabel={freshnessLabel}
        shareUrl={shareUrl}
        trendStats={trendStats}
        history={history}
        msp={msp}
        mspStats={mspStats}
        radarEntry={radarEntry}
        stateBreakdown={stateBreakdown}
        comparePairs={comparePairs}
        category={category}
        categorySlug={categorySlug}
        learnArticles={LEARN_ARTICLES.map((a) => ({ slug: a.slug, title: a.title }))}
        marketDict={marketDict}
      />
    </>
  );
}
