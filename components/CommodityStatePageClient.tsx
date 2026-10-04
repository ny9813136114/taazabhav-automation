"use client";

// Visible body of /mandi-bhav/[commodity]/[state] — same split as
// components/CommodityPageClient.tsx (see that file's comment for the full
// reasoning: what stays server-side in page.tsx — generateStaticParams,
// generateMetadata, all three JSON-LD blocks — vs. what moves here, and why
// real page DATA (commodity/market/state names) is never translated, only
// the UI chrome and prose around it). This is the state-scoped sibling: the
// same page type, but every heading/sentence that used to say "today"
// bilingual now also carries "{state}" bilingual, and price rows aren't
// re-tagged with a state span since they're already filtered to one state.

import { useMemo } from "react";
import { unpackRows, type PackedRows } from "@/lib/packed-rows";
import Link from "next/link";
import type { PriceRow, HistoryPoint } from "@/lib/data";
import { stateToSlug } from "@/lib/slug";
import { buildCommodityStateFaqs } from "@/lib/faq-commodity-state";
import { useLang } from "@/lib/use-lang";
import { translateState } from "@/lib/states-hi";
import { longDate } from "@/lib/price-stats";
import { translateMarket, type MarketTranslationDict } from "@/lib/market-translations";
import Sparkline from "@/components/Sparkline";
import MarketTable from "@/components/MarketTable";
import SellSignal from "@/components/SellSignal";
import { computeSellSignal } from "@/lib/sell-signal";
import { getCategory } from "@/lib/categories";
import CropHero from "@/components/CropHero";
import SiteFooter from "@/components/SiteFooter";
import { displayName } from "@/lib/commodity-names";
import SiteHeader from "@/components/SiteHeader";

function fmt(n: number) {
  return "₹" + Math.round(n).toLocaleString("en-IN");
}

type Msp = { season: string; marketingYear: string; pricePerQuintal: number; note?: string } | null;
type MspStats = { avgModal: number; belowMspCount: number; diffPct: number } | null;
type TrendStats = { pctChange: number; windowLo: number; windowHi: number; days: number } | null;

export default function CommodityStatePageClient({
  commodity,
  commoditySlug,
  state,
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
  otherStates,
  marketDict,
}: {
  commodity: string;
  commoditySlug: string;
  state: string;
  dv?: string;
  hindiAlias?: string;
  dateLabel: string;
  // 3 Oct 2026 speed: rows arrive packed (lib/packed-rows.ts) and are rebuilt here.
  packedRows: PackedRows;
  lo: number;
  hi: number;
  typical: number;
  // From summarizePrices() on the server — see CommodityPageClient.
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
  otherStates: string[];
  marketDict: MarketTranslationDict;
}) {
  const rows = useMemo(() => unpackRows(packedRows), [packedRows]);
  const sellSignal = useMemo(
    () => computeSellSignal({ typical, latestDate: dateLabel, history, category: getCategory(commodity), msp: msp?.pricePerQuintal ?? null }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [typical, dateLabel, history]
  );
  const [lang, setLang, t] = useLang();
  const stateT = translateState(lang, state);

  const faqs = buildCommodityStateFaqs(lang, {
    commodity,
    state,
    lo,
    hi,
    rowsCount: marketCount,
    dateLabel,
    cheapest: { market: cheapest.market, modalPrice: cheapest.modalPrice },
    priciest: { market: priciest.market, modalPrice: priciest.modalPrice },
    msp: msp ? { season: msp.season, marketingYear: msp.marketingYear, pricePerQuintal: msp.pricePerQuintal } : null,
    mspStats: mspStats ? { avgModal: mspStats.avgModal, diffPct: mspStats.diffPct } : null,
    trendStats: trendStats ? { days: trendStats.days, pctChange: trendStats.pctChange, windowLo: trendStats.windowLo, windowHi: trendStats.windowHi } : null,
  });

  return (
    <div className="wrap">
      <SiteHeader lang={lang} setLang={setLang} />

      {/* Redesign Phase B (2 Oct 2026): shared hero price card. */}
      <CropHero
        commodity={commodity}
        crumbs={[
          { href: "/", label: lang === "hi" ? "होम" : "Home" },
          { href: `/mandi-bhav/${commoditySlug}`, label: lang === "hi" && dv ? dv : displayName(commodity) },
          { label: stateT },
        ]}
        h1={<>
          {lang === "hi" ? (
            // Client-toggled only — server-rendered default stays
            // English-primary, same SEO reasoning as CommodityPageClient's H1.
            <>
              {dv || commodity} मंडी भाव {stateT} में
              <span style={{ fontWeight: 400 }}> ({displayName(commodity)})</span>
            </>
          ) : (
            <>
              {displayName(commodity)}
              {hindiAlias && <span style={{ fontWeight: 400 }}> ({hindiAlias})</span>} Mandi Bhav in {state}{" "}
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
              {longDate(dateLabel, "hi")} · रेंज:{" "}
              <span className="num">{fmt(lo)}–{fmt(hi)}</span> प्रति क्विंटल (
              <span className="num">{fmt(lo / 100)}–{fmt(hi / 100)}</span> प्रति किलो) — {stateT} की {marketCount} मंडियों में
            </>
          ) : (
            <>
              {longDate(dateLabel)} · Range:{" "}
              <span className="num">{fmt(lo)}–{fmt(hi)}</span> / quintal (
              <span className="num">{fmt(lo / 100)}–{fmt(hi / 100)}</span> / kg) across {marketCount} {state} markets
            </>
          )}
</>}
        lang={lang}
        t={t}
        answerName={displayName(commodity)}
        answerNameHi={dv || displayName(commodity)}
        place={state}
        placeHi={stateT}
      />

      {/* 3 Oct 2026: "Sell or wait?" for this state (lib/sell-signal.ts). */}
      {sellSignal && <SellSignal signal={sellSignal} lang={lang} slug={commoditySlug} />}
      <h2 className="cp-sec-title">{lang === "hi" ? `${stateT} की मंडियों के भाव` : `Prices by mandi in ${state}`}</h2>

      <MarketTable
        csvName={`${commoditySlug}-${stateToSlug(state)}-mandi-bhav`}
        rows={rows}
        lang={lang}
        t={t}
        marketDict={marketDict}
        latestDate={dateLabel}
        lo={lo}
        hi={hi}
        showStateFilter={false}
      />

      {trendStats && (
        <div className="slip-section">
          <div className="slip-heading">
            <h2 style={{ fontSize: "1.1rem" }}>
              {lang === "hi" ? `${stateT} में ${trendStats.days}-दिन का रुख` : `${trendStats.days}-day trend in ${state}`}
            </h2>
          </div>
          <div className="slip" style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
            <Sparkline data={history} />
            <p style={{ fontSize: ".88rem", lineHeight: 1.6, margin: 0 }}>
              {lang === "hi" ? (
                <>
                  {stateT} में {t("avgMandiRateIs")}{" "}
                  <span style={{ color: trendStats.pctChange >= 0 ? "var(--up)" : "var(--down)", fontWeight: 700 }}>
                    {trendStats.pctChange >= 0 ? "+" : ""}{trendStats.pctChange.toFixed(1)}%
                  </span>{" "}
                  पिछले {trendStats.days} दिनों में जिनका डेटा उपलब्ध है — इस दौरान {t("rangingLabel")}{" "}
                  <span className="num">{fmt(trendStats.windowLo)}–{fmt(trendStats.windowHi)}</span> {t("perQuintal")}।
                </>
              ) : (
                <>
                  Typical mandi rate in {state} is{" "}
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
              {lang === "hi" ? (
                <>{stateT} में आज का औसत भाव </>
              ) : (
                <>{t("todaysAvgRateIs")} in {state} is </>
              )}
              <span className="num" style={{ fontWeight: 700 }}>{fmt(mspStats.avgModal)}</span>
              {lang === "hi" ? " है, जो " : ", which is "}
              <span style={{ color: mspStats.diffPct >= 0 ? "var(--up)" : "var(--down)", fontWeight: 700 }}>
                {mspStats.diffPct >= 0 ? "+" : ""}{mspStats.diffPct.toFixed(1)}% {mspStats.diffPct >= 0 ? t("aboveMsp") : t("belowMsp")}
              </span>
              {mspStats.belowMspCount > 0 && (
                <>
                  {" "}· <span style={{ color: "var(--down)" }}>
                    {lang === "hi"
                      ? `${marketCount} में से ${mspStats.belowMspCount} ${stateT} मंडियां`
                      : `${mspStats.belowMspCount} of ${marketCount} ${state} markets`}
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

      {otherStates.length > 0 && (
        <div className="slip-section">
          <div className="slip-heading">
            <h2 style={{ fontSize: "1.1rem" }}>
              {lang === "hi" ? `${commodity} अन्य राज्यों में` : `${commodity} in other states`}
            </h2>
          </div>
          <div className="slip" style={{ display: "flex", flexWrap: "wrap", gap: "8px 16px" }}>
            {otherStates.map((s) => (
              <Link
                key={s}
                href={`/mandi-bhav/${commoditySlug}/${stateToSlug(s)}`}
                style={{ fontSize: ".85rem", color: "var(--ink)", borderBottom: "1px dotted var(--ink-faint)" }}
              >
                {translateState(lang, s)}
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
        <Link href={`/mandi-bhav/${commoditySlug}`} style={{ color: "var(--ink-soft)" }}>
          {lang === "hi" ? `← सभी राज्यों में ${commodity} मंडी भाव` : `← All-India ${commodity} mandi bhav`}
        </Link>
        {" · "}
        <Link href={`/#sahi-daam/${commoditySlug}`} style={{ color: "var(--ink-soft)" }}>
          {lang === "hi"
            ? `सही दाम कैलकुलेटर से असली लागत जानें →`
            : `Work out the true landing cost with the Sahi Daam calculator →`}
        </Link>
      </p>

      <SiteFooter lang={lang} />
    </div>
  );
}
