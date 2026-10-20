import React from "react";
import {
  AbsoluteFill, Audio, OffthreadVideo, Img, Loop, Sequence, staticFile, useCurrentFrame, useVideoConfig, interpolate, spring, Easing,
} from "remotion";
import { loadFont } from "@remotion/fonts";
import { D, SERIES, SAFE_D, toneColor } from "./theme";
import type { DeskProps, DeskScene, Word } from "./types";

// "Mandi Board 2.0" (17 Oct 2026): one composition for all four series of
// the YouTube content engine (engine/ in the repo root). The Python side
// writes every number and every word; this file only decides how a scene
// looks and moves. Rules from the execution blueprint: the number comes
// first, at most 5 words a screen, something moves every 2-3 s, captions
// for sound-off viewers, and the last beat is the first frame again so the
// Short loops.
loadFont({ family: D.font, url: staticFile("fonts/Baloo2-Bold.ttf"), weight: "700" });

export const deskFrames = (p: DeskProps) => Math.max(60, p.frames);

const useSpring = (at: number, damping = 13) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - at, fps, config: { damping, stiffness: 170, mass: 0.7 } });
};

const outline = "0 0 2px #000, 0 6px 26px rgba(0,0,0,0.9)";

const Big: React.FC<{ text: string; color?: string; size?: number; at?: number; count?: number | null }> = ({ text, color = D.ink, size = 250, at = 0, count }) => {
  const frame = useCurrentFrame();
  const a = useSpring(at, 10);
  let shown = text;
  if (count && count > 0) {
    // Count up over 0.6 s; the final text keeps its own formatting (₹, commas).
    const t = interpolate(frame - at, [0, 18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
    shown = t < 1 ? text.replace(/[\d,]+/, Math.round(count * t).toLocaleString("en-IN")) : text;
  }
  const fs = shown.length > 7 ? Math.round(size * 7 / shown.length) : size;
  return (
    <div style={{ fontFamily: D.font, fontWeight: 700, fontSize: fs, lineHeight: 1, color, textShadow: outline,
      transform: `scale(${interpolate(a, [0, 1], [1.5, 1])})`, opacity: a, letterSpacing: -2 }}>
      {shown}
    </div>
  );
};

const Line: React.FC<{ text?: string | null; size?: number; at?: number; color?: string }> = ({ text, size = 76, at = 0, color = D.ink }) => {
  const a = useSpring(at);
  if (!text) return null;
  return (
    <div style={{ fontFamily: D.font, fontWeight: 700, fontSize: text.length > 22 ? Math.round(size * 0.8) : size, lineHeight: 1.15, color,
      textShadow: outline, opacity: a, transform: `translateY(${interpolate(a, [0, 1], [40, 0])}px)` }}>
      {text}
    </div>
  );
};

const Chip: React.FC<{ text: string; color: string; at?: number; dark?: boolean }> = ({ text, color, at = 0, dark }) => {
  const a = useSpring(at, 9);
  return (
    <div style={{ alignSelf: "flex-start", background: color, color: dark ? D.bg : "#fff", borderRadius: 999, padding: "10px 34px",
      fontFamily: D.font, fontWeight: 700, fontSize: 64, transform: `scale(${a})`, boxShadow: "0 8px 30px rgba(0,0,0,0.5)" }}>
      {text}
    </div>
  );
};

const Bars: React.FC<{ s: DeskScene }> = ({ s }) => {
  const frame = useCurrentFrame();
  const items = s.bars ?? [];
  const max = Math.max(...items.map((b) => b.value), 1);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 34, width: "100%" }}>
      {items.map((b, i) => {
        const w = interpolate(frame - 6 - i * 8, [0, 20], [0, b.value / max], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
        const c = toneColor(b.tone);
        return (
          <div key={i}>
            <div style={{ fontFamily: D.font, fontWeight: 700, fontSize: 54, color: D.inkSoft, textShadow: outline }}>{b.label}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 8 }}>
              <div style={{ height: 96, width: `${Math.max(0.04, w) * 640}px`, background: c, borderRadius: 18 }} />
              <div style={{ fontFamily: D.font, fontWeight: 700, fontSize: 82, color: D.ink, textShadow: outline, opacity: w > 0.05 ? 1 : 0 }}>{b.text}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const Meter: React.FC<{ s: DeskScene }> = ({ s }) => {
  const frame = useCurrentFrame();
  const target = Math.max(-1, Math.min(1, s.pos ?? 0));
  const swing = interpolate(frame, [0, 10, 22, 30], [-1, 1, target - 0.15, target], { extrapolateRight: "clamp" });
  const angle = swing * 70;
  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", alignItems: "center" }}>
      <svg width={760} height={420} viewBox="0 0 760 420">
        <path d="M 60 380 A 320 320 0 0 1 700 380" fill="none" stroke={D.red} strokeWidth={56} strokeDasharray="335 2000" />
        <path d="M 60 380 A 320 320 0 0 1 700 380" fill="none" stroke={D.gold} strokeWidth={56} strokeDasharray="0 335 335 2000" />
        <path d="M 60 380 A 320 320 0 0 1 700 380" fill="none" stroke={D.green} strokeWidth={56} strokeDasharray="0 670 340 2000" />
        <g transform={`rotate(${angle} 380 380)`}>
          <polygon points="370,380 390,380 380,90" fill={D.ink} />
        </g>
        <circle cx={380} cy={380} r={30} fill={D.ink} />
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", width: 760, fontFamily: D.font, fontWeight: 700, fontSize: 52, color: D.inkSoft, textShadow: outline }}>
        <span>{s.left ?? "रुकें"}</span><span>{s.right ?? "बेचें"}</span>
      </div>
    </div>
  );
};

const Stamp: React.FC<{ s: DeskScene }> = ({ s }) => {
  const frame = useCurrentFrame();
  const a = interpolate(frame, [0, 7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.back(2)) });
  const c = toneColor(s.tone);
  return (
    <div style={{ transform: `rotate(-6deg) scale(${interpolate(a, [0, 1], [2.4, 1])})`, opacity: a, border: `14px solid ${c}`, borderRadius: 34,
      padding: "26px 40px", color: c, fontFamily: D.font, fontWeight: 700, fontSize: (s.big ?? "").length > 12 ? 92 : 120, lineHeight: 1.05,
      textAlign: "center", background: "rgba(0,0,0,0.55)" }}>
      {s.big}
    </div>
  );
};

const Claim: React.FC<{ s: DeskScene }> = ({ s }) => {
  const frame = useCurrentFrame();
  const shake = Math.sin(frame * 1.7) * interpolate(frame, [0, 20], [14, 2], { extrapolateRight: "clamp" });
  return (
    <div style={{ transform: `translateX(${shake}px) rotate(2deg)`, background: "#fff", color: "#111", borderRadius: 26, padding: "28px 36px",
      boxShadow: "0 18px 50px rgba(0,0,0,0.6)", fontFamily: D.font, fontWeight: 700 }}>
      <div style={{ fontSize: 44, color: D.red }}>▶ वायरल वीडियो का दावा</div>
      <div style={{ fontSize: 96, lineHeight: 1.1 }}>{s.big}</div>
    </div>
  );
};

const TimelineItem: React.FC<{ it: NonNullable<DeskScene["items"]>[number]; i: number }> = ({ it, i }) => {
  const a = useSpring(4 + i * 10);
  const c = toneColor(it.tone);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 26, opacity: a, transform: `translateX(${interpolate(a, [0, 1], [-80, 0])}px)` }}>
      <div style={{ width: 54, height: 54, borderRadius: 99, background: c, flexShrink: 0, boxShadow: "0 0 0 10px rgba(255,255,255,0.12)" }} />
      <div>
        <div style={{ fontFamily: D.font, fontWeight: 700, fontSize: 50, color: D.inkSoft, textShadow: outline }}>{it.label}</div>
        <div style={{ fontFamily: D.font, fontWeight: 700, fontSize: 74, color: D.ink, textShadow: outline, lineHeight: 1.1 }}>{it.value}</div>
      </div>
    </div>
  );
};

const Timeline: React.FC<{ s: DeskScene }> = ({ s }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 26, width: "100%" }}>
    {(s.items ?? []).map((it, i) => <TimelineItem key={i} it={it} i={i} />)}
  </div>
);

const Phone: React.FC<{ s: DeskScene }> = ({ s }) => {
  const a = useSpring(0, 14);
  return (
    <div style={{ width: 470, height: 860, borderRadius: 56, background: "#0b0b0b", padding: 18, boxShadow: "0 30px 80px rgba(0,0,0,0.7)",
      transform: `translateY(${interpolate(a, [0, 1], [500, 0])}px)`, margin: "0 auto" }}>
      <div style={{ width: "100%", height: "100%", borderRadius: 48, overflow: "hidden", background: "#fff" }}>
        {s.video ? <OffthreadVideo src={staticFile(s.video)} muted style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }} /> : null}
      </div>
    </div>
  );
};

const Dots: React.FC<{ n: number; of: number }> = ({ n, of }) => (
  <div style={{ display: "flex", gap: 14 }}>
    {Array.from({ length: of }).map((_, i) => (
      <div key={i} style={{ width: i + 1 === n ? 70 : 26, height: 26, borderRadius: 99, background: i + 1 <= n ? D.ink : "rgba(255,255,255,0.3)" }} />
    ))}
  </div>
);

const SceneBody: React.FC<{ s: DeskScene }> = ({ s }) => {
  const c = toneColor(s.tone);
  switch (s.kind) {
    case "number":
      return (
        <>
          <Line text={s.label} size={92} />
          <div style={{ height: 14 }} />
          <Big text={s.big ?? ""} color={c} count={s.count} at={2} />
          <div style={{ height: 20 }} />
          <Line text={s.sub} size={70} at={10} color={D.inkSoft} />
        </>
      );
    case "move":
      return (
        <>
          <Chip text={s.big ?? ""} color={c} />
          <div style={{ height: 36 }} />
          <Line text={s.label} size={96} at={6} />
          <Line text={s.sub} size={66} at={12} color={D.inkSoft} />
        </>
      );
    case "compare":
      return (<><Line text={s.label} size={80} /><div style={{ height: 36 }} /><Bars s={s} /></>);
    case "meter":
      return (<><Line text={s.label} size={80} /><div style={{ height: 20 }} /><Meter s={s} /><div style={{ height: 26 }} /><Line text={s.sub} size={70} at={24} color={c} /></>);
    case "stamp":
      return (<><Line text={s.label} size={78} /><div style={{ height: 50 }} /><div style={{ display: "flex", justifyContent: "center", width: "100%" }}><Stamp s={s} /></div><div style={{ height: 50 }} /><Line text={s.sub} size={62} at={10} color={D.inkSoft} /></>);
    case "claim":
      return (<><Line text={s.label} size={78} /><div style={{ height: 40 }} /><Claim s={s} /><div style={{ height: 30 }} /><Line text={s.sub} size={62} at={12} color={D.inkSoft} /></>);
    case "timeline":
      return (<><Line text={s.label} size={80} /><div style={{ height: 36 }} /><Timeline s={s} /></>);
    case "news":
      return (
        <>
          {s.n && s.of ? <Dots n={s.n} of={s.of} /> : null}
          <div style={{ height: 30 }} />
          <Line text={s.label} size={84} />
          <div style={{ height: 16 }} />
          <Big text={s.big ?? ""} color={c} size={200} at={4} count={s.count} />
          <div style={{ height: 16 }} />
          <Line text={s.sub} size={62} at={10} color={D.inkSoft} />
        </>
      );
    case "phone":
      return (<><Line text={s.label} size={64} /><div style={{ height: 16 }} /><div style={{ width: "100%" }}><Phone s={s} /></div></>);
    case "cta":
      return (
        <>
          <Line text={s.label} size={92} />
          <div style={{ height: 40 }} />
          <Chip text={s.big ?? ""} color={D.ink} dark />
          <div style={{ height: 40 }} />
          <Line text={s.sub} size={64} at={10} color={D.gold} />
        </>
      );
    default: // "headline"
      return (
        <>
          <Line text={s.label} size={84} color={D.inkSoft} />
          <div style={{ height: 18 }} />
          <Big text={s.big ?? ""} color={c} size={180} count={s.count} />
          <div style={{ height: 22 }} />
          <Line text={s.sub} size={66} at={10} />
        </>
      );
  }
};

const Captions: React.FC<{ words: Word[]; from: number; frames: number }> = ({ words, from, frames }) => {
  const frame = useCurrentFrame();
  const t = frame + from; // absolute frame
  if (!words.length) return null;
  // Show a window of up to 6 words around the current one.
  let cur = 0;
  for (let i = 0; i < words.length; i++) if (words[i].from <= t) cur = i;
  const start = Math.floor(cur / 6) * 6;
  const win = words.slice(start, start + 6);
  const done = frame > frames;
  return (
    <div style={{ position: "absolute", left: SAFE_D.left, right: 1080 - SAFE_D.right, top: SAFE_D.bottom - 190, textAlign: "center", opacity: done ? 0 : 1 }}>
      <span style={{ background: "rgba(0,0,0,0.62)", borderRadius: 18, padding: "10px 18px", boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone",
        fontFamily: D.font, fontWeight: 700, fontSize: 60, lineHeight: 1.5 }}>
        {win.map((w, i) => (
          <span key={i} style={{ color: start + i === cur ? D.gold : D.ink }}>{w.w}{" "}</span>
        ))}
      </span>
    </div>
  );
};

export const Desk: React.FC<DeskProps> = (p) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const ser = SERIES[p.series] ?? SERIES.A;
  const zoom = 1.0 + 0.06 * (frame / durationInFrames);
  return (
    <AbsoluteFill style={{ background: D.bg, overflow: "hidden" }}>
      {p.clip ? (
        // OffthreadVideo ignores `loop` when rendering; <Loop> repeats the ~8 s clip.
        <Loop durationInFrames={p.clipFrames ?? 8 * 30 - 1}>
          <OffthreadVideo src={staticFile(p.clip)} muted style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }} />
        </Loop>
      ) : p.photo ? (
        <Img src={staticFile(p.photo)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }} />
      ) : (
        <AbsoluteFill style={{ background: `radial-gradient(circle at 30% 20%, ${ser.color}55, ${D.bg} 65%)` }} />
      )}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.70) 0%, rgba(0,0,0,0.45) 40%, rgba(0,0,0,0.60) 75%, rgba(0,0,0,0.85) 100%)" }} />

      {/* Series band */}
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 210, background: `linear-gradient(180deg, ${ser.color} 0%, ${ser.color}00 100%)` }} />
      <div style={{ position: "absolute", top: 80, left: SAFE_D.left, display: "flex", alignItems: "center", gap: 18 }}>
        <div style={{ background: "#fff", color: ser.color, borderRadius: 14, padding: "4px 18px", fontFamily: D.font, fontWeight: 700, fontSize: 44 }}>{ser.name}</div>
        <div style={{ fontFamily: D.font, fontWeight: 700, fontSize: 38, color: "#fff", textShadow: outline }}>ताज़ा भाव</div>
      </div>

      {/* Sach stamp */}
      {p.stamp ? (
        <div style={{ position: "absolute", top: 200, right: 1080 - SAFE_D.right + 10, transform: "rotate(8deg)", border: `5px solid ${D.green}`, borderRadius: 999,
          width: 230, height: 230, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.5)",
          fontFamily: D.font, fontWeight: 700, color: D.green, textAlign: "center", lineHeight: 1.05 }}>
          <div style={{ fontSize: 28, maxWidth: 180 }}>{p.stampTop ?? "सरकारी आँकड़ा"}</div>
          <div style={{ fontSize: 52 }}>✓</div>
          <div style={{ fontSize: 30, maxWidth: 190 }}>{p.stamp}</div>
        </div>
      ) : null}

      {p.scenes.map((s, i) => (
        <Sequence key={i} from={s.from} durationInFrames={s.frames}>
          <AbsoluteFill style={{ top: SAFE_D.top + (s.kind === "phone" ? 200 : 260), bottom: 1920 - SAFE_D.bottom + (s.kind === "phone" ? 210 : 230), left: SAFE_D.left, right: 1080 - SAFE_D.right,
            height: "auto", width: "auto", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "flex-start" }}>
            <SceneBody s={s} />
          </AbsoluteFill>
          <Captions words={s.words ?? []} from={s.from} frames={s.frames} />
          {s.audio ? <Audio src={staticFile(s.audio)} /> : null}
          {i > 0 ? <Audio src={staticFile("sfx/whoosh.wav")} volume={0.35} /> : null}
        </Sequence>
      ))}
      <Sequence from={0} durationInFrames={20}><Audio src={staticFile("sfx/ding.wav")} volume={0.6} /></Sequence>

      {p.credit ? (
        <div style={{ position: "absolute", bottom: 1920 - SAFE_D.bottom - 60, left: SAFE_D.left, fontFamily: D.font, fontSize: 24, color: "rgba(255,255,255,0.6)" }}>{p.credit}</div>
      ) : null}
    </AbsoluteFill>
  );
};
