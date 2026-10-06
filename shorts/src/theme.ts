// TaazaBhav Shorts design tokens (27 Sep 2026).
// Built for the Shorts feed: a dark "mandi board" background so prices glow,
// one bright accent per meaning (green = best price, red = lowest, gold = brand),
// and type big enough to read on a phone with the sound off.
export const W = 1080;
export const H = 1920;
export const FPS = 30;

export const C = {
  bg: "#16110b",        // warm near-black, like a chalk rate board
  bg2: "#231a10",
  panel: "#2e2215",
  ink: "#fff6e6",
  inkSoft: "#e9d6b4",
  inkFaint: "#a8916e",
  gold: "#ffb52e",
  green: "#3ddc84",
  red: "#ff5a4e",
  line: "rgba(255,246,230,0.14)",
};

// YouTube Shorts UI covers the bottom ~22% (title, channel, music) and the
// right ~130px (like/comment/share rail). Everything that matters stays
// inside this box.
export const SAFE = { top: 150, bottom: 1440, left: 64, right: 930 };

export const FONT_HI = "Baloo2";
export const FONT_MONO = "PlexMono";
