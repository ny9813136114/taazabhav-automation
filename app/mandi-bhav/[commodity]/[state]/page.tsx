import { packRows } from "@/lib/packed-rows";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getAllCommodities, getPricesForCommodityInState, getRecentStatesForCommodity, getCommodityStatePairs, getCommodityHistory, getMarketTranslations } from "@/lib/data";
import { summarizePrices, longDate, shortDate, byDateThenPrice } from "@/lib/price-stats";
import type { PriceRow } from "@/lib/data";
import { commodityToSlug, slugToCommodity, stateToSlug, slugToState } from "@/lib/slug";
import { getMsp } from "@/lib/msp";
import { timeAgo, formatUpdatedStamp } from "@/lib/time";
import { getPrimaryHindiAlias, getHindiAliases } from "@/lib/aliases";
import { buildCommodityStateFaqs } from "@/lib/faq-commodity-state";
import CommodityStatePageClient from "@/components/CommodityStatePageClient";
import { translate } from "@/lib/i18n";
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

// One static page per (commodity, state) pair that actually has data —
// e.g. /mandi-bhav/onion/maharashtra. This is the next layer down from
// the commodity-only pages: it's what lets a search for "onion price in
// maharashtra today" land on an exact page instead of the commodity page
// (which mixes every state together) or the homepage.
// Build-speed / egress fix (24 Sep 2026): these used to be pre-rendered at
// EVERY deploy — one page (and its database queries) per pair. Once the
// tracked list grew from ~31 to ~71 commodities that meant well over a
// thousand pages per build, taking deploys from ~2 to ~15 minutes and
// re-reading the database for every page on every deploy. Now none are
// built up front: each page renders on its first real visit and is then
// cached for `revalidate` seconds (on-demand ISR). The URLs are unchanged
// and still listed in sitemap.xml; dynamicParams (default true) lets any
// valid pair render, and invalid ones still 404 via notFound().
export async function generateStaticParams() {
  return [];
}

async function resolveParams(commoditySlug: string, stateSlug: string) {
  const allCommodities = await getAllCommodities();
  const commodity = slugToCommodity(commoditySlug, allCommodities);
  if (!commodity) {
    return { commodity: undefined, state: undefined, commodityRows: [] as PriceRow[], rows: [] as PriceRow[] };
  }

  // Scoped to this one commodity at the database level — see
  // getPricesForCommodity's comment in lib/data.ts. commodityRows also
  // covers what used to need the full cross-commodity table: the "other
  // states" cross-links below only ever needed this commodity's rows.
  // Egress fix (24 Sep 2026): only state NAMES here, and only this state's
  // rows below — see getPricesForCommodityInState in lib/data.ts.
  const statesForCommodity = await getRecentStatesForCommodity(commodity);
  const commodityRows: PriceRow[] = [];
  const state = slugToState(stateSlug, statesForCommodity);
  if (!state) {
    // Batch 2 (24 Sep 2026): since Batch 1 limited "current" rows to the
    // last 14 days, a state that traded this crop before but hasn't
    // reported recently used to hit notFound() — a 404 on a URL that's in
    // the sitemap and may already be indexed. If the pair exists in history,
    // return it as `staleState` so the page can say so honestly instead.
    const pairs = await getCommodityStatePairs();
    const historicState = slugToState(
      stateSlug,
      pairs.filter((p) => p.commodity === commodity).map((p) => p.state)
    );
    return { commodity, state: undefined, staleState: historicState, commodityRows, rows: [] as PriceRow[] };
  }

  // Highest price first (sellers' view). `unusual` flags were computed
  // against the NATIONAL median in lib/data.ts, so this page and the
  // commodity page always agree on which rows are odd.
  const rows = [...(await getPricesForCommodityInState(commodity, state))].sort(byDateThenPrice);

  return { commodity, state, commodityRows, statesForCommodity, rows };
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ commodity: string; state: string }>;
}): Promise<Metadata> {
  const { commodity: commoditySlug, state: stateSlug } = await params;
  const { commodity, state, staleState, rows } = await resolveParams(commoditySlug, stateSlug);
  if (commodity && staleState) {
    // Thin, temporary page — keep it out of the index until data returns,
    // but let crawlers follow its links. Canonical stays the same URL.
    return {
      title: `${commodity} Price in ${staleState} — No Recent Mandi Report`,
      robots: { index: false, follow: true },
      alternates: { canonical: `/mandi-bhav/${commoditySlug}/${stateSlug}` },
    };
  }
  if (!commodity || !state || rows.length === 0) return {};

  // See lib/price-stats.ts — dateLabel used to be rows[0]?.priceDate (the
  // cheapest row's date), which is how this page's title said 2026-09-23
  // while showing 24 Sep prices.
  const summary = summarizePrices(rows);
  const { lo, hi } = summary;
  const dateLabel = summary.latestDate;

  // Romanized Hindi alias ("Pyaj" for "Onion") pushed into the title/meta —
  // see lib/aliases.ts.
  const hindiAlias = getPrimaryHindiAlias(commodity);
  // Devanagari name too ("प्याज़") — most Hindi searches are typed in
  // Devanagari, and the title is what Google matches first.
  const dv = rows.find((r) => r.dv)?.dv;
  const aliasParts = [hindiAlias, dv].filter(Boolean);
  const aliasSuffix = aliasParts.length ? ` (${aliasParts.join(" / ")})` : "";

  // No trailing "| TaazaBhav" here — app/layout.tsx's title template
  // ("%s | TaazaBhav") already appends it to every page automatically.
  // Near Google's ~60-character title limit: Devanagari name only (the
  // romanized alias stays in the description), date without the year.
  const titleName = dv ? `${commodity} (${dv})` : commodity;
  const title = `${titleName} Mandi Bhav in ${state} Today, ${shortDate(dateLabel)}`;
  const description = `${commodity}${aliasSuffix} mandi rate in ${state} today: ₹${lo}–₹${hi} per quintal (₹${Math.round(lo / 100)}–₹${Math.round(hi / 100)}/kg) across ${summary.count} APMC markets, sourced live from Agmarknet. Updated 3× daily.`;
  const path = `/mandi-bhav/${commoditySlug}/${stateSlug}`;

  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { images: OG_IMAGES, title, description, url: path },
  };
}

export default async function CommodityStatePage({
  params,
}: {
  params: Promise<{ commodity: string; state: string }>;
}) {
  const { commodity: commoditySlug, state: stateSlug } = await params;
  const { commodity, state, staleState, statesForCommodity, rows } = await resolveParams(commoditySlug, stateSlug);
  if (commodity && staleState) {
    // Server-rendered, both languages shown together — this rare page
    // doesn't need the client toggle.
    return (
      <div className="wrap" style={{ padding: "40px 0" }}>
        <p style={{ fontSize: ".8rem" }}>
          <a href="/">TaazaBhav</a> › <a href={`/mandi-bhav/${commoditySlug}`}>{commodity}</a> › {staleState}
        </p>
        <h1 style={{ fontSize: "1.5rem", marginTop: 12 }}>
          {commodity} — {staleState}
        </h1>
        <p style={{ marginTop: 12 }}>
          <b>{translate("en", "noRecentTitle")}</b>
          <br />
          {translate("en", "noRecentBody")}
        </p>
        <p style={{ marginTop: 12 }} lang="hi">
          <b>{translate("hi", "noRecentTitle")}</b>
          <br />
          {translate("hi", "noRecentBody")}
        </p>
        <p style={{ marginTop: 20 }}>
          <a href={`/mandi-bhav/${commoditySlug}`}>{translate("en", "noRecentCta")}</a>
          {" · "}
          <a href={`/mandi-bhav/state/${stateSlug}`}>{staleState} mandi bhav →</a>
        </p>
      </div>
    );
  }
  if (!commodity || !state || rows.length === 0) notFound();

  const summary = summarizePrices(rows);
  const { lo, hi } = summary;
  const dv = rows[0]?.dv;
  const dateLabel = summary.latestDate;
  const latestFetchedAt = rows.reduce((max, r) => (r.fetchedAt > max ? r.fetchedAt : max), "");
  const freshnessLabel = latestFetchedAt ? timeAgo(latestFetchedAt) : "";
  const updatedStamp = latestFetchedAt ? formatUpdatedStamp(latestFetchedAt) : "";

  // Romanized Hindi alias(es) — see lib/aliases.ts. hindiAlias is the single
  // most-common spelling for the H1; hindiAliases is the full list for the
  // JSON-LD alternateName.
  const hindiAlias = getPrimaryHindiAlias(commodity);
  const hindiAliases = getHindiAliases(commodity);

  // Plain wa.me deep link — see the commodity-only page's comment for why
  // this needs no API/app integration.
  const shareText = `${commodity} Mandi Bhav in ${state} — ${longDate(dateLabel)}: typical ${fmt(summary.typical)} / quintal (range ${fmt(lo)}–${fmt(hi)}) across ${summary.count} markets. Full list: ${SITE_URL}/mandi-bhav/${commoditySlug}/${stateSlug}`;
  const shareUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;

  // Other states this same commodity trades in — cross-links so a visitor
  // (and a crawler) can move sideways between states without going back
  // through the commodity page every time.
  const otherStates = [...(statesForCommodity ?? [])]
    .filter((s) => s !== state)
    .sort();

  // Hindi names for every market shown on this page — see
  // getMarketTranslations' comment in lib/data.ts. All rows here are
  // already scoped to `state`, so every pair shares the same state string.
  const marketPairs = [...new Set(rows.map((r) => r.market))].map((market) => ({ state, market }));
  const marketDict = await getMarketTranslations(marketPairs);

  // 21-day price trend, scoped to this state only.
  const history = await getCommodityHistory(commodity, 21, state);
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

  // MSP comparison, scoped to this state's markets only — see
  // lib/msp.ts for which crops carry a government MSP at all.
  const msp = getMsp(commodity);
  const mspStats = msp
    ? (() => {
        // modalPrice is typed as `number`, but Postgres NUMERIC columns
        // come back through the `pg` driver as strings — Number() guards
        // against "+" silently string-concatenating instead of summing.
        // Also drop any row whose price doesn't parse at all (a bad/missing
        // value) rather than letting a single bad entry NaN the average.
        // Typical (median) price and below-MSP count over the same headline
        // markets the hero line counts — see lib/price-stats.ts.
        const validModals = summary.headlineRows.map((r) => Number(r.modalPrice)).filter(Number.isFinite);
        if (validModals.length === 0) return null;
        const avgModal = summary.typical;
        const belowMspCount = validModals.filter((n) => n < msp.pricePerQuintal).length;
        const diffPct = ((avgModal - msp.pricePerQuintal) / msp.pricePerQuintal) * 100;
        return { avgModal, belowMspCount, diffPct };
      })()
    : null;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: `${commodity} (Mandi, ${state})`,
    ...(hindiAliases.length > 0 && {
      alternateName: hindiAliases.map((a) => a.charAt(0).toUpperCase() + a.slice(1)),
    }),
    description: `${commodity} mandi price in ${state}, India on ${dateLabel}`,
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

  // FAQPage structured data — English, server-side, unchanged. Built via
  // the shared lib/faq-commodity-state.ts (lang: "en") so the crawlable
  // JSON-LD and the visible bilingual FAQ section (built client-side in
  // CommodityStatePageClient with the same function) can never drift out
  // of sync — same pattern as the commodity-only page's lib/faq-commodity.ts.
  const cheapest = summary.cheapest ?? rows[rows.length - 1];
  const priciest = summary.priciest ?? rows[0];
  const faqs = buildCommodityStateFaqs("en", {
    commodity,
    state,
    lo,
    hi,
    rowsCount: summary.count,
    dateLabel,
    cheapest: { market: cheapest.market, modalPrice: cheapest.modalPrice },
    priciest: { market: priciest.market, modalPrice: priciest.modalPrice },
    msp: msp ? { season: msp.season, marketingYear: msp.marketingYear, pricePerQuintal: msp.pricePerQuintal } : null,
    mspStats: mspStats ? { avgModal: mspStats.avgModal, diffPct: mspStats.diffPct } : null,
    trendStats: trendStats ? { days: trendStats.days, pctChange: trendStats.pctChange, windowLo: trendStats.windowLo, windowHi: trendStats.windowHi } : null,
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

  // BreadcrumbList — same Tier B/technical-SEO fix as the commodity-only
  // page (see its comment). This one has the full 3-level trail.
  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: commodity, item: `${SITE_URL}/mandi-bhav/${commoditySlug}` },
      {
        "@type": "ListItem",
        position: 3,
        name: state,
        item: `${SITE_URL}/mandi-bhav/${commoditySlug}/${stateSlug}`,
      },
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
      <CommodityStatePageClient
        typical={summary.typical}
        commodity={commodity}
        commoditySlug={commoditySlug}
        state={state}
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
        otherStates={otherStates}
        marketDict={marketDict}
      />
    </>
  );
}
