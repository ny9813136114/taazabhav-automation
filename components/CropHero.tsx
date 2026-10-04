"use client";

// Shared hero price card for crop pages (Redesign Phase B, 2 Oct 2026):
// /mandi-bhav/[crop] and /mandi-bhav/[crop]/[state]. Typical price first,
// then lowest/highest/markets/MSP, freshness + source, and quick actions.
// The <h1> is passed in by the page so its SEO wording stays unchanged.

import Link from "next/link";
import type { ReactNode } from "react";
import type { Lang, UIKey } from "@/lib/i18n";
import { longDate } from "@/lib/price-stats";
import { cropIcon } from "@/lib/crop-icon";
import { commodityToSlug } from "@/lib/slug";
import KhetPromo from "@/components/KhetPromo";

function fmt(n: number) {
  return "₹" + Math.round(n).toLocaleString("en-IN");
}

export default function CropHero({
  commodity,
  crumbs,
  h1,
  typical,
  lo,
  hi,
  marketCount,
  mspPrice,
  trend,
  dateLabel,
  updatedStamp,
  freshnessLabel,
  shareUrl,
  rangeText,
  lang,
  t,
  answerName,
  answerNameHi,
  place,
  placeHi,
}: {
  commodity: string;
  crumbs: { href?: string; label: string }[];
  h1: ReactNode;
  typical: number;
  lo: number;
  hi: number;
  marketCount: number;
  mspPrice?: number | null;
  trend: { pctChange: number; days: number } | null;
  dateLabel: string;
  updatedStamp: string;
  freshnessLabel: string;
  shareUrl: string;
  rangeText: ReactNode;
  lang: Lang;
  t: (k: UIKey) => string;
  // fix33 (4 Oct 2026, GEO): one plain sentence with the answer, right under
  // the H1 — Google snippets and AI assistants quote sentences, not tiles.
  answerName?: string;
  answerNameHi?: string;
  place?: string;
  placeHi?: string;
}) {
  const hiLang = lang === "hi";
  const nameEn = answerName ?? commodity;
  const answer = hiLang
    ? `${answerNameHi ?? nameEn}${placeHi ? ` (${placeHi})` : ""} मंडी भाव, ${longDate(dateLabel, "hi")}: आम भाव ${fmt(typical)} प्रति क्विंटल (${fmt(typical / 100)}/किलो); सबसे कम ${fmt(lo)}, सबसे ज़्यादा ${fmt(hi)} — ${marketCount} मंडियों में।`
    : `${nameEn} mandi bhav${place ? ` in ${place}` : ""}, ${longDate(dateLabel)}: typical ${fmt(typical)} per quintal (${fmt(typical / 100)}/kg); lowest ${fmt(lo)}, highest ${fmt(hi)} across ${marketCount} mandis.`;
  return (
    <>
      <nav className="cp-crumb" aria-label="Breadcrumb">
        {crumbs.map((c, i) => (
          <span key={i}>
            {i > 0 && " › "}
            {c.href ? <Link href={c.href}>{c.label}</Link> : <span>{c.label}</span>}
          </span>
        ))}
      </nav>
      <section className="cp-hero">
        <div className="cp-top">
          <span className="cp-ico" aria-hidden="true">{cropIcon(commodity)}</span>
          <h1 className="cp-h1">{h1}</h1>
        </div>
        <p className="cp-answer" style={{ gridColumn: "1 / -1", margin: "2px 0 6px", fontSize: ".95rem", lineHeight: 1.45, color: "var(--ink-soft)" }}>
          {answer}
        </p>
        <div className="cp-price">
          <div>
            <small>{hiLang ? "आम भाव (मॉडल)" : "Typical price (modal)"}</small>
            <b className="num">{fmt(typical)}</b>
            <small>
              /{hiLang ? "क्विंटल" : "quintal"} · {fmt(typical / 100)}/{hiLang ? "किलो" : "kg"}
            </small>
          </div>
          {trend && (
            <span className={`cp-trend ${trend.pctChange >= 0 ? "up" : "down"}`}>
              {trend.pctChange >= 0 ? "↑ +" : "↓ −"}
              {Math.abs(trend.pctChange).toFixed(1)}%
              <small>{hiLang ? `${trend.days} दिन में` : `in ${trend.days} days`}</small>
            </span>
          )}
        </div>
        <div className="cp-stats">
          <div><small>{hiLang ? "न्यूनतम" : "Lowest"}</small><b className="num">{fmt(lo)}</b></div>
          <div><small>{hiLang ? "अधिकतम" : "Highest"}</small><b className="num">{fmt(hi)}</b></div>
          <div><small>{hiLang ? "मंडियां" : "Markets"}</small><b className="num">{marketCount}</b></div>
          {mspPrice ? <div><small>MSP</small><b className="num">{fmt(mspPrice)}</b></div> : null}
        </div>
        <p className="cp-fresh">
          <span className="sh-dot" aria-hidden="true" />
          <span>
            {hiLang ? "भाव की तारीख" : "Price date"}: <b>{longDate(dateLabel, lang)}</b>
            {updatedStamp && <> · {t("updatedOn")} {updatedStamp}{freshnessLabel && ` (${freshnessLabel})`}</>}
            <br />
            <span className="cp-src">{t("sourceBadge")}</span>
          </span>
        </p>
        <p className="cp-range-text">{rangeText}</p>
        <div className="cp-actions">
          <a className="btn" href={shareUrl} target="_blank" rel="noopener noreferrer">
            {hiLang ? "WhatsApp पर भेजें" : "Share on WhatsApp"}
          </a>
          <Link className="btn btn-soft" href={`/#price-alerts/${commodityToSlug(commodity)}`}>🔔 {hiLang ? "भाव अलर्ट" : "Price alert"}</Link>
          <Link className="btn btn-soft" href={`/#sahi-daam/${commodityToSlug(commodity)}`}>🧮 {hiLang ? "असली लागत" : "Landing cost"}</Link>
        </div>
      </section>
      {/* Mera Khet entry point (3 Oct 2026): soybean, onion and tomato only. */}
      <KhetPromo commodity={commodity} hi={hiLang} page={crumbs.some((c) => c.href?.startsWith("/mandi-bhav/")) ? "cropstate" : "crop"} />
    </>
  );
}
