import React from "react";
import { AbsoluteFill, staticFile, interpolate, useCurrentFrame, Easing } from "remotion";
import { loadFont } from "@remotion/fonts";
import type { DeskScene } from "./types";
import type { Theme } from "./theme";

// 23 Nov 2026 (owner: "design full change, this is the same as what we use on
// our Reels"): six whole design systems, one per video. Each has its own
// font, paper or screen, text colours, card shape and chrome, so the Reels
// read as different shows, not one template in other colours. The Python
// side only picks the number (engine/look.py STORY_COUNT).
const FONTS: [string, string][] = [
  ["Tiro", "TiroDevanagariHindi-Regular.ttf"], ["Khand", "Khand-Bold.ttf"], ["Kalam", "Kalam-Bold.ttf"],
  ["Yatra", "YatraOne-Regular.ttf"], ["Rozha", "RozhaOne-Regular.ttf"],
];
FONTS.forEach(([family, file]) => loadFont({ family, url: staticFile(`fonts/${file}`), weight: "700" }));

export type Skin = {
  name: string; font: string; ink: string; soft: string; shadow: string; hi: string;
  tone: (t?: string | null) => string; dim: string;
  capBg: string; capInk: string; capHi: string;
  clipOpacity: number; clipFilter?: string;
  bg: (th: Theme) => React.CSSProperties; wrap: (idx: number, th: Theme) => React.CSSProperties;
  mark?: string; foot?: (idx: number) => string;
};

const tones = (up: string, down: string, mid: string) => (t?: string | null) =>
  t === "up" || t === "good" ? up : t === "down" || t === "low" || t === "red" ? down : t === "white" ? mid : mid;

export const SKINS: Skin[] = [
  { // 0 akhbar: a newspaper front page
    name: "akhbar", font: "Tiro", ink: "#161616", soft: "#4a4034", shadow: "none", hi: "#b3261e",
    tone: tones("#0b6b34", "#b3261e", "#161616"), dim: "rgba(0,0,0,0.06)",
    capBg: "#161616", capInk: "#f6efdc", capHi: "#ffd54a", clipOpacity: 0.16, clipFilter: "grayscale(1) sepia(0.6)",
    bg: () => ({ background: "#f1e6cc" }),
    wrap: () => ({ borderTop: "7px double #161616", borderBottom: "7px double #161616", padding: "30px 6px" }),
  },
  { // 1 chat: a phone chat thread
    name: "chat", font: "Khand", ink: "#111b21", soft: "#3b4a54", shadow: "none", hi: "#128c7e",
    tone: tones("#0b7d43", "#c62828", "#111b21"), dim: "rgba(0,0,0,0.06)",
    capBg: "#202c33", capInk: "#e9edef", capHi: "#25d366", clipOpacity: 0.1,
    bg: () => ({ background: "#0b141a" }),
    wrap: (i) => ({ background: i % 2 ? "#d9fdd3" : "#ffffff", borderRadius: i % 2 ? "40px 40px 8px 40px" : "40px 40px 40px 8px", padding: "26px 38px 14px",
      alignSelf: i % 2 ? "flex-end" : "flex-start", maxWidth: "92%", boxShadow: "0 6px 0 rgba(0,0,0,0.25)" }),
    foot: (i) => (i % 2 ? "✓✓" : ""),
  },
  { // 2 notebook: handwriting on lined paper
    name: "notebook", font: "Kalam", ink: "#1a2c78", soft: "#2c3f94", shadow: "none", hi: "#d81b60",
    tone: tones("#0a7a38", "#c62828", "#1a2c78"), dim: "rgba(26,44,120,0.08)",
    capBg: "#fff59d", capInk: "#1a2c78", capHi: "#d81b60", clipOpacity: 0.08, mark: "#ffeb3b",
    bg: () => ({ background: "repeating-linear-gradient(180deg,#fffbe0 0 78px,#9ec7ff 78px 82px)" }),
    wrap: (i) => ({ transform: `rotate(${i % 2 ? 1.4 : -1.4}deg)`, padding: "10px 6px 10px 90px" }),
  },
  { // 3 poster: flat colour, black frame, hard shadow
    name: "poster", font: "Yatra", ink: "#111111", soft: "#111111", shadow: "none", hi: "#111111",
    tone: tones("#0a5c2a", "#9b1111", "#111111"), dim: "rgba(0,0,0,0.08)",
    capBg: "#111111", capInk: "#ffffff", capHi: "#ffe14d", clipOpacity: 0.0,
    bg: (th) => ({ background: th.accent }),
    wrap: () => ({ background: "#ffffff", border: "10px solid #111", boxShadow: "16px 16px 0 #111", padding: "34px 40px" }),
  },
  { // 4 cinema: full-bleed picture, serif titles
    name: "cinema", font: "Rozha", ink: "#ffffff", soft: "#f1e6c8", shadow: "0 4px 22px rgba(0,0,0,0.95)", hi: "#ffd36b",
    tone: tones("#7dffb0", "#ff8a80", "#ffd36b"), dim: "rgba(0,0,0,0.35)",
    capBg: "transparent", capInk: "#fff4d6", capHi: "#ffd36b", clipOpacity: 1.0,
    bg: () => ({ background: "#000" }),
    wrap: () => ({ borderLeft: "6px solid #ffd36b", padding: "10px 0 10px 34px" }),
  },
  { // 5 tv: news broadcast graphics
    name: "tv", font: "Khand", ink: "#ffffff", soft: "#cfe0ff", shadow: "0 3px 12px rgba(0,0,0,0.6)", hi: "#ffdd33",
    tone: tones("#6dffa0", "#ff7a7a", "#ffdd33"), dim: "rgba(0,0,30,0.4)",
    capBg: "#ffffff", capInk: "#0a1f5c", capHi: "#d50000", clipOpacity: 0.55,
    bg: () => ({ background: "#071a4d" }),
    wrap: () => ({ background: "rgba(7,26,77,0.94)", borderTop: "10px solid #d50000", padding: "30px 40px", width: "100%" }),
  },
];

// The skin of the video being rendered (set once at the top of <Desk>).
export let SK: Skin = SKINS[3];
export const setSkin = (i: number) => { SK = SKINS[((i % SKINS.length) + SKINS.length) % SKINS.length]; };
export const tc = (t?: string | null) => SK.tone(t);

const F = (s: number) => ({ fontFamily: SK.font, fontWeight: 700 as const, fontSize: s });

// Skin chrome: the frame around the scenes. Drawn instead of the old band + badge.
export const Chrome: React.FC<{ story: number; name: string; idx: number; n: number; prog: number; th: Theme; label?: string | null }> = ({ story, name, idx, n, prog, th, label }) => {
  const frame = useCurrentFrame();
  const L = 64, R = 150;
  if (story === 0) return (
    <div style={{ position: "absolute", top: 70, left: L, right: R }}>
      <div style={{ display: "flex", justifyContent: "space-between", ...F(28), color: "#4a4034", borderBottom: "3px solid #161616", paddingBottom: 6 }}>
        <span>ताज़ा भाव • सरकारी स्रोत</span><span>{name}</span><span>पन्ना {idx + 1}/{n}</span>
      </div>
      <div style={{ textAlign: "center", ...F(78), color: "#161616", letterSpacing: 2, marginTop: 6 }}>किसान समाचार</div>
      <div style={{ height: 10, borderTop: "5px solid #b3261e", borderBottom: "2px solid #161616" }} />
    </div>
  );
  if (story === 1) return (
    <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 190, background: "#202c33", display: "flex", alignItems: "flex-end", gap: 22, padding: `0 ${L}px 24px` }}>
      <div style={{ width: 90, height: 90, borderRadius: 99, background: "#25d366", color: "#073b1d", display: "flex", alignItems: "center", justifyContent: "center", ...F(52) }}>ता</div>
      <div><div style={{ ...F(46), color: "#e9edef" }}>TaazaBhav • {name}</div><div style={{ ...F(30), color: "#25d366" }}>{Math.floor(frame / 20) % 2 ? "typing…" : "online"}</div></div>
    </div>
  );
  if (story === 2) return (
    <>
      <div style={{ position: "absolute", top: 0, bottom: 0, left: 150, width: 5, background: "#e57373" }} />
      {[260, 620, 980, 1340, 1700].map((y) => <div key={y} style={{ position: "absolute", left: 40, top: y, width: 46, height: 46, borderRadius: 99, background: "#2b2b2b", boxShadow: "inset 0 4px 8px #000" }} />)}
      <div style={{ position: "absolute", top: 76, left: 180, ...F(64), color: "#d81b60", transform: "rotate(-2deg)" }}>आज की बात ✎</div>
      <div style={{ position: "absolute", top: 150, left: 180, width: 420, height: 8, background: "#d81b60", borderRadius: 4, transform: "rotate(-1deg)" }} />
      <div style={{ position: "absolute", top: 80, right: R, ...F(36), color: "#1a2c78" }}>{name}</div>
    </>
  );
  if (story === 3) return (
    <>
      <div style={{ position: "absolute", inset: 22, border: "12px solid #111" }} />
      <div style={{ position: "absolute", top: 22, left: 22, right: 22, height: 150, background: "#111", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 44px" }}>
        <div style={{ ...F(64), color: "#fff" }}>{name}</div><div style={{ ...F(48), color: th.accent }}>{idx + 1}/{n}</div>
      </div>
      <div style={{ position: "absolute", right: -120, top: 1180, width: 420, height: 420, borderRadius: 999, background: "#111", opacity: 0.12 }} />
    </>
  );
  if (story === 4) return (
    <>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 22%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.8) 100%)" }} />
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 60, background: "#000" }} />
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 100, background: "#000" }} />
      <div style={{ position: "absolute", top: 100, left: L, ...F(40), letterSpacing: 8, color: "#ffd36b" }}>{name} — अध्याय {idx + 1}</div>
    </>
  );
  // 5: tv
  const tick = `${label ?? name}   ★   ताज़ा भाव   ★   ${name}   ★   TaazaBhav   ★   `.repeat(4);
  return (
    <>
      <div style={{ position: "absolute", top: 70, left: L, display: "flex", alignItems: "stretch" }}>
        <div style={{ background: "#d50000", color: "#fff", ...F(44), padding: "2px 22px", opacity: Math.floor(frame / 15) % 2 ? 0.8 : 1 }}>● LIVE</div>
        <div style={{ background: "#fff", color: "#0a1f5c", ...F(44), padding: "2px 22px" }}>TaazaBhav न्यूज़</div>
      </div>
      <div style={{ position: "absolute", top: 1215, left: 0, right: 0, height: 72, background: "#ffdd33", overflow: "hidden", display: "flex", alignItems: "center" }}>
        <div style={{ whiteSpace: "nowrap", ...F(44), color: "#0a1f5c", transform: `translateX(${-(frame * 7) % 1500}px)` }}>{tick}</div>
      </div>
    </>
  );
};

export const SceneFoot: React.FC<{ idx: number }> = ({ idx }) => (SK.foot ? <div style={{ alignSelf: "flex-end", ...F(28), color: "#667781", marginTop: 6 }}>{SK.foot(idx)}</div> : null);
export const _unused = { interpolate, Easing };
