// Props the Python pipeline writes for one Short (props.json).
export type Mandi = { name: string; price: number };

export type ShortProps = {
  commodityHi: string;      // "प्याज"
  commodityEn: string;      // "Onion"
  stateHi: string;          // "उत्तर प्रदेश"
  stateShort: string;       // "UP" (for tight headings)
  dateHi: string;           // "25 सितंबर"
  story: "spread" | "best" | "shock" | "searched";
  high: Mandi;              // best-paying mandi today
  low: Mandi;               // lowest-paying mandi today
  top: Mandi[];             // up to 6, highest first (bar race)
  marketsCount: number;
  average: number;          // simple average of today's modal prices
  trend?: { dir: "up" | "down" | "flat"; pct: number } | null;
  // Seconds per scene. The pipeline sets these from the voice-over clip
  // lengths so picture and voice stay in step; defaults work silently.
  durations?: { hook: number; gap: number; race: number; insight: number; cta: number };
  audio?: string | null;    // file name in public/ (voice-over), optional
};
