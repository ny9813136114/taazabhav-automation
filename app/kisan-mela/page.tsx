import type { Metadata } from "next";
import MelaIndexClient from "@/components/MelaIndexClient";
import { OG_IMAGES } from "@/lib/og";
import { melaStates, todayIST, upcomingMelas, melaWhen, MELA_VERIFIED } from "@/lib/melas";
import { buildMelaFaqs, faqJsonLd } from "@/lib/faq-site";

// Static data (lib/melas.ts) — no database read. Rebuilt daily so past
// events drop off and "in N days" stays right.
export const revalidate = 86400;

const SITE_URL = "https://taazabhav.com";
const TITLE = "Kisan Mela 2026-27 Calendar — Krishi Mela & Agri Expo Dates | किसान मेला";
const DESC =
  "Kisan Mela 2026-27 dates: Pantnagar, GKVK Bangalore, PAU Ludhiana, Pusa, Kisan Pune and 40+ krishi melas and agri expos — venue and official source for each.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESC,
  alternates: { canonical: "/kisan-mela" },
  openGraph: { images: OG_IMAGES, title: TITLE, description: DESC, url: "/kisan-mela" },
};

export default function KisanMelaPage() {
  const today = todayIST();
  const melas = upcomingMelas(today);
  const itemList = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "Kisan Mela & Agri Expo calendar 2026-27",
    itemListElement: melas.map((m, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: `${m.en} — ${melaWhen(m)}`,
      url: `${SITE_URL}/kisan-mela/${m.slug}`,
    })),
  };
  const crumbs = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "Kisan Mela", item: `${SITE_URL}/kisan-mela` },
    ],
  };
  // Fix 5 (3 Oct 2026): FAQ from the same static list (no database read).
  const faqs = buildMelaFaqs({ melas, verified: MELA_VERIFIED });
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(itemList) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd(faqs.en)) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(crumbs) }} />
      <MelaIndexClient melas={melas} today={today} states={melaStates()} faqs={faqs} />
    </>
  );
}
