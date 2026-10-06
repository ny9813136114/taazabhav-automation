import React from "react";
import {
  AbsoluteFill, Sequence, Series, Audio, staticFile, useCurrentFrame, useVideoConfig,
  interpolate, spring, Easing,
} from "remotion";
import { loadFont } from "@remotion/fonts";
import { C, SAFE, FONT_HI, FONT_MONO, W } from "./theme";
import type { ShortProps, Mandi } from "./types";

loadFont({ family: FONT_HI, url: staticFile("fonts/Baloo2-Bold.ttf"), weight: "700" });
loadFont({ family: FONT_MONO, url: staticFile("fonts/IBMPlexMono-SemiBold.ttf"), weight: "600" });

export const DEFAULT_DURATIONS = { hook: 2.6, gap: 3.2, race: 8.4, insight: 4.6, cta: 3.6 };

// ---------- helpers ----------
export const inr = (v: number) => {
  const n = Math.round(v);
  const s = String(Math.abs(n));
  if (s.length <= 3) return (n < 0 ? "-" : "") + s;
  let head = s.slice(0, -3);
  const tail = s.slice(-3);
  const groups: string[] = [];
  while (head.length > 2) { groups.unshift(head.slice(-2)); head = head.slice(0, -2); }
  if (head) groups.unshift(head);
  return (n < 0 ? "-" : "") + [...groups, tail].join(",");
};

const pop = (frame: number, fps: number, at: number, damping = 12) =>
  spring({ frame: frame - at, fps, config: { damping, stiffness: 180, mass: 0.7 } });

const countUp = (frame: number, at: number, dur: number, to: number) =>
  to * interpolate(frame, [at, at + dur], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic),
  });

// small camera shake for "slam" moments
const shake = (frame: number, at: number, amp = 14) => {
  const t = frame - at;
  if (t < 0 || t > 8) return { x: 0, y: 0 };
  const k = (8 - t) / 8;
  return { x: Math.sin(t * 2.7) * amp * k, y: Math.cos(t * 3.3) * amp * k };
};

// every scene sits in the safe box, vertically centred
const Stage: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div style={{
    position: "absolute", top: SAFE.top + 60, left: SAFE.left,
    width: SAFE.right - SAFE.left, height: SAFE.bottom - 70 - (SAFE.top + 60),
    display: "flex", flexDirection: "column", justifyContent: "center", ...style,
  }}>{children}</div>
);

const T: React.FC<{ size: number; color?: string; mono?: boolean; style?: React.CSSProperties; children: React.ReactNode }> =
  ({ size, color = C.ink, mono, style, children }) => (
    <div style={{
      fontFamily: mono ? FONT_MONO : FONT_HI, fontSize: size, lineHeight: 1.15, color,
      fontWeight: 700, ...style,
    }}>{children}</div>
  );

// ---------- persistent frame (brand, progress, source) ----------
const Chrome: React.FC<ShortProps & { total: number }> = (p) => {
  const frame = useCurrentFrame();
  const progress = frame / p.total;
  return (
    <AbsoluteFill>
      {/* retention cue: thin progress bar */}
      <div style={{ position: "absolute", top: 0, left: 0, height: 10, width: `${progress * 100}%`, background: C.gold }} />
      <div style={{ position: "absolute", top: 70, left: SAFE.left, display: "flex", gap: 16, alignItems: "center" }}>
        <div style={{ background: C.gold, color: C.bg, borderRadius: 999, padding: "6px 22px", fontFamily: FONT_HI, fontSize: 36, fontWeight: 700 }}>ताज़ा भाव</div>
        <T size={34} color={C.inkSoft}>{p.dateHi} · {p.stateHi}</T>
      </div>
      <div style={{ position: "absolute", top: SAFE.bottom - 10, left: SAFE.left, right: W - SAFE.right }}>
        <T size={26} color={C.inkFaint} style={{ fontWeight: 400 }}>स्रोत: Agmarknet / data.gov.in (भारत सरकार) · भाव ₹/क्विंटल</T>
      </div>
    </AbsoluteFill>
  );
};

// ---------- scene 1: hook ----------
const PriceChip: React.FC<{ m: Mandi; color: string; label: string; enter: number; fromX: number }> =
  ({ m, color, label, enter, fromX }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();
    const s = pop(frame, fps, enter, 11);
    const x = interpolate(s, [0, 1], [fromX, 0]);
    return (
      <div style={{
        transform: `translateX(${x}px) scale(${interpolate(s, [0, 1], [0.8, 1])})`, opacity: Math.min(1, s * 1.5),
        background: C.panel, border: `4px solid ${color}`, borderRadius: 36, padding: "18px 40px",
        width: SAFE.right - SAFE.left, boxSizing: "border-box",
      }}>
        <T size={38} color={color}>{label} · {m.name}</T>
        <T size={170} mono color={color} style={{ letterSpacing: -4 }}>₹{inr(m.price)}</T>
      </div>
    );
  };

const Hook: React.FC<ShortProps> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const title = pop(frame, fps, 0, 9);
  const sh1 = shake(frame, 12), sh2 = shake(frame, 22);
  const sh = { x: sh1.x + sh2.x, y: sh1.y + sh2.y };
  return (
    <Stage style={{ transform: `translate(${sh.x}px, ${sh.y}px)` }}>
      <T size={150} color={C.gold} style={{ transform: `scale(${interpolate(title, [0, 1], [1.5, 1])})`, transformOrigin: "left center" }}>
        {p.commodityHi}
      </T>
      <T size={60} color={C.inkSoft} style={{ opacity: interpolate(frame, [4, 12], [0, 1], { extrapolateRight: "clamp" }), marginBottom: 36 }}>
        एक ही राज्य · एक ही दिन
      </T>
      <PriceChip m={p.high} color={C.green} label="सबसे ऊँचा" enter={10} fromX={-900} />
      <div style={{ height: 30 }} />
      <PriceChip m={p.low} color={C.red} label="सबसे कम" enter={20} fromX={900} />
      <T size={70} color={C.gold} style={{
        marginTop: 44, opacity: interpolate(frame, [34, 42], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>
        कहाँ बेचें? ↓
      </T>
    </Stage>
  );
};

// ---------- scene 2: the gap ----------
const Gap: React.FC<ShortProps> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const gap = p.high.price - p.low.price;
  const perKg = gap / 100;
  const pill = pop(frame, fps, 40);
  const bump = 1 + 0.06 * Math.max(0, 1 - Math.abs(frame - 34) / 6);
  return (
    <Stage>
      <T size={76} color={C.inkSoft}>मंडी बदलने से फ़र्क</T>
      <T size={230} mono color={C.green} style={{ letterSpacing: -8, transform: `scale(${bump})`, transformOrigin: "left center" }}>
        ₹{inr(countUp(frame, 4, 30, gap))}
      </T>
      <T size={60} color={C.inkSoft}>प्रति क्विंटल</T>
      <div style={{
        marginTop: 60, display: "inline-block", alignSelf: "flex-start", transform: `scale(${pill})`, transformOrigin: "left center",
        background: C.gold, color: C.bg, borderRadius: 999, padding: "14px 40px", fontFamily: FONT_HI, fontSize: 64, fontWeight: 700,
      }}>
        = ₹{inr(perKg)} प्रति किलो
      </div>
      {/* two bars: lowest vs highest */}
      <div style={{ marginTop: 90, display: "flex", flexDirection: "column", gap: 22 }}>
        {[{ m: p.low, c: C.red }, { m: p.high, c: C.green }].map(({ m, c }, i) => {
          const w = interpolate(frame, [8 + i * 6, 34 + i * 6], [0, (m.price / p.high.price) * (SAFE.right - SAFE.left)], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic),
          });
          return <div key={i} style={{ height: 56, width: w, background: c, borderRadius: 28 }} />;
        })}
      </div>
    </Stage>
  );
};

// ---------- scene 3: mandi bar race ----------
const Race: React.FC<ShortProps> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const rows = [...p.top.slice(0, 5)];
  const showLow = !rows.some((r) => r.name === p.low.name);
  const maxW = SAFE.right - SAFE.left - 20;
  const step = 16;
  const Row: React.FC<{ m: Mandi; i: number; color: string; badge?: string }> = ({ m, i, color, badge }) => {
    const at = 14 + i * step;
    const s = pop(frame, fps, at, 14);
    const w = interpolate(s, [0, 1], [0, Math.max(0.18, m.price / p.high.price) * maxW]);
    const badgeS = badge ? pop(frame, fps, 14 + (rows.length + 1) * step + 6) : 0;
    return (
      <div style={{ opacity: Math.min(1, s * 2), marginBottom: 34 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: maxW }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <T size={56} color={C.ink}>{m.name}</T>
            {badge ? (
              <div style={{
                transform: `scale(${badgeS})`, background: color, color: C.bg,
                borderRadius: 999, padding: "2px 18px", fontFamily: FONT_HI, fontSize: 34, fontWeight: 700, whiteSpace: "nowrap",
              }}>{badge}</div>
            ) : null}
          </div>
          <T size={60} mono color={color}>₹{inr(countUp(frame, at, 18, m.price))}</T>
        </div>
        <div style={{ height: 44, width: w, background: color, borderRadius: 22, marginTop: 8 }} />
      </div>
    );
  };
  return (
    <Stage>
      <T size={72} color={C.ink}>आज {p.stateShort} में {p.commodityHi} का भाव</T>
      <T size={42} color={C.inkFaint} style={{ marginBottom: 44 }}>{p.marketsCount} मंडियों में से टॉप {rows.length} · ₹/क्विंटल</T>
      {rows.map((m, i) => (
        <Row key={m.name} m={m} i={i} color={i === 0 ? C.green : C.gold} badge={i === 0 ? "सबसे ऊँचा" : undefined} />
      ))}
      {showLow ? (
        <>
          <T size={46} color={C.inkFaint} style={{ margin: "0 0 18px", opacity: interpolate(frame, [14 + rows.length * step - 6, 14 + rows.length * step], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>⋮</T>
          <Row m={p.low} i={rows.length} color={C.red} badge="सबसे कम" />
        </>
      ) : null}
    </Stage>
  );
};

// ---------- scene 4: insight + comment prompt ----------
const Insight: React.FC<ShortProps> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tip = pop(frame, fps, 30);
  const ask = pop(frame, fps, 70);
  const t = p.trend;
  return (
    <Stage>
      <T size={68} color={C.inkSoft}>{p.marketsCount} मंडियों का औसत</T>
      <T size={200} mono color={C.gold} style={{ letterSpacing: -6 }}>₹{inr(countUp(frame, 2, 26, p.average))}</T>
      {t && t.dir !== "flat" ? (
        <T size={58} color={t.dir === "up" ? C.green : C.red} style={{ opacity: interpolate(frame, [20, 28], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
          {t.dir === "up" ? "▲" : "▼"} कल से {t.pct}% {t.dir === "up" ? "ऊपर" : "नीचे"}
        </T>
      ) : null}
      <div style={{
        marginTop: 60, transform: `scale(${tip})`, transformOrigin: "left center", background: C.panel,
        border: `3px solid ${C.line}`, borderRadius: 32, padding: "26px 34px",
      }}>
        <T size={52} color={C.ink}>भाड़ा और आढ़त जोड़कर ही मंडी चुनें</T>
      </div>
      <div style={{ marginTop: 50, transform: `translateY(${interpolate(ask, [0, 1], [40, 0])}px)`, opacity: ask }}>
        <T size={58} color={C.gold}>आपकी मंडी में आज क्या भाव मिला?</T>
        <T size={52} color={C.inkSoft}>कमेंट में लिखें ↓</T>
      </div>
    </Stage>
  );
};

// ---------- scene 5: CTA that loops back into the hook ----------
const Cta: React.FC<ShortProps & { dur: number }> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = pop(frame, fps, 6);
  const underline = interpolate(frame, [14, 34], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const outro = interpolate(frame, [p.dur - 14, p.dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <Stage style={{ opacity: 1 - outro }}>
        <T size={70} color={C.inkSoft}>अपनी मंडी का पूरा भाव</T>
        <div style={{ transform: `scale(${s})`, transformOrigin: "left center", marginTop: 20 }}>
          <T size={118} mono color={C.gold} style={{ letterSpacing: -3 }}>taazabhav.com</T>
          <div style={{ height: 10, width: `${underline * 100}%`, background: C.gold, borderRadius: 5 }} />
        </div>
        <T size={56} color={C.ink} style={{ marginTop: 60 }}>{p.marketsCount} मंडियाँ · हर फ़सल · मुफ़्त</T>
        <T size={56} color={C.green} style={{ marginTop: 18 }}>कल सुबह 6 बजे — नया भाव</T>
      </Stage>
      {/* loop: the last frames fade back into the hook's opening word */}
      <Stage style={{ opacity: outro }}>
        <T size={150} color={C.gold}>{p.commodityHi}</T>
      </Stage>
    </AbsoluteFill>
  );
};

// ---------- composition ----------
export const MandiShort: React.FC<ShortProps> = (p) => {
  const { fps } = useVideoConfig();
  const d = { ...DEFAULT_DURATIONS, ...(p.durations || {}) };
  const f = (s: number) => Math.round(s * fps);
  const total = f(d.hook) + f(d.gap) + f(d.race) + f(d.insight) + f(d.cta);
  const raceStart = f(d.hook) + f(d.gap);
  return (
    <AbsoluteFill style={{ background: `radial-gradient(1200px 900px at 20% 10%, ${C.bg2}, ${C.bg})` }}>
      <Series>
        <Series.Sequence durationInFrames={f(d.hook)}><Hook {...p} /></Series.Sequence>
        <Series.Sequence durationInFrames={f(d.gap)}><Gap {...p} /></Series.Sequence>
        <Series.Sequence durationInFrames={f(d.race)}><Race {...p} /></Series.Sequence>
        <Series.Sequence durationInFrames={f(d.insight)}><Insight {...p} /></Series.Sequence>
        <Series.Sequence durationInFrames={f(d.cta)}><Cta {...p} dur={f(d.cta)} /></Series.Sequence>
      </Series>
      <Chrome {...p} total={total} />
      {/* sound design: whoosh on each price slam, tick as bars land, ding on the gap */}
      <Sequence from={10}><Audio src={staticFile("sfx/whoosh.wav")} volume={0.5} /></Sequence>
      <Sequence from={20}><Audio src={staticFile("sfx/whoosh.wav")} volume={0.5} /></Sequence>
      <Sequence from={f(d.hook) + 34}><Audio src={staticFile("sfx/ding.wav")} volume={0.6} /></Sequence>
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <Sequence key={i} from={raceStart + 14 + i * 16}><Audio src={staticFile("sfx/tick.wav")} volume={0.35} /></Sequence>
      ))}
      {p.audio ? <Audio src={staticFile(p.audio)} /> : null}
    </AbsoluteFill>
  );
};

export const totalFrames = (p: ShortProps, fps: number) => {
  const d = { ...DEFAULT_DURATIONS, ...(p.durations || {}) };
  return ["hook", "gap", "race", "insight", "cta"].reduce((a, k) => a + Math.round((d as any)[k] * fps), 0);
};
