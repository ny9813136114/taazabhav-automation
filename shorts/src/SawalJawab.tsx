import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, Audio, staticFile, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { C, SAFE, FONT_HI, FONT_MONO } from "./theme";

// "सवाल-जवाब" explainer (Batch 8, 6 Oct 2026): one farmer question answered
// in ~20-30 s. Line 0 is the hook (the question), then the answer points,
// then the CTA. Each line has its own voice clip; it appears on screen the
// moment it is spoken and stays, so the viewer can read along sound-off.
export type SawalLine = { text: string; audio?: string | null; from: number; frames: number };
export type SawalProps = {
  clip?: string | null;
  credit?: string | null;
  label: string;                       // pillar badge, e.g. "सरकारी पैसा"
  tone: "gold" | "green" | "red";
  lines: SawalLine[];
  link: string;                        // "taazabhav.com/sarkari-paisa"
  asof: string;                        // "जानकारी 6 अक्टूबर 2026 तक की"
  frames: number;
};

export const sawalFrames = (p: SawalProps) => Math.max(90, p.frames);

export const SawalJawab: React.FC<SawalProps> = (p) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames: D } = useVideoConfig();
  const s = (at: number) => spring({ frame: frame - at, fps, config: { damping: 13, stiffness: 170, mass: 0.7 } });
  const accent = p.tone === "red" ? C.red : p.tone === "green" ? C.green : C.gold;
  const scale = 1.05 + 0.05 * (frame / D);
  const out = interpolate(frame, [D - 8, D], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const [hook, ...rest] = p.lines;
  const cta = rest.length ? rest[rest.length - 1] : null;
  const points = rest.slice(0, -1);
  const badge = s(0);
  const hookIn = hook ? s(hook.from) : 1;

  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      {p.clip ? (
        <OffthreadVideo src={staticFile(p.clip)} muted style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale})` }} />
      ) : (
        <AbsoluteFill style={{ background: `radial-gradient(circle at 70% 85%, ${C.bg2}, ${C.bg} 70%)` }} />
      )}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(10,7,3,0.94) 0%, rgba(10,7,3,0.86) 62%, rgba(10,7,3,0.5) 80%, rgba(10,7,3,0.7) 100%)" }} />

      <div style={{ position: "absolute", top: 70, left: SAFE.left, background: C.gold, color: C.bg, borderRadius: 999, padding: "6px 22px", fontFamily: FONT_HI, fontSize: 36, fontWeight: 700 }}>ताज़ा भाव</div>

      <div style={{ position: "absolute", top: SAFE.top + 10, left: SAFE.left, width: SAFE.right - SAFE.left, opacity: out, textShadow: "0 3px 14px rgba(0,0,0,0.85)" }}>
        <div style={{ display: "inline-block", opacity: badge, transform: `translateY(${interpolate(badge, [0, 1], [-30, 0])}px)`,
          background: accent, color: p.tone === "gold" ? C.bg : "#fff", borderRadius: 999, padding: "6px 26px",
          fontFamily: FONT_HI, fontWeight: 700, fontSize: 42 }}>
          {p.label}
        </div>

        {hook ? (
          <div style={{ marginTop: 26, opacity: hookIn, transform: `scale(${interpolate(hookIn, [0, 1], [1.25, 1])})`, transformOrigin: "left center",
            fontFamily: FONT_HI, fontWeight: 700, fontSize: hook.text.length > 40 ? 68 : 80, lineHeight: 1.15, color: C.ink }}>
            {hook.text}
          </div>
        ) : null}

        <div style={{ marginTop: 30, display: "flex", flexDirection: "column", gap: 18 }}>
          {points.map((l, i) => {
            const a = s(l.from);
            const speaking = frame >= l.from && frame < l.from + l.frames;
            return (
              <div key={i} style={{ opacity: frame < l.from ? 0 : a, transform: `translateX(${interpolate(a, [0, 1], [-60, 0])}px)`,
                display: "flex", gap: 16, alignItems: "flex-start",
                background: speaking ? "rgba(255,181,46,0.16)" : "rgba(255,246,230,0.07)", borderLeft: `8px solid ${speaking ? accent : C.line}`,
                borderRadius: 18, padding: "14px 20px" }}>
                <div style={{ fontFamily: FONT_MONO, fontWeight: 600, fontSize: 44, color: accent, lineHeight: 1.25 }}>{i + 1}</div>
                <div style={{ fontFamily: FONT_HI, fontWeight: 700, fontSize: l.text.length > 60 ? 42 : 48, lineHeight: 1.25, color: C.ink }}>{l.text}</div>
              </div>
            );
          })}
        </div>

        {cta ? (() => {
          const a = s(cta.from);
          return (
            <div style={{ marginTop: 30, opacity: frame < cta.from ? 0 : a, transform: `scale(${interpolate(a, [0, 1], [0.85, 1])})`, transformOrigin: "left center",
              background: "rgba(255,246,230,0.12)", border: `2px solid ${C.line}`, borderRadius: 24, padding: "14px 24px", display: "inline-block" }}>
              <div style={{ fontFamily: FONT_HI, fontWeight: 700, fontSize: 36, color: C.inkSoft }}>पूरा हिसाब मुफ़्त:</div>
              <div style={{ fontFamily: FONT_MONO, fontWeight: 600, fontSize: 38, color: C.gold }}>{p.link}</div>
            </div>
          );
        })() : null}
      </div>

      <div style={{ position: "absolute", top: SAFE.bottom - 60, left: SAFE.left, fontFamily: FONT_HI, fontSize: 26, color: "rgba(255,255,255,0.8)", textShadow: "0 2px 8px rgba(0,0,0,0.9)" }}>
        {p.asof}{p.credit ? ` · ${p.credit}` : ""}
      </div>

      <Audio src={staticFile("sfx/whoosh.wav")} volume={0.35} />
      {p.lines.map((l, i) => l.audio ? (
        <Sequence key={i} from={l.from} durationInFrames={l.frames + 6}><Audio src={staticFile(l.audio)} /></Sequence>
      ) : null)}
    </AbsoluteFill>
  );
};
