// Builds content/tool_posts.json: the daily FB/IG "tool se hal" carousel posts.
// Every number comes from the website's own tool code (lib/*.ts), so a post
// never says something the tool would not. Imports are relative to the
// website repo root, so copy it there and run:
//   cp ops/build_tool_posts.ts ../Taazabhav-website/_btp.ts
//   cd ../Taazabhav-website && npx tsx _btp.ts ../taazabhav-automation/content/tool_posts.json && rm _btp.ts
// Re-run whenever a rate/MSP/rule changes on the site, then commit the JSON.
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { CROP_DOSES, FERTS, planFertilizer } from "./lib/khad";
import { BIGHA_STATES, SQFT_PER_ACRE, SQFT_PER_HECTARE } from "./lib/land-units";
import { MSP_CROPS } from "./lib/msp-vs-mandi";
import { checkHisab, COMMISSION_CAP_PCT, DEDUCTIONS_HIGH_PCT } from "./lib/hisab";
import { BHAVANTAR, bhavantar } from "./lib/bhavantar";
import { HOLD_DEFAULTS, holdOrSell } from "./lib/hold-or-sell";
import { DOCS, HELPLINE, KCC, REPORT_HOURS } from "./lib/fasal-nuksan";
import { STUCK } from "./lib/sarkari";

const OUT = resolve(process.argv[2] ?? "../taazabhav-automation/content/tool_posts.json");
const rs = (n: number) => "₹" + (Number.isInteger(n) || n > 5000 ? Math.round(n).toLocaleString("en-IN") : n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const num = (n: number, d = 2) => Number(n.toFixed(d)).toLocaleString("en-IN", { maximumFractionDigits: d });
const TAGS = "#किसान #kisan #farmer #taazabhav #ताज़ाभाव";

type Slide = Record<string, unknown> & { kind: string };
type Post = { id: string; tool: string; path: string; slides: Slide[]; caption: string; group: string; validUntil?: string };

function post(id: string, tool: string, path: string, slides: Slide[], lines: string[], group: string, validUntil?: string): Post {
  const url = `taazabhav.com${path}`;
  slides.push({ kind: "cta", big: "मुफ़्त टूल, हिंदी में", url });
  const caption = [...lines, "", `पूरा हिसाब अपने आंकड़ों से: ${url} (लिंक बायो में)`, "काम का लगे तो किसान भाइयों को शेयर करें, सेव कर लें।", "", TAGS].join("\n");
  return { id, tool, path, slides, caption, group: `${group}\nमुफ़्त टूल: https://${url}`, ...(validUntil ? { validUntil } : {}) };
}

const groups: Post[][] = [];

// 1. Khad calculator: bags + cost for a crop and area.
const khad: Post[] = [];
for (const [crop, acres] of [["wheat", 2], ["mustard", 2], ["chana", 2], ["potato", 1], ["paddy", 2], ["maize", 2], ["soybean", 2], ["cotton", 2], ["onion", 1], ["tomato", 1]] as const) {
  const d = CROP_DOSES.find((c) => c.key === crop)!;
  const p = planFertilizer(d, acres)!;
  const rows = p.lines.map((l) => [`${l.fert.hi} ${l.bagsToBuy} बोरी`, rs(l.cost)]);
  khad.push(post(`khad-${crop}-${acres}`, "khad", "/khad-calculator", [
    { kind: "hook", label: "खाद का हिसाब", big: `${acres} एकड़ ${d.hi} में कितनी खाद?`, sub: "बोरी भी, खर्च भी" },
    { kind: "answer", label: `${acres} एकड़ ${d.hi}, कुल खर्च`, big: rs(p.totalCost), sub: `सरकारी रेट पर: डीएपी ${rs(FERTS.dap.mrp)}, यूरिया ${rs(FERTS.urea.mrp)}` },
    { kind: "table", title: "कितनी बोरी लगेगी", rows, total: ["कुल", rs(p.totalCost)] },
    { kind: "list", title: "ध्यान रखें", items: [`खुराक: ${d.n}:${d.p}:${d.k} किलो N:P:K प्रति हेक्टेयर (सामान्य सिफ़ारिश)`, "मृदा स्वास्थ्य कार्ड हो तो उसकी खुराक डालें", "यूरिया एक बार में नहीं, 2-3 बार में", "पोटाश का दाम कंपनी के हिसाब से, बोरी का MRP देखें"] },
  ], [`${acres} एकड़ ${d.hi} में कितनी खाद लगेगी? कुल खर्च लगभग ${rs(p.totalCost)}।`, ...p.lines.map((l) => `• ${l.fert.hi}: ${l.bagsToBuy} बोरी, ${rs(l.cost)}`), `(खुराक ${d.n}:${d.p}:${d.k} किलो N:P:K/हेक्टेयर, सामान्य सिफ़ारिश। मृदा कार्ड हो तो उसकी खुराक डालें।)`],
  `${acres} एकड़ ${d.hi} में कितनी बोरी खाद और कितना खर्च, मुफ़्त कैलकुलेटर से 10 सेकंड में देखें।`));
}
groups.push(khad);

// 2. Khad rate: fixed government prices + what to do if overcharged.
const complain = ["छपी हुई PoS रसीद मांगें", "साथ में दूसरी दवा/खाद ज़बरदस्ती (टैगिंग) मना करें", `शिकायत: ज़िला कृषि अधिकारी या किसान कॉल सेंटर ${KCC} (मुफ़्त)`];
groups.push([
  post("rate-dap", "khad", "/khad-rate/dap", [
    { kind: "hook", label: "डीएपी की बोरी", big: `${rs(FERTS.dap.mrp)} से ज़्यादा दिए?`, sub: "तो दुकानदार गलत ले रहा है" },
    { kind: "answer", label: `डीएपी ${FERTS.dap.bagKg} किलो बोरी`, big: rs(FERTS.dap.mrp), sub: "सरकार सब्सिडी से इसी दाम पर रखती है" },
    { kind: "list", title: "ज़्यादा मांगे तो", items: complain },
  ], [`डीएपी (${FERTS.dap.bagKg} किलो) की बोरी का दाम ${rs(FERTS.dap.mrp)} है। इससे ज़्यादा न दें।`, ...complain.map((c) => `• ${c}`)],
  `डीएपी की बोरी ${rs(FERTS.dap.mrp)} की है, ज़्यादा न दें। शिकायत कहां करें, यहां लिखा है।`),
  post("rate-urea", "khad", "/khad-rate/urea", [
    { kind: "hook", label: "यूरिया की बोरी", big: `${rs(FERTS.urea.mrp)} से ज़्यादा दिए?`, sub: "सरकार का तय दाम, हर राज्य में एक" },
    { kind: "answer", label: `यूरिया ${FERTS.urea.bagKg} किलो बोरी`, big: rs(FERTS.urea.mrp), sub: "₹242 MRP + नीम कोटिंग और टैक्स" },
    { kind: "list", title: "ज़्यादा मांगे तो", items: complain },
  ], [`यूरिया (${FERTS.urea.bagKg} किलो) की बोरी ${rs(FERTS.urea.mrp)} की है (₹242 MRP + नीम कोटिंग व टैक्स)। हर राज्य में एक दाम।`, ...complain.map((c) => `• ${c}`)],
  `यूरिया की बोरी ${rs(FERTS.urea.mrp)} की है, हर राज्य में एक दाम। ज़्यादा लिया तो शिकायत ऐसे करें।`),
]);

// 3. Bigha to acre by state.
groups.push(BIGHA_STATES.map((s) => {
  const acre = s.sqft / SQFT_PER_ACRE, ha = s.sqft / SQFT_PER_HECTARE, perAcre = SQFT_PER_ACRE / s.sqft;
  return post(`bigha-${s.key}`, "bigha", "/bigha-to-acre", [
    { kind: "hook", label: s.hi, big: "1 बीघा = कितने एकड़?", sub: "हर राज्य का बीघा अलग" },
    { kind: "answer", label: `${s.hi} में 1 बीघा`, big: `${num(acre, 3)} एकड़`, sub: `${s.sqft.toLocaleString("en-IN")} वर्ग फ़ुट · ${num(ha, 3)} हेक्टेयर` },
    { kind: "table", title: "उल्टा हिसाब", rows: [["1 एकड़", `${num(perAcre, 2)} बीघा`], ["1 हेक्टेयर", `${num(perAcre * 2.471, 2)} बीघा`], ["10 बीघा", `${num(acre * 10, 2)} एकड़`]], ...(s.note ? { note: s.note } : {}) },
  ], [`${s.hi} में 1 बीघा = ${num(acre, 3)} एकड़ (${s.sqft.toLocaleString("en-IN")} वर्ग फ़ुट)।`, `1 एकड़ = ${num(perAcre, 2)} बीघा। 10 बीघा = ${num(acre * 10, 2)} एकड़।`, ...(s.note ? [`ध्यान दें: ${s.note}।`] : [])],
  `${s.hi} में 1 बीघा कितने एकड़? ${num(acre, 3)} एकड़। बीघा, बिस्वा, एकड़, हेक्टेयर सब एक जगह बदलें।`);
}));

// 4. MSP per crop -> MSP vs mandi tool.
groups.push(MSP_CROPS.map((c) => post(`msp-${c.key}`, "msp", "/msp-vs-mandi", [
  { kind: "hook", label: c.hi, big: "MSP पर बेचें या मंडी में?", sub: "भाड़ा और इंतज़ार जोड़कर देखें" },
  { kind: "answer", label: `${c.hi} का MSP (${c.season})`, big: `${rs(c.msp)}/क्विंटल`, sub: "सरकारी ख़रीद केंद्र पर" },
  { kind: "list", title: "बेचने से पहले जोड़ें", items: ["ख़रीद केंद्र तक भाड़ा", "आढ़त, हम्माली, तुलाई", "पैसा कितने दिन में आएगा", "टूल बताएगा: मंडी में कितने भाव से ऊपर बेचना फ़ायदे का"] },
], [`${c.hi} का MSP ${rs(c.msp)} प्रति क्विंटल (${c.season})।`, "MSP पर बेचें या मंडी में? भाड़ा, खर्च और पैसा आने का इंतज़ार जोड़कर ही असली फ़र्क दिखता है।"],
`${c.hi} MSP ${rs(c.msp)}। MSP केंद्र या मंडी, किसमें हाथ में ज़्यादा पैसा आएगा, मुफ़्त हिसाब देखें।`)));

// 5. Mandi hisab: commission cap.
const hisab: Post[] = [];
for (const [id, kind, qtl, rate, label] of [["grain", "grain", 20, 4500, "अनाज (20 क्विंटल × ₹4,500)"], ["veg", "perishable", 30, 1200, "सब्ज़ी (30 क्विंटल × ₹1,200)"]] as const) {
  const gross = qtl * rate, cap = (gross * COMMISSION_CAP_PCT[kind]) / 100;
  const r = checkHisab({ kind, slipWeightQtl: qtl, rate, commissionRs: cap * 1.5 })!;
  const c = r.checks.find((x) => x.id === "commission-high");
  hisab.push(post(`hisab-${id}`, "hisab", "/mandi-hisab", [
    { kind: "hook", label: "मंडी की पर्ची", big: "आढ़ती ने ज़्यादा काटा?", sub: "30 सेकंड में जांचें" },
    { kind: "answer", label: `${kind === "grain" ? "अनाज" : "सब्ज़ी-फल"} पर आढ़त की सीमा`, big: `${COMMISSION_CAP_PCT[kind]}%`, sub: `कुल कटौती ${DEDUCTIONS_HIGH_PCT}% से ज़्यादा = जांच करें` },
    { kind: "table", title: `उदाहरण: ${label}`, rows: [["कुल रकम", rs(gross)], [`आढ़त ज़्यादा से ज़्यादा`, rs(cap)], ["पर्ची में काटा (मान लो)", rs(cap * 1.5)]], total: ["ज़्यादा कटा", rs(c?.rs ?? cap * 0.5)] },
  ], [`मंडी पर्ची में आढ़त कितनी कट सकती है? ${kind === "grain" ? "अनाज" : "सब्ज़ी-फल"} पर ${COMMISSION_CAP_PCT[kind]}% तक।`, `उदाहरण: ${label} = ${rs(gross)}, आढ़त ${rs(cap)} से ज़्यादा नहीं।`, `कुल कटौती ${DEDUCTIONS_HIGH_PCT}% से ऊपर हो तो पर्ची दोबारा जांचें। (नियम राज्य के हिसाब से बदल सकते हैं, टूल पेज पर देखें।)`],
  "मंडी पर्ची में आढ़त, मंडी शुल्क, तौल की कटौती सही है या ज़्यादा? पर्ची के आंकड़े डालकर तुरंत जांचें।"));
}
groups.push(hisab);

// 6. Bhavantar (MP soybean), only during the sale window.
const bv: Post[] = [];
for (const [id, model, sale] of [["below", 4800, 4500], ["between", 4800, 5100]] as const) {
  const r = bhavantar(BHAVANTAR.msp, model, sale, 20)!;
  bv.push(post(`bhavantar-${id}`, "bhavantar", "/bhavantar-calculator", [
    { kind: "hook", label: "MP सोयाबीन भावांतर", big: "कितना पैसा मिलेगा?", sub: `MSP ${rs(BHAVANTAR.msp)} · बिक्री 22 अक्टूबर से` },
    { kind: "table", title: "उदाहरण (मॉडल रेट मान लो ₹" + model.toLocaleString("en-IN") + ")", rows: [["आपने बेचा", `${rs(sale)}/क्विंटल`], ["भावांतर", `${rs(r.perQtl)}/क्विंटल`], ["20 क्विंटल पर", rs(r.total)]], total: ["कुल मिला भाव", `${rs(r.effectivePerQtl)}/क्विंटल`] },
    { kind: "list", title: "नियम (2025 योजना जैसा)", items: ["मॉडल रेट से कम बेचा: MSP − मॉडल रेट", "मॉडल रेट और MSP के बीच: MSP − आपका भाव", "MSP से ऊपर बेचा: भावांतर नहीं", "असली मॉडल रेट सरकार रोज़ जारी करेगी"] },
  ], [`MP सोयाबीन भावांतर में कितना पैसा मिलेगा? उदाहरण: मॉडल रेट ${rs(model)} मानें, आपने ${rs(sale)} में बेचा, तो ${rs(r.perQtl)}/क्विंटल। 20 क्विंटल पर ${rs(r.total)}।`, "असली मॉडल रेट सरकार जारी करेगी, टूल में डालकर अपना हिसाब देखें।"],
  "MP सोयाबीन भावांतर में आपको कितना मिलेगा? अपना भाव और क्विंटल डालकर देखें।", BHAVANTAR.saleEnd));
}
groups.push(bv);

// 7. Rokun ya bechun.
const hold: Post[] = [];
for (const [crop, cropHi, qtl, price] of [["soybean", "सोयाबीन", 20, 4600], ["chana", "चना", 20, 5500]] as const) {
  const r = holdOrSell({ qtl, priceNow: price, priceLater: 0, ...HOLD_DEFAULTS })!;
  hold.push(post(`rokun-${crop}`, "rokun", "/rokun-ya-bechun", [
    { kind: "hook", label: cropHi, big: "अभी बेचें या रोकें?", sub: "रोकने का भी खर्च है" },
    { kind: "answer", label: `${HOLD_DEFAULTS.months} महीने रोका तो कम से कम चाहिए`, big: `${rs(r.breakEven)}/क्विंटल`, sub: `आज का भाव ${rs(price)} मानें` },
    { kind: "table", title: `उदाहरण: ${qtl} क्विंटल ${cropHi}`, rows: [["आज बेचें तो", rs(r.sellNow)], [`गोदाम किराया (₹${HOLD_DEFAULTS.storagePerQtlMonth}/क्विंटल/महीना)`, rs(r.storageCost)], [`ब्याज (${HOLD_DEFAULTS.interestPctYear}% सालाना)`, rs(r.interestCost)], [`सूखत/नुकसान ${HOLD_DEFAULTS.lossPct}%`, `${num(qtl - r.qtlLater, 1)} क्विंटल`]], total: ["भाव हर महीने बढ़ना चाहिए", rs(r.risePerMonth)] },
  ], [`${qtl} क्विंटल ${cropHi}, आज ${rs(price)}। ${HOLD_DEFAULTS.months} महीने रोकें तो गोदाम, ब्याज और सूखत जोड़कर भाव कम से कम ${rs(r.breakEven)} होना चाहिए, तभी फ़ायदा।`, "यह भविष्यवाणी नहीं है, रोकने का खर्च है। अपने आंकड़े डालकर देखें।"],
  `${cropHi} रोकें या बेचें? रोकने में कितना खर्च, और भाव कितना बढ़े तब फ़ायदा, अपने आंकड़ों से देखें।`));
}
groups.push(hold);

// 8. Fasal nuksan.
groups.push([
  post("nuksan-72", "nuksan", "/fasal-nuksan", [
    { kind: "hook", label: "ओले, बारिश, जलभराव से फ़सल खराब?", big: `${REPORT_HOURS} घंटे`, sub: "बीमा क्लेम की सूचना की समय सीमा" },
    { kind: "list", title: "सूचना कैसे दें", items: ["Crop Insurance ऐप पर फ़ोटो के साथ", `या हेल्पलाइन ${HELPLINE} पर कॉल`, "डॉकेट/शिकायत नंबर संभाल कर रखें", "कुछ खराब पौधे सर्वे तक रखें"] },
  ], [`ओले, बादल फटना, खेत में जलभराव से फ़सल खराब हुई? बीमा क्लेम के लिए ${REPORT_HOURS} घंटे में सूचना दें।`, `• Crop Insurance ऐप या हेल्पलाइन ${HELPLINE}`, "• डॉकेट नंबर संभाल कर रखें", "टूल से फ़ोटो, तारीख और मौसम के साथ सबूत बनाएं।"],
  `फ़सल नुकसान हुआ? ${REPORT_HOURS} घंटे में सूचना ज़रूरी। सबूत बनाने का मुफ़्त टूल।`),
  post("nuksan-docs", "nuksan", "/fasal-nuksan", [
    { kind: "hook", label: "फ़सल बीमा क्लेम", big: "कौन से कागज़ चाहिए?", sub: "पहले से तैयार रखें" },
    { kind: "list", title: "ये रखें", items: DOCS.slice(0, 5).map((d) => d.hi) },
  ], ["फ़सल बीमा क्लेम में कौन से कागज़ चाहिए:", ...DOCS.map((d) => `• ${d.hi}`)],
  "फ़सल बीमा क्लेम के लिए कौन से कागज़ चाहिए, पूरी लिस्ट और सबूत बनाने का मुफ़्त टूल।"),
]);

// 9. Sarkari paisa stuck.
groups.push(STUCK.map((g) => post(`stuck-${g.scheme}`, "sarkari", "/sarkari-paisa", [
  { kind: "hook", label: "सरकारी पैसा", big: g.titleHi, sub: "ये 5 चीज़ें जांचें" },
  { kind: "list", title: "क्या करें", items: g.stepsHi },
  { kind: "answer", label: "हेल्पलाइन", big: g.helpline, sub: "मुफ़्त कॉल" },
], [g.titleHi, ...g.stepsHi.map((s, i) => `${i + 1}. ${s}`), `हेल्पलाइन: ${g.helpline}`],
`${g.titleHi} ये 5 चीज़ें जांचें, हेल्पलाइन ${g.helpline}।`)));

// Interleave so consecutive days use different tools.
const posts: Post[] = [];
for (let i = 0; posts.length < groups.flat().length; i++) for (const g of groups) if (g[i]) posts.push(g[i]);
writeFileSync(OUT, JSON.stringify({ built: new Date().toISOString().slice(0, 10), posts }, null, 1) + "\n");
console.log(`${posts.length} posts -> ${OUT}`);
