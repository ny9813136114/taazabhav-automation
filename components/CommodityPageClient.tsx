"use client";

// The visible body of /mandi-bhav/[commodity], split out of that route's
// page.tsx as a Client Component specifically so this page can carry the
// same Hindi/English toggle the homepage already has (components/
// HomeClient.tsx) — see lib/use-lang.ts for why the toggle is a client
// concern and lib/i18n.ts for why the dictionary is typed the way it is.
//
// What stays server-side, in page.tsx, and does NOT move here:
// generateStaticParams, generateMetadata (title/meta/canonical — English,
// unchanged), and all three JSON-LD <script> blocks (Product, FAQPage,
// BreadcrumbList — also English, unchanged). Next.js still server-renders
// a Client Component's initial HTML, so none of this is a "hide it behind
// JS" concern — a crawler sees the exact same English-default page as
// before; a real visitor with JS can additionally toggle to Hindi. Only
// the toggle-able UI chrome (labels, headings, the FAQ that's actually
// visible on the page, MSP/trend/explain-price prose) lives here.
//
// Real page DATA — commodity names, market names, prices, state names — is
// never translated, same as the homepage's toggle. Only the words around
// that data change.

import { useMemo } from "react";
import { unpackRows, type PackedRows } from "@/lib/packed-rows";
import Link from "next/link";
import type { PriceRow, RadarPair, HistoryPoint } from "@/lib/data";
import { stateToSlug } from "@/lib/slug";
import { explainPrice, type ExplainPriceLine } from "@/lib/explain-price";
import { buildCommodityFaqs } from "@/lib/faq-commodity";
import { useLang } from "@/lib/use-lang";
import { translateCategory } from "@/lib/i18n";
import { translateState } from "@/lib/states-hi";
import { longDate } from "@/lib/price-stats";
import { translateMarket, type MarketTranslationDict } from "@/lib/market-translations";
import type { Category } from "@/lib/categories";
import Sparkline from "@/components/Sparkline";
import MarketTable from "@/components/MarketTable";
import SiteFooter from "@/components/SiteFooter";
import { displayName } from "@/lib/commodity-names";
import SiteHeader from "@/components/SiteHeader";
import SellSignal from "@/components/SellSignal";
import { computeSellSignal } from "@/lib/sell-signal";
import CropHero from "@/components/CropHero";

function fmt(n: number) {
  return "₹" + Math.round(n).toLocaleString("en-IN");
}

type Msp = { season: string; marketingYear: string; pricePerQuintal: number; note?: string } | null;
type MspStats = { avgModal: number; belowMspCount: number; diffPct: number } | null;
type TrendStats = { pctChange: number; windowLo: number; windowHi: number; days: number } | null;
type StateBreakdownRow = { state: string; count: number; lo: number; hi: number };
type ComparePairRow = { pairSlug: string; commodityA: string; commodityB: string };
type LearnLink = { slug: string; title: string };

export default function CommodityPageClient({
  commodity,
  slug,
  dv,
  hindiAlias,
  dateLabel,
  packedRows,
  lo,
  hi,
  typical,
  marketCount,
  cheapest,
  priciest,
  updatedStamp,
  freshnessLabel,
  shareUrl,
  trendStats,
  history,
  msp,
  mspStats,
  radarEntry,
  stateBreakdown,
  comparePairs,
  category,
  categorySlug,
  learnArticles,
  marketDict,
}: {
  commodity: string;
  slug: string;
  dv?: string;
  hindiAlias?: string;
  dateLabel: string;
  // 3 Oct 2026 speed: rows arrive packed (lib/packed-rows.ts) and are rebuilt here.
  packedRows: PackedRows;
  lo: number;
  hi: number;
  typical: number; // median of the headline rows (summarizePrices)
  // Markets behind the headline numbers (latest date, usable rows) and the
  // real cheapest/priciest among them — from summarizePrices() on the
  // server, so the FAQ/Quick read never name a flagged row.
  marketCount: number;
  cheapest: PriceRow;
  priciest: PriceRow;
  updatedStamp: string;
  freshnessLabel: string;
  shareUrl: string;
  trendStats: TrendStats;
  history: HistoryPoint[];
  msp: Msp;
  mspStats: MspStats;
  radarEntry: RadarPair | undefined;
  stateBreakdown: StateBreakdownRow[];
  comparePairs: ComparePairRow[];
  category: Category;
  categorySlug: string | null;
  learnArticles: LearnLink[];
  marketDict: MarketTranslationDict;
}) {
  const rows = useMemo(() => unpackRows(packedRows), [packedRows]);
  const sellSignal = useMemo(
    () => computeSellSignal({ typical, latestDate: dateLabel, history, category: category, msp: msp?.pricePerQuintal ?? null }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [typical, dateLabel, history]
  );
  const [lang, setLang, t] = useLang();

  const explainLines: ExplainPriceLine[] = explainPrice(
    {
      commodity,
      trend: trendStats ? { pctChange: trendStats.pctChange, days: trendStats.days } : null,
      msp: mspStats ? { belowMspCount: mspStats.belowMspCount, totalCount: marketCount, diffPct: mspStats.diffPct } : null,
      spread: radarEntry ? { fromModal: radarEntry.from.modalPrice, toModal: radarEntry.to.modalPrice } : null,
    },
    lang
  );

  const faqs = buildCommodityFaqs(lang, {
    commodity,
    lo,
    hi,
    rowsCount: marketCount,
    dateLabel,
    cheapest: { market: cheapest.market, state: cheapest.state, modalPrice: cheapest.modalPrice },
    priciest: { market: priciest.market, state: priciest.state, modalPrice: priciest.modalPrice },
    msp: msp ? { season: msp.season, marketingYear: msp.marketingYear, pricePerQuintal: msp.pricePerQuintal } : null,
    mspStats: mspStats ? { avgModal: mspStats.avgModal, diffPct: mspStats.diffPct } : null,
    trendStats: trendStats ? { days: trendStats.days, pctChange: trendStats.pctChange, windowLo: trendStats.windowLo, windowHi: trendStats.windowHi } : null,
  });

  return (
    <div className="wrap">
      <SiteHeader lang={lang} setLang={setLang} />

      {/* Redesign Phase B (2 Oct 2026): hero price card (components/CropHero.tsx).
          The <h1> wording is unchanged (SEO). */}
      <CropHero
        commodity={commodity}
        crumbs={[
          { href: "/", label: lang === "hi" ? "होम" : "Home" },
          { href: "/", label: lang === "hi" ? "मंडी भाव" : "Mandi Bhav" },
          { label: lang === "hi" && dv ? dv : displayName(commodity) },
        ]}
        h1={<>
            {lang === "hi" ? (
              // Client-toggled Hindi state only — the server-rendered default
              // (what a crawler or JS-disabled visitor sees) is unchanged,
              // still English-primary, per the 21 Sep 2026 decision to keep
              // Hindi-first H1s off the indexed default for SEO reasons. This
              // doesn't reopen that decision: it only applies once a real
              // visitor has explicitly picked Hindi client-side.
              <>
                {dv || commodity} मंडी भाव
                <span style={{ fontWeight: 400 }}> ({displayName(commodity)})</span>
              </>
            ) : (
              <>
                {displayName(commodity)}
                {hindiAlias && <span style={{ fontWeight: 400 }}> ({hindiAlias})</span>} Mandi Bhav{" "}
                <span className="dv">{dv}</span>
              </>
            )}
</>}
        typical={typical}
        lo={lo}
        hi={hi}
        marketCount={marketCount}
        mspPrice={msp?.pricePerQuintal ?? null}
        trend={trendStats ? { pctChange: trendStats.pctChange, days: trendStats.days } : null}
        dateLabel={dateLabel}
        updatedStamp={updatedStamp}
        freshnessLabel={freshnessLabel}
        shareUrl={shareUrl}
        rangeText={<>
          {lang === "hi" ? (
            <>
              {longDate(dateLabel, "hi")} · रेंज: <span className="num">{fmt(lo)}–{fmt(hi)}</span> प्रति क्विंटल (<span className="num">{fmt(lo / 100)}–{fmt(hi / 100)}</span> प्रति किलो) — {marketCount} मंडियों में
            </>
          ) : (
            <>
              {longDate(dateLabel)} · Range: <span className="num">{fmt(lo)}–{fmt(hi)}</span> / quintal (<span className="num">{fmt(lo / 100)}–{fmt(hi / 100)}</span> / kg) across {marketCount} markets
            </>
          )}
</>}
        lang={lang}
        t={t}
        answerName={displayName(commodity)}
        answerNameHi={dv || displayName(commodity)}
      />

      {/* 3 Oct 2026: "Sell or wait?" — today vs last week / 3 weeks / MSP (lib/sell-signal.ts). */}
      {sellSignal && <SellSignal signal={sellSignal} lang={lang} slug={slug} />}

      {explainLines.length > 0 && (
        <div className="cp-quick">
          <b>{t("quickRead")}</b>
          {explainLines.map((line, i) => (
            <p key={i} className={`tone-${line.tone}`}>
              {line.text}
            </p>
          ))}
        </div>
      )}

      <h2 className="cp-sec-title">{lang === "hi" ? "मंडी के अनुसार भाव" : "Prices by mandi"}</h2>
      <MarketTable
        csvName={`${slug}-mandi-bhav`}
        rows={rows}
        lang={lang}
        t={t}
        marketDict={marketDict}
        latestDate={dateLabel}
        lo={lo}
        hi={hi}
        showStateFilter={true}
      />

      {trendStats && (
        <div className="slip-section">
          <div className="slip-heading">
            <h2 style={{ fontSize: "1.1rem" }}>
              {lang === "hi" ? `${trendStats.days}-दिन का रुख` : `${trendStats.days}-day trend`}
            </h2>
          </div>
          <div className="slip" style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
            <Sparkline data={history} />
            <p style={{ fontSize: ".88rem", lineHeight: 1.6, margin: 0 }}>
              {lang === "hi" ? (
                <>
                  {t("avgMandiRateIs")}{" "}
                  <span style={{ color: trendStats.pctChange >= 0 ? "var(--up)" : "var(--down)", fontWeight: 700 }}>
                    {trendStats.pctChange >= 0 ? "+" : ""}{trendStats.pctChange.toFixed(1)}%
                  </span>{" "}
                  पिछले {trendStats.days} दिनों में जिनका डेटा उपलब्ध है — इस दौरान {t("rangingLabel")}{" "}
                  <span className="num">{fmt(trendStats.windowLo)}–{fmt(trendStats.windowHi)}</span> {t("perQuintal")}।
                </>
              ) : (
                <>
                  {t("avgMandiRateIs")}{" "}
                  <span style={{ color: trendStats.pctChange >= 0 ? "var(--up)" : "var(--down)", fontWeight: 700 }}>
                    {trendStats.pctChange >= 0 ? "+" : ""}{trendStats.pctChange.toFixed(1)}%
                  </span>{" "}
                  over the last {trendStats.days} days it has data for — {t("rangingLabel")}{" "}
                  <span className="num">{fmt(trendStats.windowLo)}–{fmt(trendStats.windowHi)}</span> {t("perQuintal")}.
                </>
              )}
            </p>
          </div>
          <p style={{ fontSize: ".76rem", color: "var(--ink-faint)", marginTop: 8 }}>{t("freeHistoryNote")}</p>
        </div>
      )}

      {msp && mspStats && (
        <div className="slip-section">
          <div className="slip-heading">
            <h2 style={{ fontSize: "1.1rem" }}>{t("mspCheckHeading")}</h2>
          </div>
          <div className="slip">
            <p style={{ fontSize: ".88rem", lineHeight: 1.6, margin: 0 }}>
              {t("govtMsp")} ({msp.season} {msp.marketingYear}):{" "}
              <span className="num" style={{ fontWeight: 700 }}>{fmt(msp.pricePerQuintal)}</span> / {lang === "hi" ? "क्विंटल" : "quintal"}.{" "}
              {t("todaysAvgRateIs")}{" "}
              <span className="num" style={{ fontWeight: 700 }}>{fmt(mspStats.avgModal)}</span>
              {lang === "hi" ? ", जो " : ", which is "}
              <span style={{ color: mspStats.diffPct >= 0 ? "var(--up)" : "var(--down)", fontWeight: 700 }}>
                {mspStats.diffPct >= 0 ? "+" : ""}{mspStats.diffPct.toFixed(1)}% {mspStats.diffPct >= 0 ? t("aboveMsp") : t("belowMsp")}
              </span>
              {mspStats.belowMspCount > 0 && (
                <>
                  {" "}· <span style={{ color: "var(--down)" }}>
                    {lang === "hi"
                      ? `${marketCount} में से ${mspStats.belowMspCount} मंडियां`
                      : `${mspStats.belowMspCount} of ${marketCount} markets`}
                  </span>{" "}
                  {t("areTradingBelowMspToday")}
                </>
              )}
              .
              {msp.note && (
                <>
                  <br />
                  <span style={{ color: "var(--ink-faint)", fontSize: ".78rem" }}>{msp.note}</span>
                </>
              )}
            </p>
            <p style={{ marginTop: 10, fontSize: ".82rem" }}>
              <Link href={`/mandi-bhav/${slug}/msp-comparison`} style={{ color: "var(--ink-soft)", borderBottom: "1px dotted var(--ink-faint)" }}>
                {t("seeFullBelowMspBreakdown")}
              </Link>
            </p>
          </div>
        </div>
      )}

      {!msp && (
        <div className="slip-section">
          <div className="slip-heading">
            <h2 style={{ fontSize: "1.1rem" }}>{t("mspCheckHeading")}</h2>
          </div>
          <div className="slip">
            <p style={{ fontSize: ".85rem", color: "var(--ink-soft)", lineHeight: 1.6, margin: 0 }}>
              {lang === "hi" ? (
                <>
                  {commodity} सरकार की एमएसपी योजना में शामिल नहीं है — एमएसपी केवल लगभग दो दर्जन तय अनाज, दालों,
                  तिलहन और नकदी फ़सलों (गेहूं, धान, कपास और इस तरह की फ़सलों) पर लागू होती है। इस तरह की जल्दी
                  ख़राब होने वाली उपज का भाव पूरी तरह मंडी की मांग और आपूर्ति से तय होता है।
                </>
              ) : (
                <>
                  {commodity} isn&apos;t covered by the government&apos;s MSP scheme — MSP applies to a fixed list of
                  roughly two dozen cereals, pulses, oilseeds and commercial crops (wheat, paddy, cotton and similar).
                  Perishable produce like this is priced entirely by mandi demand and supply.
                </>
              )}
            </p>
          </div>
        </div>
      )}

      {radarEntry && (
        <div className="slip-section">
          <div className="slip-heading">
            <h2 style={{ fontSize: "1.1rem" }}>{t("widestSpreadToday")}</h2>
          </div>
          <div className="slip">
            <div className="radar-card" style={{ borderLeft: "3px solid var(--gold-ink)", paddingLeft: 14 }}>
              <div className="rc-route">
                {translateMarket(lang, radarEntry.from.state, radarEntry.from.market, marketDict)}, {translateState(lang, radarEntry.from.state)} <b>{fmt(radarEntry.from.modalPrice)}</b> →{" "}
                {translateMarket(lang, radarEntry.to.state, radarEntry.to.market, marketDict)}, {translateState(lang, radarEntry.to.state)} <b>{fmt(radarEntry.to.modalPrice)}</b>
              </div>
              <div className="rc-spread">
                +{fmt(radarEntry.to.modalPrice - radarEntry.from.modalPrice)} / {lang === "hi" ? "क्विंटल" : "quintal"}
              </div>
            </div>
          </div>
        </div>
      )}

      {stateBreakdown.length > 1 && (
        <div className="slip-section">
          <div className="slip-heading">
            <h2 style={{ fontSize: "1.1rem" }}>
              {lang === "hi" ? `राज्य के अनुसार ${commodity}` : `${commodity} by state`}
            </h2>
          </div>
          <div className="slip" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "10px 20px" }}>
            {stateBreakdown.map((s) => (
              <Link
                key={s.state}
                href={`/mandi-bhav/${slug}/${stateToSlug(s.state)}`}
                style={{ color: "var(--ink)", fontSize: ".85rem", borderBottom: "1px dotted var(--ink-faint)", paddingBottom: 4 }}
              >
                {translateState(lang, s.state)}{" "}
                <span className="num" style={{ color: "var(--ink-soft)" }}>
                  {fmt(s.lo)}–{fmt(s.hi)}
                </span>{" "}
                <span style={{ color: "var(--ink-faint)", fontSize: ".72rem" }}>({s.count})</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {comparePairs.length > 0 && (
        <div className="slip-section">
          <div className="slip-heading">
            <h2 style={{ fontSize: "1.1rem" }}>
              {lang === "hi" ? `${commodity} की तुलना करें` : `Compare ${commodity} with`}
            </h2>
          </div>
          <div className="slip" style={{ display: "flex", flexWrap: "wrap", gap: "8px 16px" }}>
            {comparePairs.map((p) => {
              const other = p.commodityA === commodity ? p.commodityB : p.commodityA;
              return (
                <Link
                  key={p.pairSlug}
                  href={`/compare/${p.pairSlug}`}
                  style={{ fontSize: ".85rem", color: "var(--ink)", borderBottom: "1px dotted var(--ink-faint)" }}
                >
                  {other} →
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {(categorySlug || learnArticles.length > 0) && (
        <div className="slip-section">
          <div className="slip-heading">
            <h2 style={{ fontSize: "1.1rem" }}>{t("learnMoreHeading")}</h2>
          </div>
          <div className="slip" style={{ display: "flex", flexWrap: "wrap", gap: "8px 16px" }}>
            {categorySlug && (
              <Link
                href={`/category/${categorySlug}`}
                style={{ fontSize: ".85rem", color: "var(--ink)", borderBottom: "1px dotted var(--ink-faint)" }}
              >
                {lang === "hi"
                  ? `सभी ${translateCategory(lang, category)} मंडी भाव →`
                  : `All ${category} mandi bhav →`}
              </Link>
            )}
            {learnArticles.map((a) => (
              <Link
                key={a.slug}
                href={`/learn/${a.slug}`}
                style={{ fontSize: ".85rem", color: "var(--ink)", borderBottom: "1px dotted var(--ink-faint)" }}
              >
                {a.title} →
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="slip-section">
        <div className="slip-heading">
          <h2 style={{ fontSize: "1.1rem" }}>{t("faqHeading")}</h2>
        </div>
        <div className="slip">
          {faqs.map((f) => (
            <details key={f.q} style={{ padding: "10px 0", borderBottom: "1px solid var(--paper-line)" }}>
              <summary style={{ cursor: "pointer", fontWeight: 600, fontSize: ".88rem" }}>{f.q}</summary>
              <p style={{ fontSize: ".85rem", color: "var(--ink-soft)", lineHeight: 1.6, marginTop: 8, marginBottom: 0 }}>
                {f.a}
              </p>
            </details>
          ))}
        </div>
      </div>

      <p style={{ marginTop: 40, fontSize: ".85rem" }}>
        <Link href={`/#sahi-daam/${slug}`} style={{ color: "var(--ink-soft)" }}>
          {lang === "hi"
            ? `सही दाम कैलकुलेटर से ${commodity} की असली लागत जानें →`
            : `Work out the true landing cost for ${commodity} with the Sahi Daam calculator →`}
        </Link>
      </p>

      <SiteFooter lang={lang} />
    </div>
  );
}
