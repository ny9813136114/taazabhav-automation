import type { Metadata, Viewport } from "next";
import { Work_Sans, Noto_Sans_Devanagari } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";
import { OG_IMAGES } from "@/lib/og";
import InstallApp from "@/components/InstallApp";

// Self-hosted via next/font instead of a <link> to fonts.googleapis.com —
// that render-blocking external stylesheet was costing ~750ms+ before the
// page could even start painting (flagged by PageSpeed Insights as the
// single biggest opportunity). next/font downloads these at build time and
// serves them from our own domain, with font-display: swap baked in so
// text still renders immediately in a fallback font while these load.
// 2 Oct 2026 redesign: one sans family for Latin (Work Sans) and one for
// Hindi (Noto Sans Devanagari). The serif (Fraunces) and mono (Space Mono)
// fonts are gone — two fewer font downloads on every first visit. Old CSS
// that still names --font-fraunces / --font-space-mono falls back to these
// via the aliases at the top of globals.css.
const workSans = Work_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-work-sans",
  display: "swap",
});
const notoSansDevanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-noto-devanagari",
  display: "swap",
  // Not preloaded (2 Oct 2026, Phase D): preloading it competed with the
  // first paint on mobile; the English default page doesn't need it first.
  preload: false,
});

const SITE_URL = "https://taazabhav.com";
const DESCRIPTION =
  "Aaj ka mandi bhav: onion, potato, tomato, soyabean, wheat and 70+ crops from 900+ APMC mandis (Agmarknet). Best mandi finder, MSP check and Kisan Mela dates.";

export const viewport: Viewport = { themeColor: "#0F6B3E" };

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "TaazaBhav — Live Mandi Bhav Today | ताज़ा भाव",
    template: "%s | TaazaBhav",
  },
  description: DESCRIPTION,
  alternates: { canonical: "/" },
  openGraph: {
    images: OG_IMAGES,
    type: "website",
    siteName: "TaazaBhav",
    title: "TaazaBhav — Live Mandi Bhav Today",
    description: DESCRIPTION,
    url: SITE_URL,
    locale: "hi_IN",
  },
  // Brand icons (3 Oct 2026): Integrated Flow "भ" (public/brand/ has the
  // full set). favicon.ico (16/32/48) for Google results and old browsers,
  // SVG for sharp tabs, PNG for Android, apple-touch-icon for iPhone.
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "48x48" },
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  twitter: {
    card: "summary_large_image",
    images: ["/og.png"],
    title: "TaazaBhav — Live Mandi Bhav Today",
    description: DESCRIPTION,
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="hi"
      className={`${workSans.variable} ${notoSansDevanagari.variable}`}
    >
      <body>
        {children}
        <InstallApp />
        <Analytics />
      </body>
    </html>
  );
}
