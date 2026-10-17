// Design tokens for "Mandi Board 2.0" (17 Oct 2026), the YouTube content
// engine's look. Each series owns one colour so a viewer can tell them
// apart in the feed before reading a word.
export const D = {
  bg: "#0d0f0c",
  ink: "#ffffff",
  inkSoft: "#e8e4d8",
  green: "#2fd47a",
  red: "#ff4d42",
  gold: "#ffc531",
  font: "Baloo2",
};

export const SERIES: Record<string, { name: string; color: string }> = {
  A: { name: "भाव धमाका", color: "#e8620c" },
  B: { name: "किस्त का सच", color: "#13955a" },
  C: { name: "किसान खबर", color: "#1f5fd1" },
  D: { name: "टूल से हल", color: "#7b3fd0" },
};

// Shorts UI covers the bottom ~25% and a ~150 px rail on the right.
export const SAFE_D = { top: 150, bottom: 1440, left: 64, right: 930 };

export const toneColor = (tone?: string | null) =>
  tone === "up" || tone === "good" ? D.green : tone === "down" || tone === "low" || tone === "red" ? D.red : tone === "white" ? D.ink : D.gold;
