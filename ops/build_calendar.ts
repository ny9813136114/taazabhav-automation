// Builds content/calendar/<YYYY-MM>.json: the 09:30 IST FB/IG pillar post for
// every day of a month (TaazaBhav FB/IG Content Engine plan, sections 3-5).
// Static posts take every number from the website's own lib/*.ts, like
// ops/build_tool_posts.ts; days marked "dynamic" are built on the day by
// posts/pillar.py from taazabhav.com/api/yt-feed (today's prices).
// Imports are relative to the website repo root, so copy it there and run:
//   cp ops/build_calendar.ts ../taazabhav-website/_bc.ts
//   cd ../taazabhav-website && npx tsx _bc.ts 2026-11 ../taazabhav-automation/content/calendar/2026-11.json && rm _bc.ts
// Re-check every date against its government source before a new month.
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { CROP_DOSES, FERTS, planFertilizer } from "./lib/khad";
import { BIGHA_STATES, SQFT_PER_ACRE } from "./lib/land-units";
import { checkHisab, COMMISSION_CAP_PCT, DEDUCTIONS_HIGH_PCT, type HisabInput } from "./lib/hisab";
import { EVENTS, daysLeft, eventStatus, CHECKED_ON as SARKARI_CHECKED } from "./lib/sarkari";
import { DHAN_STATES, MSP_COMMON, dhanAmount, DHAN_CHECKED_ON } from "./lib/dhan-kharid";
import { PREMIUM_PCT, RABI_CUTOFF, OPT_OUT_BY, BIMA_CHECKED_ON } from "./lib/fasal-bima";
import { SOF_EXAMPLES, KCC_SUBVENTION_CAP, KCC_CHECKED_ON } from "./lib/kcc";
import { NEEDS, FID_CHECKED_ON } from "./lib/farmer-id";
import { SDRF_RATES, SDRF_MAX_HA, SDRF_MIN_LOSS, PALA_CHECKED_ON, PREVENT_HI, WATCH_C, HIGH_C, PALA_CROPS, TIER_HI } from "./lib/pala";
import { HOLD_DEFAULTS } from "./lib/hold-or-sell";
import { BHAVANTAR } from "./lib/bhavantar";
import { MSP_TABLE } from "./lib/msp";

const MONTH = process.argv[2] ?? "2026-11";
const OUT = resolve(process.argv[3] ?? `../taazabhav-automation/content/calendar/${MONTH}.json`);
const BUILT = new Date().toISOString().slice(0, 10);
const rs = (n: number) => "₹" + (Number.isInteger(n) ? n.toLocaleString("en-IN") : n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const num = (n: number, d = 2) => Number(n.toFixed(d)).toLocaleString("en-IN", { maximumFractionDigits: d });
const HI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"];
const hiDate = (iso: string) => { const [y, m, d] = iso.split("-").map(Number); return `${d} ${HI_MONTHS[m - 1]}`; };
const hiCheck = (iso: string) => `${hiDate(iso)} ${iso.slice(0, 4)}`;
const TAGS = "#किसान #kisan #taazabhav #ताज़ाभाव";

type Slide = Record<string, unknown> & { kind: string };
type Meta = { tool?: string; crop?: string; state?: string; angle: string; claim?: string };
type Post = { id: string; path: string; slides: Slide[]; caption: string; group: string; trust: string; link: string; ask: string; meta: Meta };
type Day = { date: string; weekday: string; pillar: string; week: string; dynamic?: string; args?: Record<string, unknown>; post?: Post };

// Pillar per weekday (plan section 4). Index = JS getUTCDay (0 = Sunday).
const WEEKDAY_HI = ["रविवार", "सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार"];
const ROTATION = ["P2", "P8", "P3", "P6", "P5", "P4", "P1"];
// Nov 2026 week themes (plan section 5).
const WEEKS: [string, string][] = [["2026-11-01", "सोयाबीन कब बेचें"], ["2026-11-09", "गेहूं-चना बुवाई"], ["2026-11-16", "सरकारी पैसा"], ["2026-11-23", "धान ख़रीद + पाले की तैयारी"]];
const weekOf = (d: string) => [...WEEKS].reverse().find(([s]) => d >= s)?.[1] ?? "";

function post(id: string, path: string, slides: Slide[], lines: string[], ask: string, group: string, trust: string, meta: Meta): Post {
  const link = `taazabhav.com${path}`;
  slides.push({ kind: "cta", big: "मुफ़्त टूल, हिंदी में", url: link });
  const caption = [...lines, "", ask, "", `पूरा हिसाब: ${link} (लिंक बायो में)`, "", TAGS].join("\n");
  return { id, path, slides, caption, group: `${group}\nhttps://${link}`, trust, link: `https://${link}`, ask, meta };
}

// ---------- P8 Deadline Ghanti (Mondays): dates from lib/sarkari + lib/dhan-kharid ----------
const hooked = new Set<string>();
function deadlines(day: string): Post {
  const until = (iso: string) => Math.round((Date.parse(`${iso}T00:00:00Z`) - Date.parse(`${day}T00:00:00Z`)) / 86_400_000);
  const rows: { hi: string; when: string; sort: number }[] = [];
  for (const e of EVENTS) {
    if (e.expected) continue;
    const left = daysLeft(e, day);
    if (left !== null && left <= 75) rows.push({ hi: e.hi.replace(/ \(₹[\d,]+\/क्विंटल\)/, ""), when: left === 0 ? "आज आख़िरी दिन" : `${left} दिन · ${hiDate(e.end)}`, sort: left });
    else if (eventStatus(e, day) === "upcoming" && until(e.start) <= 14) rows.push({ hi: e.hi, when: `${until(e.start)} दिन में शुरू · ${hiDate(e.start)}`, sort: 100 + until(e.start) });
  }
  const optOut = until(OPT_OUT_BY);
  if (optOut >= 0 && optOut <= 75) rows.push({ hi: "KCC लोन वाले: बीमा न चाहें तो बैंक को अर्ज़ी", when: `${optOut} दिन · ${hiDate(OPT_OUT_BY)}`, sort: optOut });
  for (const s of DHAN_STATES) {
    if (s.start && s.start <= day && until(s.start) >= -3) rows.push({ hi: `${s.hi}: धान ख़रीद शुरू हो गई`, when: `${-until(s.start)} दिन पहले · ${hiDate(s.start)}`, sort: 40 });
    if (s.start && s.start > day && until(s.start) <= 7) rows.push({ hi: `${s.hi}: धान ख़रीद शुरू`, when: `${until(s.start)} दिन में · ${hiDate(s.start)}`, sort: 50 + until(s.start) });
    if (s.end && s.end >= day && until(s.end) <= 10) rows.push({ hi: `${s.hi}: धान ख़रीद बंद`, when: `${until(s.end)} दिन · ${hiDate(s.end)}`, sort: until(s.end) });
  }
  rows.sort((a, b) => a.sort - b.sort);
  // Deadlines first; at most 2 "just started" rows so they never crowd them out.
  const started = rows.filter((r) => r.sort === 40).slice(0, 2);
  const top = [...rows.filter((r) => r.sort !== 40).slice(0, 4 - started.length), ...started];
  const first = top.find((r) => !hooked.has(r.hi)) ?? top[0];
  hooked.add(first.hi);
  return post(`p8-${day}`, "/sarkari-paisa", [
    { kind: "hook", label: `डेडलाइन घंटी · ${hiDate(day)}`, big: first.when.includes("शुरू") || first.when.includes("आज") ? first.when.split(" · ")[0] : `${first.when.split(" · ")[0]} बाकी`, sub: `${first.hi} (${first.when.split(" · ")[1] ?? ""})` },
    { kind: "table", title: "इन तारीख़ों से पहले काम कर लें", rows: top.map((r) => [r.hi, r.when]) },
    { kind: "list", title: "चूकें नहीं", items: ["पंजीकरण की पर्ची/रसीद संभाल कर रखें", "आख़िरी दिन का इंतज़ार न करें, पोर्टल धीमा हो जाता है", "राज्य की तारीख़ अलग हो सकती है, अपने पोर्टल पर पक्का करें"] },
  ], [`इस हफ़्ते की सरकारी तारीख़ें (${hiDate(day)} से):`, ...top.map((r) => `• ${r.hi}: ${r.when.replace(" · ", " (")})`)],
  "आपके इलाके में कौन सी तारीख़ सबसे ज़रूरी है? कमेंट में ज़िला लिखें।",
  `इस हफ़्ते की सरकारी तारीख़ें: ${first.hi}, ${first.when.replace(" · ", " (")})। पूरी लिस्ट 👇`,
  `स्रोत: सरकारी आदेश/PIB · जाँच: ${hiCheck(SARKARI_CHECKED)}`,
  { tool: "sarkari", angle: `deadlines-${day}` });
}

// ---------- P3 Kisan ka Hisaab (Tuesdays) ----------
function khadStory(day: string, stateHi: string, stateKey: string, acres: number): Post {
  const d = CROP_DOSES.find((c) => c.key === "wheat")!;
  const dap = planFertilizer(d, acres, "dap")!;
  const nps = planFertilizer(d, acres, "npk202013")!;
  const diff = nps.totalCost - dap.totalCost;
  const lines = (p: typeof dap) => p.lines.map((l) => [`${l.fert.hi}: ${l.bagsToBuy} बोरी`, rs(l.cost)]);
  return post(`p3-khad-wheat-${stateKey}-${acres}`, "/khad-calculator", [
    { kind: "hook", label: `किसान का हिसाब · ${stateHi}`, big: `${acres} एकड़ गेहूं: खाद ${rs(dap.totalCost)}`, sub: "डीएपी न मिले तो एनपीएस से कितना?" },
    { kind: "table", title: "डीएपी से (आम सिफ़ारिश)", rows: lines(dap), total: ["कुल", rs(dap.totalCost)] },
    { kind: "table", title: "एनपीएस 20:20:0:13 से", rows: lines(nps), total: ["कुल", rs(nps.totalCost)], note: "एनपीएस में 13% गंधक भी" },
    { kind: "answer", label: "फ़र्क", big: `${diff >= 0 ? "+" : "−"}${rs(Math.abs(diff))}`, sub: diff > 0 ? "एनपीएस से ज़्यादा बोरी, ज़्यादा ख़र्च" : "एनपीएस से कम ख़र्च" },
  ], [`${stateHi} का उदाहरण: ${acres} एकड़ गेहूं में खाद का ख़र्च, ${d.n}:${d.p}:${d.k} किलो N:P:K प्रति हेक्टेयर पर।`,
      `• डीएपी से: ${rs(dap.totalCost)} (${dap.lines.map((l) => `${l.fert.hi} ${l.bagsToBuy}`).join(", ")} बोरी)`,
      `• एनपीएस 20:20:0:13 से: ${rs(nps.totalCost)} (${nps.lines.map((l) => `${l.fert.hi} ${l.bagsToBuy}`).join(", ")} बोरी)`,
      `डीएपी ${rs(FERTS.dap.mrp)}, यूरिया ${rs(FERTS.urea.mrp)} सरकारी दाम; बाकी बोरी पर छपा MRP देखें। मृदा कार्ड हो तो उसकी खुराक।`],
  "आपके यहाँ डीएपी मिल रहा है या लाइन लग रही है? कमेंट में ज़िला लिखें।",
  `${acres} एकड़ गेहूं: डीएपी से ${rs(dap.totalCost)}, एनपीएस से ${rs(nps.totalCost)}। पूरा हिसाब 👇`,
  `स्रोत: खाद का सरकारी दाम (उर्वरक विभाग), सामान्य सिफ़ारिश · जाँच: ${hiCheck(BUILT)}`,
  { tool: "khad", crop: "wheat", state: stateKey, angle: "dap-vs-nps" });
}

function bimaStory(day: string): Post {
  const ex = SOF_EXAMPLES.find((s) => s.stateHi === "राजस्थान" && s.cropHi.startsWith("सरसों"))!;
  const [lo, hi] = (ex.perAcreHi.match(/[\d,]+/g) ?? []).map((v) => Number(v.replace(/,/g, "")));
  const acres = 5, pct = PREMIUM_PCT.rabi;
  const prem = (v: number) => Math.round((v * acres * pct) / 100);
  return post("p3-bima-mustard-rajasthan-5", "/fasal-bima-2026", [
    { kind: "hook", label: "किसान का हिसाब · राजस्थान", big: `5 एकड़ सरसों का बीमा: ${rs(prem(lo))} से`, sub: `किसान का प्रीमियम सिर्फ़ ${pct}%` },
    { kind: "table", title: `5 एकड़ सरसों (सिंचित), ${ex.year}`, rows: [["बीमा राशि (ज़िले के हिसाब से)", `${rs(lo * acres)} से ${rs(hi * acres)}`], [`आपका प्रीमियम (${pct}%)`, `${rs(prem(lo))} से ${rs(prem(hi))}`]], note: "बीमा राशि = फसल ऋण का स्केल ऑफ फाइनेंस × रकबा" },
    { kind: "list", title: "तारीख़ें", items: [`आख़िरी तारीख़: ${hiCheck(RABI_CUTOFF)} (राजस्थान)`, `KCC वाले किसान बीमा न चाहें तो ${hiCheck(OPT_OUT_BY)} तक बैंक को लिखित दें`, "फसल नुकसान पर 72 घंटे में सूचना दें"] },
  ], [`राजस्थान में 5 एकड़ सिंचित सरसों का रबी बीमा: किसान प्रीमियम ${pct}%, यानी ${rs(prem(lo))} से ${rs(prem(hi))} (ज़िले के हिसाब से)।`,
      `बीमा राशि ${ex.perAcreHi} प्रति एकड़ (स्केल ऑफ फाइनेंस ${ex.year})।`, `आख़िरी तारीख़ ${hiCheck(RABI_CUTOFF)}।`],
  "आपने रबी का बीमा करवाया? किस बैंक/CSC से? कमेंट में बताएं।",
  `5 एकड़ सरसों का बीमा ${rs(prem(lo))} से शुरू। अपना हिसाब 👇`,
  `स्रोत: PMFBY (pmfby.gov.in), SLBC राजस्थान SoF ${ex.year} · जाँच: ${hiCheck(BIMA_CHECKED_ON)}`,
  { tool: "bima", crop: "mustard", state: "rajasthan", angle: "premium" });
}

function dhanStory(): Post {
  const s = DHAN_STATES.find((x) => x.key === "chhattisgarh")!;
  const q = 50, amt = dhanAmount(q, "common");
  return post("p3-dhan-chhattisgarh-50", "/dhan-kharid", [
    { kind: "hook", label: "किसान का हिसाब · छत्तीसगढ़", big: `50 क्विंटल धान: ${rs(amt)}`, sub: `MSP ${rs(MSP_COMMON)} पर, ${hiDate(s.start!)} से ख़रीद` },
    { kind: "table", title: "50 क्विंटल कॉमन धान", rows: [["MSP (2026-27)", `${rs(MSP_COMMON)}/क्विंटल`], ["50 × MSP", rs(amt)], ["ख़रीद", `${hiDate(s.start!)} से ${hiCheck(s.end!)}`]], note: s.limitHi },
    { kind: "list", title: "बेचने से पहले", items: ["एग्रीस्टैक / एकीकृत किसान पोर्टल पर पंजीयन", "बिक्री से कम से कम 7 दिन पहले टोकन", "कृषक उन्नति योजना का 2026-27 सरकारी आदेश अभी नहीं मिला"] },
  ], [`छत्तीसगढ़ में धान की सरकारी ख़रीद ${hiDate(s.start!)} से ${hiCheck(s.end!)} तक।`, `50 क्विंटल कॉमन धान MSP ${rs(MSP_COMMON)} पर = ${rs(amt)}।`, `टोकन बिक्री से कम से कम 7 दिन पहले।`],
  "आपके केंद्र पर टोकन मिल गया? कितने दिन बाद की तारीख़ मिली? कमेंट में बताएं।",
  `छत्तीसगढ़ धान ख़रीद ${hiDate(s.start!)} से: 50 क्विंटल का ${rs(amt)}। पूरी जानकारी 👇`,
  `स्रोत: राज्य ख़रीद आदेश/खबरें · जाँच: ${hiCheck(DHAN_CHECKED_ON)}`,
  { tool: "dhan", crop: "paddy", state: "chhattisgarh", angle: "msp-amount" });
}

// ---------- P6 Hisaab Challenge (Wednesdays) + answer on Thursday ----------
type Challenge = { id: string; tool: string; path: string; q: string; options: string[]; answer: string; why: string; trust: string };
function challenges(): Challenge[] {
  const mp = BIGHA_STATES.find((s) => s.key === "mp")!;
  const bighaAcre = (5 * mp.sqft) / SQFT_PER_ACRE;
  const w = planFertilizer(CROP_DOSES.find((c) => c.key === "wheat")!, 1)!;
  const urea = w.lines.find((l) => l.fert.key === "urea")!;
  const prem = (40000 * PREMIUM_PCT.rabi) / 100;
  const dhan = dhanAmount(40, "common");
  return [
    { id: "bigha-mp-5", tool: "bigha", path: "/bigha-to-acre", q: "मध्य प्रदेश में 5 बीघा = कितने एकड़?", options: ["A) 1.38 एकड़", "B) 2.5 एकड़", "C) 3.1 एकड़"],
      answer: `${num(bighaAcre)} एकड़`, why: `मप्र में 1 बीघा = ${mp.sqft.toLocaleString("en-IN")} वर्ग फ़ुट, 1 एकड़ = ${SQFT_PER_ACRE.toLocaleString("en-IN")} वर्ग फ़ुट`, trust: "स्रोत: राज्य भू-अभिलेख इकाई" },
    { id: "urea-wheat-1", tool: "khad", path: "/khad-calculator", q: "1 एकड़ गेहूं में यूरिया की कितनी बोरी (45 किलो)?", options: ["A) 1 बोरी", "B) 2 बोरी", "C) 4 बोरी"],
      answer: `${urea.bagsToBuy} बोरी`, why: `120 किलो N/हेक्टेयर; डीएपी से मिली नाइट्रोजन घटाकर ${num(urea.kg, 0)} किलो यूरिया`, trust: "स्रोत: सामान्य सिफ़ारिश, खाद कैलकुलेटर" },
    { id: "bima-40000", tool: "bima", path: "/fasal-bima-2026", q: "₹40,000 बीमा राशि पर रबी का किसान प्रीमियम कितना?", options: ["A) ₹600", "B) ₹2,000", "C) ₹4,000"],
      answer: rs(prem), why: `रबी फसल पर किसान प्रीमियम ${PREMIUM_PCT.rabi}% (बाकी सरकार देती है)`, trust: "स्रोत: PMFBY (pmfby.gov.in)" },
    { id: "dhan-40", tool: "dhan", path: "/dhan-kharid", q: "40 क्विंटल कॉमन धान MSP पर कितने का?", options: ["A) ₹88,000", "B) ₹97,640", "C) ₹1,04,400"],
      answer: rs(dhan), why: `MSP 2026-27 ${rs(MSP_COMMON)}/क्विंटल × 40`, trust: "स्रोत: MSP 2026-27 (कृषि मंत्रालय)" },
  ];
}
function challengePost(c: Challenge, day: string): Post {
  return post(`p6-${c.id}`, c.path, [
    { kind: "quiz", label: "हिसाब चैलेंज", q: c.q, options: c.options, sub: "जवाब कमेंट में, सही जवाब कल सुबह" },
    { kind: "list", title: "तरीका", items: ["बिना कैलकुलेटर सोचें", "A, B या C कमेंट करें", "कल 9:30 बजे सही जवाब और हिसाब"] },
  ], [`हिसाब चैलेंज: ${c.q}`, ...c.options, "", "बिना कैलकुलेटर जवाब दें। सही जवाब और पूरा हिसाब कल सुबह।"],
  "आपका जवाब: A, B या C?",
  `हिसाब चैलेंज: ${c.q} जवाब दें 👇`, `${c.trust} · जाँच: ${hiCheck(BUILT)}`,
  { tool: c.tool, angle: `challenge-${c.id}` });
}

// ---------- P5 Sach ya Jhooth (Thursdays), with yesterday's answer ----------
type Claim = { id: string; tool: string; path: string; claim: string; verdict: string; tone: "false" | "half" | "true"; truth: string[]; trust: string; order: string };
function claims(): Claim[] {
  const pmkNew = NEEDS.find((n) => n.hi.includes("नया"))!;
  const pmkOld = NEEDS.find((n) => n.hi.includes("पुराने"))!;
  return [
    { id: "urea-300", tool: "khad", path: "/khad-rate/urea", claim: "यूरिया की बोरी अब ₹300 की हो गई है", verdict: "झूठ", tone: "false",
      truth: [`यूरिया (${FERTS.urea.bagKg} किलो) का सरकारी दाम ${rs(FERTS.urea.mrp)}, हर राज्य में एक`, "दाम में कोई बदलाव नहीं (उर्वरक विभाग)", "ज़्यादा मांगे तो PoS रसीद मांगें, ज़िला कृषि अधिकारी से शिकायत"],
      trust: `स्रोत: उर्वरक विभाग / PIB · जाँच: ${hiCheck(BUILT)}`, order: "2026-04-27" },
    { id: "kcc-5-lakh", tool: "kcc", path: "/kisan-credit-card", claim: "KCC पर सस्ता लोन अब ₹5 लाख तक मिलता है", verdict: "अभी नहीं", tone: "half",
      truth: ["बजट 2025-26 में ₹5 लाख की घोषणा हुई थी", `पर ब्याज छूट (MISS) के आदेश में सस्ती दर अब भी ${rs(KCC_SUBVENTION_CAP)} तक`, "बैंक में लिखित नियम देखकर ही भरोसा करें"],
      trust: `स्रोत: कृषि मंत्रालय MISS आदेश, SBI · जाँच: ${hiCheck(KCC_CHECKED_ON)}`, order: "2025-06-16" },
    { id: "farmer-id-pmkisan", tool: "farmer-id", path: "/farmer-id", claim: "Farmer ID नहीं बनी तो PM किसान की किस्त बंद", verdict: "पूरा सच नहीं", tone: "half",
      truth: [`नया पंजीकरण: ${pmkNew.noteHi.split(";")[0]}`, `पुराने किसान: ${pmkOld.noteHi.split(".")[0].split("।")[0]}`, "फिर भी Farmer ID बनवा लें, यही सुरक्षित है"],
      trust: `स्रोत: कृषि मंत्रालय, राज्य आदेश · जाँच: ${hiCheck(FID_CHECKED_ON)}`, order: "2025-01-01" },
    { id: "pala-bima", tool: "pala", path: "/pala-alert", claim: "पाले का नुकसान फसल बीमा (PMFBY) से मिल जाएगा", verdict: "बीमा से नहीं", tone: "false",
      truth: ["PMFBY में अकेले खेत का दावा: ओला, जलभराव, भूस्खलन, बादल फटना, आग; पाला नहीं", `SDRF में पाला आपदा है: ${SDRF_MIN_LOSS}%+ नुकसान पर ${rs(SDRF_RATES.rainfed)} (बारानी), ${rs(SDRF_RATES.irrigated)} (सिंचित) प्रति हेक्टेयर`, `ज़्यादा से ज़्यादा ${SDRF_MAX_HA} हेक्टेयर; पटवारी सर्वे ज़रूरी`],
      trust: `स्रोत: लोकसभा उत्तर (PMFBY), MHA SDRF नियम 2022-26 · जाँच: ${hiCheck(PALA_CHECKED_ON)}`, order: "2022-10-10" },
  ];
}
function claimPost(c: Claim, prev: Challenge | null): Post {
  const slides: Slide[] = [
    { kind: "claim", label: "सच या झूठ?", claim: c.claim, verdict: c.verdict, tone: c.tone },
    { kind: "list", title: "सरकारी सच", items: c.truth },
  ];
  const lines = [`सच या झूठ: "${c.claim}"`, `जवाब: ${c.verdict}।`, ...c.truth.map((t) => `• ${t}`)];
  if (prev) {
    slides.push({ kind: "answer", label: `कल का चैलेंज: ${prev.q}`, big: prev.answer, sub: prev.why });
    lines.push("", `कल के हिसाब चैलेंज का जवाब: ${prev.answer} (${prev.why})।`);
  }
  return post(`p5-${c.id}`, c.path, slides, lines, "आपने यह बात कहाँ सुनी थी? ऐसा कोई और दावा हो तो कमेंट में लिखें, अगली बार जाँचेंगे।",
    `"${c.claim}": ${c.verdict}। सरकारी सच यहाँ 👇`, c.trust, { tool: c.tool, angle: `claim-${c.id}`, claim: `${c.id}|${c.order}` });
}

// ---------- P2 Parchi Doctor (Sundays): example slips checked by lib/hisab ----------
type Slip = { id: string; cropHi: string; crop: string; state: string; stateHi: string; input: HisabInput; story: string };
function slips(): Slip[] {
  const msp = (k: string) => MSP_TABLE[k].pricePerQuintal;
  const s = (q: number, r: number) => q * r;
  return [
    { id: "soybean-commission", cropHi: "सोयाबीन", crop: "soybean", state: "madhya-pradesh", stateHi: "मध्य प्रदेश",
      input: { kind: "grain", slipWeightQtl: 20, rate: msp("Soyabean"), commissionRs: Math.round(s(20, msp("Soyabean")) * 0.03), marketFeeRs: 0, laborRs: 400 }, story: "आढ़त 3% कटी" },
    { id: "dhan-kg-cut", cropHi: "धान", crop: "paddy", state: "uttar-pradesh", stateHi: "उत्तर प्रदेश",
      input: { kind: "grain", slipWeightQtl: 40, rate: msp("Paddy(Common)"), cutKgPerQtl: 2, laborRs: 600 }, story: "हर क्विंटल पर 2 किलो काटा" },
    { id: "onion-commission", cropHi: "प्याज़", crop: "onion", state: "maharashtra", stateHi: "महाराष्ट्र",
      input: { kind: "perishable", slipWeightQtl: 30, rate: 1500, commissionRs: Math.round(30 * 1500 * 0.06), laborRs: 450 }, story: "6% आढ़त, सब्ज़ी पर" },
    { id: "maize-deductions", cropHi: "मक्का", crop: "maize", state: "rajasthan", stateHi: "राजस्थान",
      input: { kind: "grain", slipWeightQtl: 25, rate: msp("Maize"), commissionRs: Math.round(25 * msp("Maize") * 0.02), marketFeeRs: Math.round(25 * msp("Maize") * 0.016), laborRs: 1500, otherRs: 800 }, story: "तुलाई-हम्माली-बारदाना अलग से" },
    { id: "bajra-payment", cropHi: "बाजरा", crop: "bajra", state: "haryana", stateHi: "हरियाणा",
      input: { kind: "grain", slipWeightQtl: 15, rate: msp("Bajra(Pearl Millet/Cumbu)"), commissionRs: Math.round(15 * msp("Bajra(Pearl Millet/Cumbu)") * 0.02), laborRs: 300, paymentDays: 12 }, story: "कमीशन भी किसान से कटा" },
  ];
}
// Same wording as the site's checker (components/HisabCheckerClient.tsx).
const CHECK_HI: Record<string, (c: { rs: number; pct?: number; kg?: number; limitPct?: number; days?: number }) => string> = {
  "commission-high": (c) => `कमीशन ${num(c.pct ?? 0, 1)}%, सीमा ${c.limitPct}%: लगभग ${rs(c.rs)} ज़्यादा`,
  "commission-charged": (c) => `आपसे ${rs(c.rs)} कमीशन काटा; कई राज्यों में यह ख़रीदार देता है`,
  "kg-cut": (c) => `हर क्विंटल पर ${num(c.kg ?? 0, 1)} किलो की कटौती: ${rs(c.rs)} कम मिले`,
  "deductions-high": (c) => `कुल कटौती ${num(c.pct ?? 0, 1)}%, ${c.limitPct}% से ज़्यादा`,
  "market-fee": (c) => `आपसे ${rs(c.rs)} मंडी शुल्क काटा; आम तौर पर ख़रीदार देता है`,
  "payment-late": (c) => `भुगतान ${c.days} दिन बाद; ज़्यादातर राज्यों में उसी दिन का नियम`,
  "weight-short": (c) => `पर्ची पर वज़न ${c.kg} किलो कम: ${rs(c.rs)}`,
  "slip-math": (c) => `पर्ची का जोड़ ${rs(c.rs)} कम`,
  "received-less": (c) => `हाथ में ${rs(c.rs)} कम आए`,
};
// First-slide hook from the slip's main problem: one number, one point.
const HOOK_HI: Record<string, (c: { rs: number; pct?: number; kg?: number; days?: number }, crop: string) => string> = {
  "commission-high": (c, crop) => `${crop}: ${rs(c.rs)} ज़्यादा कमीशन`,
  "kg-cut": (c, crop) => `${crop}: ${rs(c.rs)} की वज़न कटौती`,
  "deductions-high": (c, crop) => `${crop}: ${num(c.pct ?? 0, 1)}% कटौती`,
  "payment-late": (c, crop) => `${crop}: पैसा ${c.days} दिन बाद`,
};
const HOOK_ORDER = ["commission-high", "kg-cut", "deductions-high", "payment-late"];

function slipPost(sl: Slip): Post {
  const r = checkHisab(sl.input)!;
  const checks = r.checks.map((c) => CHECK_HI[c.id](c));
  const rows: [string, string][] = [["कुल बिक्री", rs(r.gross)], ["कटौती", `${rs(r.deductions)} (${num(r.deductionPct, 1)}%)`], ["हाथ में", rs(r.correctNet)]];
  const main = HOOK_ORDER.map((id) => r.checks.find((c) => c.id === id)).find(Boolean)!;
  const big = HOOK_HI[main.id](main, `${sl.cropHi} की पर्ची`);
  return post(`p2-${sl.id}`, "/mandi-hisab", [
    { kind: "hook", label: `पर्ची डॉक्टर · ${sl.stateHi}`, big, sub: `${sl.story} (उदाहरण पर्ची)` },
    { kind: "table", title: `${sl.input.slipWeightQtl} क्विंटल ${sl.cropHi} @ ${rs(sl.input.rate)}`, rows },
    { kind: "list", title: "पर्ची में क्या गड़बड़", items: checks.length ? checks : ["इस पर्ची में कोई बड़ी गड़बड़ नहीं"] },
    { kind: "list", title: "आप क्या करें", items: ["पर्ची (J-फॉर्म) की फ़ोटो हमेशा रखें", "ज़्यादा कटौती पर मंडी सचिव को लिखित शिकायत", `आढ़त की सीमा: अनाज ${COMMISSION_CAP_PCT.grain}%, सब्ज़ी ${COMMISSION_CAP_PCT.perishable}% (मॉडल कानून; राज्य का नियम देखें)`] },
  ], [`पर्ची डॉक्टर (उदाहरण पर्ची, ${sl.stateHi}): ${sl.input.slipWeightQtl} क्विंटल ${sl.cropHi} @ ${rs(sl.input.rate)}।`,
      `कुल ${rs(r.gross)}, कटौती ${rs(r.deductions)} (${num(r.deductionPct, 1)}%), हाथ में ${rs(r.correctNet)}।`, ...checks.map((c) => `• ${c}`)],
  "अपनी पर्ची की फ़ोटो कमेंट में डालें (नाम-नंबर छुपाकर), अगले रविवार उसका हिसाब करेंगे।",
  `${big}? अपनी मंडी पर्ची ऐसे जाँचें 👇`,
  `स्रोत: मॉडल APLM कानून 2017, मंडी हिसाब टूल · उदाहरण पर्ची · जाँच: ${hiCheck(BUILT)}`,
  { tool: "hisab", crop: sl.crop, state: sl.state, angle: `parchi-${sl.id}` });
}

// ---------- the month ----------
function build(month: string): Day[] {
  const [y, m] = month.split("-").map(Number);
  const daysIn = new Date(Date.UTC(y, m, 0)).getUTCDate();
  const ch = challenges(), cl = claims(), sp = slips();
  const p3 = [
    { dynamic: "P3-hold", args: { crop: "soybean", state: "madhya-pradesh", qtl: 20 } },
    { post: (d: string) => khadStory(d, "उत्तर प्रदेश", "uttar-pradesh", 5) },
    { post: (d: string) => bimaStory(d) },
    { post: () => dhanStory() },
  ];
  const p1States = ["madhya-pradesh", "rajasthan", "maharashtra", "uttar-pradesh", "gujarat"];
  const count: Record<string, number> = {};
  const out: Day[] = [];
  let lastChallenge: Challenge | null = null;
  for (let d = 1; d <= daysIn; d++) {
    const iso = `${month}-${String(d).padStart(2, "0")}`;
    const wd = new Date(`${iso}T00:00:00Z`).getUTCDay();
    const pillar = ROTATION[wd];
    const i = count[pillar] = (count[pillar] ?? -1) + 1;
    const day: Day = { date: iso, weekday: WEEKDAY_HI[wd], pillar, week: weekOf(iso) };
    if (pillar === "P8") day.post = deadlines(iso);
    else if (pillar === "P3") { const x = p3[i % p3.length]; if ("dynamic" in x) Object.assign(day, x); else day.post = x.post(iso); }
    else if (pillar === "P6") { lastChallenge = ch[i % ch.length]; day.post = challengePost(lastChallenge, iso); }
    else if (pillar === "P5") { day.post = claimPost(cl[i % cl.length], lastChallenge); lastChallenge = null; }
    else if (pillar === "P2") day.post = slipPost(sp[i % sp.length]);
    else if (pillar === "P4") day.dynamic = "P4";
    else if (pillar === "P1") { day.dynamic = "P1"; day.args = { state: p1States[i % p1States.length] }; }
    out.push(day);
  }
  return out;
}

const days = build(MONTH);
// Site facts the dynamic pillars (posts/pillar.py) need, so Python never
// keeps its own copy of a rule or a number.
const site = {
  hold: HOLD_DEFAULTS,
  bhavantar: { msp: BHAVANTAR.msp, saleStart: BHAVANTAR.saleStart, saleEnd: BHAVANTAR.saleEnd },
  pala: {
    watchC: WATCH_C, highC: HIGH_C, checkedOn: PALA_CHECKED_ON,
    prevent: PREVENT_HI.slice(0, 3),
    crops: PALA_CROPS.filter((c) => c.tier === 1).slice(0, 4).map((c) => `${c.hi}: ${TIER_HI[c.tier]} नुकसान, ${c.stageHi}`),
    sdrf: `SDRF: ${SDRF_MIN_LOSS}%+ नुकसान पर ${rs(SDRF_RATES.rainfed)} (बारानी) / ${rs(SDRF_RATES.irrigated)} (सिंचित) प्रति हेक्टेयर, ${SDRF_MAX_HA} हेक्टेयर तक`,
  },
};
writeFileSync(OUT, JSON.stringify({ month: MONTH, built: BUILT, site, days }, null, 1) + "\n");
console.log(`${days.length} days -> ${OUT}`);
