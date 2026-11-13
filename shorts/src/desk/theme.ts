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
export type Enter = "slide" | "zoom" | "wipe" | "rise" | "fade" | "tilt" | "drop";
// 13 Nov 2026 (owner: "card design, colour, background, everything different"):
// a theme is now a whole look, not just a tint. accent = band, badge and
// highlighted caption word; panel = the card behind each scene; align = left
// or centred text; badge = shape of the series tag; stamp = side of the stamp;
// cap = caption style.
export type Theme = {
  tint: string; alpha: [string, string, string, string]; enter: Enter; pan: "in" | "out" | "left" | "right";
  accent: string; panel: "none" | "glass" | "solid" | "outline"; align: "left" | "center";
  badge: "pill" | "square" | "outline"; stamp: "left" | "right"; cap: "box" | "plain" | "accent";
};
export const THEMES: Theme[] = [
  { tint: "#0d0f0c", alpha: ["b3", "73", "99", "d9"], enter: "slide", pan: "in", accent: "#2fd47a", panel: "none", align: "left", badge: "square", stamp: "right", cap: "box" },
  { tint: "#06210f", alpha: ["a6", "59", "80", "d0"], enter: "zoom", pan: "out", accent: "#ffc531", panel: "glass", align: "center", badge: "pill", stamp: "left", cap: "plain" },
  { tint: "#1b0f2e", alpha: ["b8", "73", "99", "d9"], enter: "wipe", pan: "left", accent: "#ff6fa5", panel: "outline", align: "left", badge: "outline", stamp: "right", cap: "accent" },
  { tint: "#2a1405", alpha: ["a6", "66", "8c", "d0"], enter: "rise", pan: "in", accent: "#ff9a3c", panel: "solid", align: "center", badge: "pill", stamp: "right", cap: "box" },
  { tint: "#061a2e", alpha: ["b0", "66", "8c", "d9"], enter: "fade", pan: "right", accent: "#4fc3f7", panel: "glass", align: "left", badge: "square", stamp: "left", cap: "accent" },
  { tint: "#2b0a0a", alpha: ["b3", "73", "99", "d9"], enter: "tilt", pan: "in", accent: "#ff5252", panel: "solid", align: "left", badge: "outline", stamp: "right", cap: "plain" },
  { tint: "#0b2a2a", alpha: ["a6", "59", "80", "d0"], enter: "drop", pan: "out", accent: "#5eead4", panel: "outline", align: "center", badge: "pill", stamp: "left", cap: "box" },
  { tint: "#26200a", alpha: ["b0", "66", "8c", "d9"], enter: "wipe", pan: "right", accent: "#d4e157", panel: "glass", align: "center", badge: "square", stamp: "right", cap: "accent" },
];

// Shorts UI covers the bottom ~25% and a ~150 px rail on the right.
export const SAFE_D = { top: 150, bottom: 1440, left: 64, right: 930 };

export const toneColor = (tone?: string | null) =>
  tone === "up" || tone === "good" ? D.green : tone === "down" || tone === "low" || tone === "red" ? D.red : tone === "white" ? D.ink : D.gold;
