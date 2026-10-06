import React from "react";
import { Composition, registerRoot } from "remotion";
import { MandiShort, totalFrames } from "./MandiShort";
import { BhavFlash, flashFrames, type FlashProps } from "./BhavFlash";
import { MelaAlert, melaFrames, type MelaProps } from "./MelaAlert";
import { FPS, H, W } from "./theme";
import type { ShortProps } from "./types";

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

const Root: React.FC = () => (
  <>
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
