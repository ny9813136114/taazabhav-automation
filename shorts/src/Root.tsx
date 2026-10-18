import React from "react";
import { Composition, registerRoot } from "remotion";
import { MandiShort, totalFrames } from "./MandiShort";
import { BhavFlash, flashFrames, type FlashProps } from "./BhavFlash";
import { MelaAlert, melaFrames, type MelaProps } from "./MelaAlert";
import { SawalJawab, sawalFrames, type SawalProps } from "./SawalJawab";
import { FPS, H, W } from "./theme";
import type { ShortProps } from "./types";
import { Desk, deskFrames } from "./desk/Desk";
import type { DeskProps } from "./desk/types";

// Defaults only drive Remotion Studio previews; real renders always pass
// --props from flash.py (Batch 4, 27 Sep 2026).
const FLASH_DEFAULT: FlashProps = {
  clip: null, photo: null, credit: null, tone: "low", word: "सबसे सस्ता!", commodityHi: "प्याज",
  perKg: 17, perQtl: 1700, mandi: "Konch", stateHi: "उत्तर प्रदेश",
  compare: { mandi: "Bahraich", perKg: 59.57 }, dateHi: "25 सितंबर", seconds: 8,
};
const SHORT_DEFAULT: ShortProps = {
  commodityHi: "प्याज", commodityEn: "Onion", stateHi: "उत्तर प्रदेश", stateShort: "UP", dateHi: "25 सितंबर",
  story: "spread", high: { name: "Bahraich", price: 5957 }, low: { name: "Konch", price: 1700 },
  top: [{ name: "Bahraich", price: 5957 }, { name: "Badayoun", price: 4293 }, { name: "Mathura", price: 4000 }],
  marketsCount: 16, average: 3071, trend: null, audio: null,
};

// Sample only (layout preview); real props come from mela_video.py.
export const MELA_SAMPLE: MelaProps = {
  clip: null, credit: null, badge: "किसान मेला अलर्ट", countdown: "7 दिन बाकी", urgent: false,
  name: "Sample Krishi Mela", dates: "12–15 नवंबर 2026", place: "Sample Venue, Sample City, State",
  cta: "तारीख, पता, कैलेंडर में जोड़ें:", link: "taazabhav.com/kisan-mela/sample", seconds: 9,
};

// Sample only (layout preview); real props come from sawal_video.py (Batch 8).
export const SAWAL_SAMPLE: SawalProps = {
  clip: null, credit: null, label: "खाद का सही रेट", tone: "gold",
  lines: [
    { text: "डीएपी की बोरी ₹1,350 से ज़्यादा में मिली?", audio: null, from: 0, frames: 75 },
    { text: "50 किलो डीएपी की कीमत सरकार ने ₹1,350 तय की है।", audio: null, from: 80, frames: 90 },
    { text: "इससे ज़्यादा लेना गलत है, बिल ज़रूर मांगें।", audio: null, from: 175, frames: 75 },
    { text: "शिकायत ज़िला कृषि अधिकारी से करें।", audio: null, from: 255, frames: 70 },
    { text: "बोरी का पूरा हिसाब taazabhav.com/khad-calculator पर।", audio: null, from: 330, frames: 80 },
  ],
  link: "taazabhav.com/khad-calculator", asof: "जानकारी 6 अक्टूबर 2026 तक की", frames: 450,
};

// Sample only (Studio preview); real props come from engine/render.py.
export const DESK_SAMPLE: DeskProps = {
  series: "A", stamp: "17 अक्टूबर", frames: 300,
  scenes: [
    { kind: "number", from: 0, frames: 60, label: "सोयाबीन", big: "₹9,560", count: 9560, sub: "नीमच मंडी", tone: "up",
      words: [{ w: "सोयाबीन", from: 0 }, { w: "9560", from: 20 }, { w: "रुपये!", from: 40 }] },
    { kind: "move", from: 60, frames: 60, big: "▲ 12%", label: "नीमच मंडी", sub: "मध्य प्रदेश", tone: "up" },
    { kind: "compare", from: 120, frames: 70, label: "देश का आम भाव", bars: [
      { label: "आम भाव", value: 4350, text: "₹4,350", tone: "low" }, { label: "MSP", value: 5328, text: "₹5,328", tone: "white" }] },
    { kind: "meter", from: 190, frames: 70, label: "फ़ैसला", pos: -0.6, sub: "सरकारी खरीद देखें", tone: "low" },
    { kind: "cta", from: 260, frames: 40, label: "आपकी मंडी का भाव?", big: "कमेंट करें 👇", sub: "taazabhav.com" },
  ],
};

const Root: React.FC = () => (
  <>
    <Composition id="Desk" component={Desk as any} width={W} height={H} fps={FPS}
      durationInFrames={deskFrames(DESK_SAMPLE)} defaultProps={DESK_SAMPLE}
      calculateMetadata={({ props }) => ({ durationInFrames: deskFrames(props as DeskProps) })} />
    <Composition id="SawalJawab" component={SawalJawab as any} width={W} height={H} fps={FPS}
      durationInFrames={sawalFrames(SAWAL_SAMPLE)} defaultProps={SAWAL_SAMPLE}
      calculateMetadata={({ props }) => ({ durationInFrames: sawalFrames(props as SawalProps) })} />
  <Composition
    id="MelaAlert"
    component={MelaAlert as any}
    width={W}
    height={H}
    fps={FPS}
    durationInFrames={melaFrames(MELA_SAMPLE, FPS)}
    defaultProps={MELA_SAMPLE}
    calculateMetadata={({ props }) => ({ durationInFrames: melaFrames(props as MelaProps, FPS) })}
  />
    <Composition id="BhavFlash" component={BhavFlash as any} width={W} height={H} fps={FPS}
      durationInFrames={flashFrames(FLASH_DEFAULT, FPS)} defaultProps={FLASH_DEFAULT}
      calculateMetadata={({ props }) => ({ durationInFrames: flashFrames(props as FlashProps, FPS) })} />
    <Composition id="MandiShort" component={MandiShort as any} width={W} height={H} fps={FPS}
      durationInFrames={totalFrames(SHORT_DEFAULT, FPS)} defaultProps={SHORT_DEFAULT}
      calculateMetadata={({ props }) => ({ durationInFrames: totalFrames(props as ShortProps, FPS) })} />
  </>
);
registerRoot(Root);
