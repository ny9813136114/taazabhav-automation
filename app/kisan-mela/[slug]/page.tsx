import type { Metadata } from "next";
import { notFound } from "next/navigation";
import MelaEventClient from "@/components/MelaEventClient";
import { OG_IMAGES } from "@/lib/og";
import { stateToSlug } from "@/lib/slug";
import { MELAS, getMela, melaWhen, todayIST, upcomingMelas } from "@/lib/melas";

export const revalidate = 86400;
const SITE_URL = "https://taazabhav.com";

export function generateStaticParams() {
  return MELAS.map((m) => ({ slug: m.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const m = getMela((await params).slug);
  if (!m) return {};
  const year = m.month.slice(0, 4);
  const path = `/kisan-mela/${m.slug}`;
  // 4 Oct 2026 (GSC): people search "<short name> 2026 date" and click the
  // result that shows the date, so the date goes in the title itself.
  const name = m.seoName ?? m.en;
  const when = melaWhen(m); // "13 Nov 2026" / "3–6 Oct 2026" / "Expected: Mar 2027"
  const whenShort = when.replace(` ${year}`, "");
  const ended = m.status === "confirmed" && !!m.end && m.end < todayIST();
  const title =
    m.status !== "confirmed"
      ? `${name} ${year} Date — ${whenShort}, Venue | ${m.hi}`
      : ended
        ? `${name} ${year} (${whenShort}, held) — Next Mela Date | ${m.hi}`
        : `${name} ${year} Date: ${whenShort} — Venue, Details | ${m.hi}`;
  const lead = m.status === "confirmed" ? `${name} ${year} date: ${when}${m.previousStart ? " (date changed by the organiser)" : ""}` : `${name} ${year}: dates not announced yet (${when})`;
  const description = `${lead}, at ${m.venue}, ${m.state}. ${m.highlights}. Organiser: ${m.organiser}. Official source linked.`;
  return { title, description, alternates: { canonical: path }, openGraph: { images: OG_IMAGES, title, description, url: path } };
}

export default async function MelaEventPage({ params }: { params: Promise<{ slug: string }> }) {
  const m = getMela((await params).slug);
  if (!m) notFound();
  const today = todayIST();
  const up = upcomingMelas(today).filter((r) => r.slug !== m.slug);
  const related = [...up.filter((r) => r.state === m.state), ...up.filter((r) => r.state !== m.state)].slice(0, 4);
  const path = `${SITE_URL}/kisan-mela/${m.slug}`;

  // Event schema only when real dates are announced (Google requires a
  // startDate; we never publish guessed dates).
  const eventLd =
    m.status === "confirmed" && m.start
      ? {
          "@context": "https://schema.org",
          "@type": "Event",
          name: `${m.en} ${m.start.slice(0, 4)}`,
          alternateName: m.hi,
          startDate: m.start,
          endDate: m.end ?? m.start,
          eventStatus: m.previousStart ? "https://schema.org/EventRescheduled" : "https://schema.org/EventScheduled",
          ...(m.previousStart ? { previousStartDate: m.previousStart } : {}),
          eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
          description: m.highlights,
          url: path,
          image: [`${SITE_URL}/og.png`],
          location: {
            "@type": "Place",
            name: m.venue,
            address: { "@type": "PostalAddress", addressLocality: m.city, addressRegion: m.state, addressCountry: "IN" },
          },
          organizer: { "@type": "Organization", name: m.organiser, url: m.source },
          ...(m.entry?.startsWith("Free")
            ? { isAccessibleForFree: true, offers: { "@type": "Offer", price: 0, priceCurrency: "INR", availability: "https://schema.org/InStock", url: m.source, validFrom: "2026-09-01" } }
            : {}),
        }
      : null;
  const crumbs = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "Kisan Mela", item: `${SITE_URL}/kisan-mela` },
      { "@type": "ListItem", position: 3, name: m.state, item: `${SITE_URL}/kisan-mela/state/${stateToSlug(m.state)}` },
      { "@type": "ListItem", position: 4, name: m.en, item: path },
    ],
  };
  return (
    <>
      {eventLd && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(eventLd) }} />}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(crumbs) }} />
      <MelaEventClient mela={m} today={today} related={related} />
    </>
  );
}
