import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, Audio, staticFile, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { C, SAFE, FONT_HI, FONT_MONO } from "./theme";

// "किसान मेला अलर्ट" (Batch 7, 27 Sep 2026): 9 s event reminder built from
// the confirmed Kisan Mela calendar on taazabhav.com. One job: tell a farmer
// WHICH mela, WHEN, WHERE, and how many days are left.
export type MelaProps = {
  clip?: string | null;
  credit?: string | null;
  badge: string;          // "किसान मेला अलर्ट"
  countdown: string;      // "7 दिन बाकी" / "कल से शुरू!"
  urgent: boolean;
  name: string;
  dates: string;          // "12–15 नवंबर 2026"
  place: string;
  cta: string;
  link: string;
  seconds?: number;
};

export const melaFrames = (p: MelaProps, fps: number) => Math.round((p.seconds ?? 9) * fps);

export const MelaAlert: React.FC<MelaProps> = (p) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames: D } = useVideoConfig();
  const s = (at: number, damping = 12) => spring({ frame: frame - at, fps, config: { damping, stiffness: 180, mass: 0.7 } });
  const accent = p.urgent ? C.red : C.green;
  const t = frame / D;
  const scale = 1.06 + 0.05 * Math.sin(Math.PI * t);
  const out = interpolate(frame, [D - 10, D], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const badge = s(0, 9), count = s(6, 9), name = s(16), dates = s(26), place = s(34), cta = s(56);
  const pulse = 1 + 0.03 * Math.sin(frame / 4);

  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      {p.clip ? (
        <OffthreadVideo src={staticFile(p.clip)} muted style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale})` }} />
      ) : (
        <AbsoluteFill style={{ background: `radial-gradient(circle at 70% 80%, ${C.bg2}, ${C.bg} 70%)` }} />
      )}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(10,7,3,0.93) 0%, rgba(10,7,3,0.82) 55%, rgba(10,7,3,0.35) 78%, rgba(10,7,3,0.6) 100%)" }} />

      <div style={{ position: "absolute", top: SAFE.top + 10, left: SAFE.left, width: SAFE.right - SAFE.left, opacity: out, textShadow: "0 3px 14px rgba(0,0,0,0.85)" }}>
        <div style={{ display: "inline-block", opacity: badge, transform: `translateY(${interpolate(badge, [0, 1], [-40, 0])}px)`,
          background: C.gold, color: C.bg, borderRadius: 999, padding: "8px 28px", fontFamily: FONT_HI, fontWeight: 700, fontSize: 46 }}>
          {p.badge}
        </div>

        <div style={{ marginTop: 28, display: "inline-block", transform: `scale(${interpolate(count, [0, 1], [2, 1]) * (p.urgent ? pulse : 1)}) rotate(-2deg)`,
          transformOrigin: "left center", opacity: Math.min(1, count * 2), background: accent, color: "#fff",
          borderRadius: 24, padding: "4px 30px", fontFamily: FONT_HI, fontWeight: 700, fontSize: 104 }}>
          {p.countdown}
        </div>

        <div style={{ marginTop: 34, opacity: name, transform: `translateY(${interpolate(name, [0, 1], [50, 0])}px)`,
          fontFamily: FONT_HI, fontWeight: 700, fontSize: p.name.length > 34 ? 70 : 84, lineHeight: 1.12, color: C.ink }}>
          {p.name}
        </div>

        <div style={{ marginTop: 26, opacity: dates, transform: `translateX(${interpolate(dates, [0, 1], [-70, 0])}px)`,
          fontFamily: FONT_HI, fontWeight: 700, fontSize: 64, color: C.gold }}>
          {p.dates}
        </div>

        <div style={{ marginTop: 8, opacity: place, fontFamily: FONT_HI, fontWeight: 700, fontSize: 46, color: C.inkSoft, lineHeight: 1.2 }}>
          {p.place}
        </div>

        <div style={{ marginTop: 40, opacity: cta, transform: `scale(${interpolate(cta, [0, 1], [0.85, 1])})`, transformOrigin: "left center",
          background: "rgba(255,246,230,0.12)", border: `2px solid ${C.line}`, borderRadius: 24, padding: "14px 24px", display: "inline-block" }}>
          <div style={{ fontFamily: FONT_HI, fontWeight: 700, fontSize: 36, color: C.inkSoft }}>{p.cta}</div>
          <div style={{ fontFamily: FONT_MONO, fontWeight: 600, fontSize: 34, color: C.gold }}>{p.link}</div>
        </div>
      </div>

      <div style={{ position: "absolute", top: 70, left: SAFE.left, background: C.gold, color: C.bg, borderRadius: 999, padding: "6px 22px", fontFamily: FONT_HI, fontSize: 36, fontWeight: 700 }}>ताज़ा भाव</div>
      {p.credit ? (
        <div style={{ position: "absolute", top: SAFE.bottom - 20, left: SAFE.left, fontFamily: FONT_HI, fontSize: 24, color: "rgba(255,255,255,0.75)", textShadow: "0 2px 8px rgba(0,0,0,0.9)" }}>{p.credit}</div>
      ) : null}

      <Audio src={staticFile("sfx/whoosh.wav")} volume={0.5} />
      <Sequence from={8}><Audio src={staticFile("sfx/ding.wav")} volume={0.5} /></Sequence>
    </AbsoluteFill>
  );
};
