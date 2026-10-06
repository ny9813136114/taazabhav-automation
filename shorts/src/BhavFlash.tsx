import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, Sequence, Audio, staticFile, useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from "remotion";
import { C, SAFE, FONT_HI, FONT_MONO, W } from "./theme";
import { inr } from "./MandiShort";

// Format A: "भाव फ्लैश" — a 7-10 second loopable Short (27 Sep 2026).
// Modelled on what actually wins in Indian daily-price Shorts (vidIQ, Jun-Sep
// 2026): 5-15 s, real produce on screen, ONE emotion word + ONE per-kg number,
// a named mandi. What we add that those channels can't: the verified contrast
// (the same crop, same day, another mandi) and a government source line.
export type FlashProps = {
  clip?: string | null;     // video file in public/ (Pexels/Pixabay/own), preferred
  photo?: string | null;    // still photo in public/, fallback

  credit?: string | null;   // "Video: Name / Pexels"
  tone: "low" | "high";     // cheapest mandi story or dearest mandi story
  word: string;             // "सबसे सस्ता!" / "सबसे महंगा!"
  commodityHi: string;
  perKg: number;            // wholesale ₹/kg (modal / 100)
  perQtl: number;
  mandi: string;            // "कोंच"
  stateHi: string;
  compare: { mandi: string; perKg: number }; // the other extreme, same day
  dateHi: string;
  seconds?: number;
};

export const flashFrames = (p: FlashProps, fps: number) => Math.round((p.seconds ?? 8) * fps);

export const BhavFlash: React.FC<FlashProps> = (p) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames: D } = useVideoConfig();
  const accent = p.tone === "low" ? C.red : C.green;

  // photo: slow push-in that returns to the start for a seamless loop
  const t = frame / D;
  const scale = 1.06 + 0.06 * Math.sin(Math.PI * t);
  const panY = -30 * Math.sin(Math.PI * t);

  const s = (at: number, damping = 11) => spring({ frame: frame - at, fps, config: { damping, stiffness: 190, mass: 0.7 } });
  const word = s(0, 9);
  const price = s(6);
  const mandi = s(16);
  const cmp = s(34);
  const meta = interpolate(frame, [54, 64], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // last 10 frames: text eases out so the loop restarts cleanly on the slam
  const out = interpolate(frame, [D - 10, D], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const kg = p.perKg * interpolate(frame, [6, 22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });

  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      {p.clip ? (
        <OffthreadVideo src={staticFile(p.clip)} muted style={{
          position: "absolute", width: "100%", height: "100%", objectFit: "cover",
          transform: `scale(${1 + (scale - 1) * 0.5})`,
        }} />
      ) : p.photo ? (
        <Img src={staticFile(p.photo)} style={{
          position: "absolute", width: "100%", height: "100%", objectFit: "cover",
          transform: `scale(${scale}) translateY(${panY}px)`,
        }} />
      ) : null}
      {/* readability: dark top-to-middle gradient, photo stays bright at the bottom */}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(10,7,3,0.92) 0%, rgba(10,7,3,0.78) 42%, rgba(10,7,3,0.15) 70%, rgba(10,7,3,0.55) 100%)" }} />

      <div style={{ position: "absolute", top: SAFE.top + 20, left: SAFE.left, width: SAFE.right - SAFE.left, opacity: out, textShadow: "0 3px 14px rgba(0,0,0,0.85)" }}>
        <div style={{
          display: "inline-block", transform: `scale(${interpolate(word, [0, 1], [2.2, 1])}) rotate(-2deg)`, transformOrigin: "left center",
          opacity: Math.min(1, word * 2), background: accent, color: "#fff", borderRadius: 22, padding: "6px 30px",
          fontFamily: FONT_HI, fontWeight: 700, fontSize: 92,
        }}>{p.word}</div>

        <div style={{ marginTop: 26, transform: `translateY(${interpolate(price, [0, 1], [60, 0])}px)`, opacity: price }}>
          <div style={{ fontFamily: FONT_HI, fontWeight: 700, fontSize: 96, color: C.ink, lineHeight: 1 }}>{p.commodityHi}</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 18 }}>
            <div style={{ fontFamily: FONT_MONO, fontWeight: 600, fontSize: 250, color: C.gold, letterSpacing: -10, lineHeight: 1.05 }}>₹{Math.round(kg)}</div>
            <div style={{ fontFamily: FONT_HI, fontWeight: 700, fontSize: 72, color: C.gold }}>/किलो</div>
          </div>
        </div>

        <div style={{ transform: `translateX(${interpolate(mandi, [0, 1], [-80, 0])}px)`, opacity: mandi, fontFamily: FONT_HI, fontWeight: 700, fontSize: 64, color: C.ink }}>
          {p.mandi} मंडी · {p.stateHi}
        </div>

        <div style={{
          marginTop: 34, display: "inline-flex", gap: 14, alignItems: "baseline", transform: `scale(${cmp})`, transformOrigin: "left center",
          background: "rgba(255,246,230,0.12)", border: `2px solid ${C.line}`, borderRadius: 24, padding: "12px 26px",
        }}>
          <span style={{ fontFamily: FONT_HI, fontWeight: 700, fontSize: 50, color: C.inkSoft }}>वहीं {p.compare.mandi} में</span>
          <span style={{ fontFamily: FONT_MONO, fontWeight: 600, fontSize: 60, color: p.tone === "low" ? C.green : C.red }}>₹{Math.round(p.compare.perKg)}</span>
          <span style={{ fontFamily: FONT_HI, fontWeight: 700, fontSize: 44, color: C.inkSoft }}>/किलो</span>
        </div>

        <div style={{ marginTop: 30, opacity: meta, fontFamily: FONT_HI, fontWeight: 700, fontSize: 38, color: C.inkSoft }}>
          थोक भाव ₹{inr(p.perQtl)}/क्विंटल · {p.dateHi}
        </div>
        <div style={{ opacity: meta, fontFamily: FONT_HI, fontSize: 32, color: C.inkFaint }}>
          स्रोत: Agmarknet (भारत सरकार) · taazabhav.com
        </div>
      </div>

      <div style={{ position: "absolute", top: 70, left: SAFE.left, background: C.gold, color: C.bg, borderRadius: 999, padding: "6px 22px", fontFamily: FONT_HI, fontSize: 36, fontWeight: 700 }}>ताज़ा भाव</div>
      {p.credit ? <div style={{ position: "absolute", top: SAFE.bottom - 20, left: SAFE.left, fontFamily: FONT_HI, fontSize: 24, color: "rgba(255,255,255,0.75)", textShadow: "0 2px 8px rgba(0,0,0,0.9)" }}>{p.credit}</div> : null}

      <Audio src={staticFile("sfx/whoosh.wav")} volume={0.5} />
      <Sequence from={20}><Audio src={staticFile("sfx/ding.wav")} volume={0.5} /></Sequence>
    </AbsoluteFill>
  );
};
