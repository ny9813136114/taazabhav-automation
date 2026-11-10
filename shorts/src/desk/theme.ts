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
  Y: { name: "योजना की बात", color: "#c2185b" },
};

// Visual themes (10 Nov 2026, owner: "background and transitions should change,
// videos must not look the same"). The Python side picks one per video
// (engine/look.py); each theme tints the background, moves the picture in its
// own direction and brings every scene in with its own transition.
export type Enter = "slide" | "zoom" | "wipe" | "rise" | "fade";
export const THEMES: { tint: string; alpha: [string, string, string, string]; enter: Enter; pan: "in" | "out" | "left" | "right" }[] = [
  { tint: "#0d0f0c", alpha: ["b3", "73", "99", "d9"], enter: "slide", pan: "in" },
  { tint: "#06210f", alpha: ["a6", "59", "80", "d0"], enter: "zoom", pan: "out" },
  { tint: "#1b0f2e", alpha: ["b8", "73", "99", "d9"], enter: "wipe", pan: "left" },
  { tint: "#2a1405", alpha: ["a6", "66", "8c", "d0"], enter: "rise", pan: "in" },
  { tint: "#061a2e", alpha: ["b0", "66", "8c", "d9"], enter: "fade", pan: "right" },
];

// Shorts UI covers the bottom ~25% and a ~150 px rail on the right.
export const SAFE_D = { top: 150, bottom: 1440, left: 64, right: 930 };

export const toneColor = (tone?: string | null) =>
  tone === "up" || tone === "good" ? D.green : tone === "down" || tone === "low" || tone === "red" ? D.red : tone === "white" ? D.ink : D.gold;
