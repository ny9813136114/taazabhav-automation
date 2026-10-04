// Tier C item 12 (SEO competitor-analysis doc) — a small, honest evergreen
// "Learn" section, built 22 Sep 2026. Scoped down from the original
// ChatGPT-proposed 8-article batch to these 4, each deliberately tied to a
// feature that's already live elsewhere on the site (MSP comparison pages,
// commodity+state pages, the Mandi Spread Radar) rather than written as
// generic filler — see the build brief for the full reasoning. The 4th
// (e-NAM) was added later the same day, once the strategist's build order
// reached it — its stats were verified fresh, separately, right before
// writing (see that article's own note below), not carried over untouched
// from the 3rd article's earlier, shallower e-NAM mention.
//
// English-primary with the Hindi term shown alongside, matching the
// convention already decided for commodity page titles (the competitor-gap
// batch's decision #2 — English-first, Hindi in parentheses, not a
// Hindi-first or fully bilingual treatment) rather than introducing a
// second content pattern for just this section.
//
// Facts used here (MSP crop count, e-NAM mandi/state/farmer counts) were
// verified against PIB press releases and enam.gov.in on 22 Sep 2026 before
// writing, not asserted from general knowledge — see the build brief.
//
// Hindi fields (dekHi, bodyHi, faqsHi, relatedHi) added 23 Sep 2026
// alongside the Learn pages' toggle. Unlike every other page type on this
// site, the Learn articles are genuinely hand-written long-form content —
// not templated strings or numbers plugged into a sentence — so the Hindi
// versions are full parallel translations, not a generator function.
// Numbers, crop names, and the English title/hindiTitle pairing are
// deliberately kept identical to the English version in every translated
// field (same convention as the rest of the site: real data is never
// re-derived per language, only the surrounding prose is).

export type LearnBlock =
  | { type: "p"; text: string }
  | { type: "h2"; text: string }
  | { type: "ul"; items: string[] };

export type LearnArticle = {
  slug: string;
  title: string; // page <title> / H1 — do not hardcode "| TaazaBhav", layout.tsx's template already appends it
  hindiTitle: string; // shown next to the English title, same pattern as "Onion (Pyaj)"
  description: string; // meta description — English only, same as every other page's <meta>
  dek: string; // one-line summary under the H1
  dekHi: string;
  datePublished: string; // ISO date, ymd
  dateModified?: string; // ISO date, ymd — set when an article gets a real content update
  body: LearnBlock[];
  bodyHi: LearnBlock[];
  faqs: { q: string; a: string }[];
  faqsHi: { q: string; a: string }[];
  related: { label: string; href: string }[];
  relatedHi: { label: string; href: string }[]; // same href order/values as `related`, label only
};

export const LEARN_ARTICLES: LearnArticle[] = [
  {
    slug: "what-is-mandi-bhav",
    title: "What Is Mandi Bhav? A Plain-Language Guide to India's Daily Market Prices",
    hindiTitle: "मंडी भाव",
    description:
      "What \"mandi bhav\" actually means, how a mandi price is discovered each day, and what the min/max/modal price on TaazaBhav stand for — explained plainly.",
    dek: "\"Mandi bhav\" shows up in the news, in WhatsApp forwards, in everyday conversation. Here's what the number actually means and where it comes from.",
    dekHi:
      "\"मंडी भाव\" खबरों में, व्हाट्सएप फॉरवर्ड में, रोज़मर्रा की बातचीत में सुनने को मिलता है। यहां बताया गया है कि यह नंबर असल में क्या मतलब रखता है और कहां से आता है।",
    datePublished: "2026-09-22",
    body: [
      { type: "h2", text: "Mandi bhav, in one sentence" },
      {
        type: "p",
        text: "Mandi bhav (मंडी भाव) literally means \"market rate\" — the price a crop actually sold for at a mandi, the regulated wholesale market where farmers, traders, and commission agents buy and sell agricultural produce. It isn't a government-fixed number (that's MSP, a different thing — see the next article) and it isn't a retail price either. It's the wholesale rate discovered fresh, market by market, day by day.",
      },
      { type: "h2", text: "Where the number actually comes from" },
      {
        type: "p",
        text: "Every mandi in India operates under its state's Agricultural Produce Market Committee (APMC) framework. Produce arrives at the mandi yard each morning, buyers and commission agents inspect the lots, and prices are settled through open bidding — historically an in-person auction, increasingly also through e-NAM's online bidding where a mandi has adopted it (more on that in the third article). Each mandi then reports what it actually traded that day to Agmarknet, the Ministry of Agriculture & Farmers Welfare's official price-reporting system, which publishes it as open data on data.gov.in. That's the exact same government dataset TaazaBhav pulls from — nothing on this site is scraped, estimated, or manually typed in.",
      },
      { type: "h2", text: "Min, max, and modal price — what the three numbers mean" },
      {
        type: "p",
        text: "For a given commodity at a given mandi on a given day, Agmarknet reports three prices, not one, because not every lot of the same crop sells for the same amount — quality and grade vary within a single day's arrivals:",
      },
      {
        type: "ul",
        items: [
          "Min price — the lowest price any lot of that commodity actually sold for that day (usually the weakest quality/grade).",
          "Max price — the highest price any lot sold for (usually the best quality/grade).",
          "Modal price — the price most transactions actually settled at. This is the single number people usually mean when they say \"today's rate,\" and it's what TaazaBhav highlights as the headline price on every commodity page.",
        ],
      },
      { type: "h2", text: "Per quintal vs per kg" },
      {
        type: "p",
        text: "Agmarknet reports everything per quintal (100 kg) — the standard wholesale unit in Indian mandis. TaazaBhav also shows the same range converted to per-kg, since that's the unit most people actually think in day to day; it's a straight ÷100 conversion of the real reported price, not a separate figure.",
      },
      { type: "h2", text: "How often it changes" },
      {
        type: "p",
        text: "TaazaBhav's pipeline pulls fresh data from Agmarknet's public API three times a day, and every page shows both a relative freshness badge (\"updated 2h ago\") and an absolute timestamp, so it's always clear how current a given number is rather than leaving that to guesswork.",
      },
    ],
    bodyHi: [
      { type: "h2", text: "मंडी भाव, एक वाक्य में" },
      {
        type: "p",
        text: "मंडी भाव का शाब्दिक अर्थ है \"बाज़ार दर\" — वह कीमत जिस पर कोई फसल मंडी में असल में बिकी, यानी वह नियमित थोक बाज़ार जहां किसान, व्यापारी और कमीशन एजेंट कृषि उपज खरीदते-बेचते हैं। यह सरकार द्वारा तय कोई निश्चित आंकड़ा नहीं है (वह एमएसपी है, एक अलग चीज़ — अगला लेख देखें) और न ही यह खुदरा कीमत है। यह वह थोक दर है जो हर मंडी में, हर दिन, नए सिरे से तय होती है।",
      },
      { type: "h2", text: "यह नंबर असल में कहां से आता है" },
      {
        type: "p",
        text: "भारत की हर मंडी अपने राज्य के कृषि उपज मंडी समिति (एपीएमसी) ढांचे के तहत काम करती है। हर सुबह उपज मंडी प्रांगण में पहुंचती है, खरीदार और कमीशन एजेंट लॉट का निरीक्षण करते हैं, और कीमतें खुली बोली के ज़रिए तय होती हैं — परंपरागत रूप से प्रत्यक्ष नीलामी, और जहां मंडी ने अपनाया है वहां ई-नाम की ऑनलाइन बोली के ज़रिए भी (इस पर और जानकारी तीसरे लेख में)। इसके बाद हर मंडी उस दिन जो असल कारोबार हुआ, वह कृषि एवं किसान कल्याण मंत्रालय की आधिकारिक मूल्य-रिपोर्टिंग प्रणाली एगमार्कनेट को भेजती है, जो इसे data.gov.in पर खुले डेटा के रूप में प्रकाशित करती है। यह वही सरकारी डेटासेट है जिससे TaazaBhav डेटा लेता है — इस साइट पर कुछ भी स्क्रैप, अनुमानित या मैन्युअली टाइप नहीं किया जाता।",
      },
      { type: "h2", text: "न्यूनतम, अधिकतम और मोडल भाव — तीन नंबरों का मतलब" },
      {
        type: "p",
        text: "किसी एक मंडी में, किसी एक दिन, किसी एक वस्तु के लिए एगमार्कनेट एक नहीं बल्कि तीन कीमतें दर्शाता है, क्योंकि एक ही फसल के हर लॉट की कीमत एक जैसी नहीं होती — एक ही दिन आई उपज में भी गुणवत्ता और ग्रेड अलग-अलग होते हैं:",
      },
      {
        type: "ul",
        items: [
          "न्यूनतम भाव — उस दिन उस वस्तु के किसी भी लॉट की सबसे कम बिकी कीमत (आमतौर पर सबसे कमज़ोर गुणवत्ता/ग्रेड)।",
          "अधिकतम भाव — किसी भी लॉट की सबसे ज़्यादा बिकी कीमत (आमतौर पर सबसे बेहतर गुणवत्ता/ग्रेड)।",
          "मोडल भाव — वह कीमत जिस पर सबसे ज़्यादा सौदे तय हुए। जब लोग \"आज का भाव\" कहते हैं तो आमतौर पर यही एक नंबर उनका मतलब होता है, और TaazaBhav हर वस्तु पेज पर इसी को मुख्य भाव के रूप में दिखाता है।",
        ],
      },
      { type: "h2", text: "प्रति क्विंटल बनाम प्रति किलो" },
      {
        type: "p",
        text: "एगमार्कनेट हर आंकड़ा प्रति क्विंटल (100 किलो) में दर्शाता है — भारतीय मंडियों में यही मानक थोक इकाई है। TaazaBhav वही रेंज प्रति किलो में बदलकर भी दिखाता है, क्योंकि रोज़मर्रा में ज़्यादातर लोग इसी इकाई में सोचते हैं; यह असल रिपोर्ट की गई कीमत का सीधा ÷100 रूपांतरण है, कोई अलग आंकड़ा नहीं।",
      },
      { type: "h2", text: "यह कितनी बार बदलता है" },
      {
        type: "p",
        text: "TaazaBhav की पाइपलाइन दिन में तीन बार एगमार्कनेट के सार्वजनिक एपीआई से ताज़ा डेटा खींचती है, और हर पेज पर एक सापेक्ष ताज़गी बैज (\"2 घंटे पहले अपडेट\") के साथ-साथ पूर्ण समय-मुहर भी दिखाई जाती है, ताकि यह हमेशा स्पष्ट रहे कि कोई आंकड़ा कितना ताज़ा है — इसे अंदाज़े पर नहीं छोड़ा जाता।",
      },
    ],
    faqs: [
      {
        q: "Is mandi bhav the same everywhere in India for the same crop?",
        a: "No — it's a local number. The same crop can trade at meaningfully different prices in different mandis on the same day, because each mandi is its own local market. See the third article in this series for why.",
      },
      {
        q: "Is the modal price what a farmer actually receives?",
        a: "It's what the mandi reports as the most common settled price that day. What an individual farmer actually nets can differ slightly depending on the exact grade of their lot and any commission/handling deductions specific to that transaction.",
      },
      {
        q: "Where does TaazaBhav's data come from?",
        a: "The Government of India's official Agmarknet / data.gov.in open dataset, pulled through their public API three times a day — the same source government agencies and researchers use.",
      },
    ],
    faqsHi: [
      {
        q: "क्या पूरे भारत में एक ही फसल का मंडी भाव हर जगह समान होता है?",
        a: "नहीं — यह एक स्थानीय आंकड़ा है। एक ही फसल एक ही दिन अलग-अलग मंडियों में काफी अलग कीमतों पर बिक सकती है, क्योंकि हर मंडी अपने आप में एक स्थानीय बाज़ार है। वजह जानने के लिए इस सीरीज़ का तीसरा लेख देखें।",
      },
      {
        q: "क्या मोडल भाव वही है जो किसान को असल में मिलता है?",
        a: "यह वह कीमत है जिसे मंडी उस दिन सबसे आम तय भाव के रूप में दर्शाती है। किसी किसान को असल में जो राशि मिलती है वह उसके लॉट के सटीक ग्रेड और उस सौदे से जुड़ी कमीशन/हैंडलिंग कटौती के आधार पर थोड़ी अलग हो सकती है।",
      },
      {
        q: "TaazaBhav का डेटा कहां से आता है?",
        a: "भारत सरकार के आधिकारिक एगमार्कनेट / data.gov.in खुले डेटासेट से, जिसे दिन में तीन बार उनके सार्वजनिक एपीआई के ज़रिए लिया जाता है — यही स्रोत सरकारी एजेंसियां और शोधकर्ता भी इस्तेमाल करते हैं।",
      },
    ],
    related: [
      { label: "See today's Onion mandi bhav", href: "/mandi-bhav/onion" },
      { label: "Browse mandi bhav by state", href: "/mandi-bhav/state/punjab" },
      { label: "MSP vs Mandi Bhav: what's the difference?", href: "/learn/msp-vs-mandi-bhav" },
    ],
    relatedHi: [
      { label: "आज का प्याज़ मंडी भाव देखें", href: "/mandi-bhav/onion" },
      { label: "राज्य अनुसार मंडी भाव देखें", href: "/mandi-bhav/state/punjab" },
      { label: "एमएसपी बनाम मंडी भाव: क्या अंतर है?", href: "/learn/msp-vs-mandi-bhav" },
    ],
  },
  {
    slug: "msp-vs-mandi-bhav",
    title: "MSP vs Mandi Bhav: What's the Difference?",
    hindiTitle: "एमएसपी और मंडी भाव में अंतर",
    description:
      "MSP and mandi bhav both get called \"the price\" — but they answer different questions. Here's how MSP is actually set, which crops have one, and why a mandi price can legitimately trade below it.",
    dek: "Two numbers, often confused. One is a government-guaranteed floor set once or twice a year; the other is what a market actually paid today.",
    dekHi:
      "दो आंकड़े, जो अक्सर उलझा देते हैं। एक सरकार द्वारा गारंटीशुदा न्यूनतम भाव है जो साल में एक या दो बार तय होता है; दूसरा वह है जो आज किसी बाज़ार ने असल में चुकाया।",
    datePublished: "2026-09-22",
    body: [
      { type: "h2", text: "Two different numbers, often confused" },
      {
        type: "p",
        text: "Minimum Support Price (MSP) and mandi bhav both get talked about as \"the price\" of a crop, which is exactly why they get mixed up — but they answer different questions. MSP is a promise: the floor price the government guarantees it will pay for a fixed list of crops, set once or twice a year. Mandi bhav is a fact: what a specific market actually paid for a specific lot on a specific day, discovered fresh through bidding. A crop's mandi bhav moves daily with supply and demand; its MSP, once announced for a season, doesn't move until the next announcement.",
      },
      { type: "h2", text: "How MSP is actually set" },
      {
        type: "p",
        text: "MSP isn't set arbitrarily. The Commission for Agricultural Costs & Prices (CACP) recommends a price for each covered crop based on the cost of production, demand-supply conditions, and domestic/international price trends, after consulting state governments; the Cabinet Committee on Economic Affairs (CCEA) then approves it. Since the 2018-19 season, the government's stated formula has kept MSP at a minimum of 1.5 times the all-India weighted average cost of production — a built-in 50% margin over cost, at least on paper. MSPs are announced separately for the two main cropping seasons: Kharif (the monsoon-sown crops — paddy, cotton, soyabean, and others) and Rabi (the winter-sown crops — wheat, mustard, and others).",
      },
      { type: "h2", text: "Which crops actually have one" },
      {
        type: "p",
        text: "Only 22 crops nationally carry an official MSP, plus two more (Toria and de-husked coconut) whose price is derived from a related covered crop rather than set independently. That's it — nothing else. Most fruits and vegetables, including staples like onion, potato, and tomato, are deliberately outside the scheme, mainly because they're too perishable for the government procurement model MSP relies on. That's exactly why TaazaBhav shows an explicit \"not MSP-covered\" note on those commodity pages instead of silently leaving the section out — it's a real, correct answer, not missing data.",
      },
      { type: "h2", text: "Why a mandi price can legitimately trade below MSP" },
      {
        type: "p",
        text: "This is the part that trips people up most: MSP is a guarantee, but it's only actually paid out at official government procurement centres, and only during notified procurement windows — not automatically at every mandi, every day. A farmer selling in the open market on an ordinary day, at a mandi where procurement isn't currently active, can genuinely receive less than MSP for a perfectly normal, legal transaction. That doesn't make the MSP scheme meaningless, but it does mean a below-MSP mandi price is a real, honest distress-sale signal worth paying attention to — not necessarily a policy failure, but not nothing either.",
      },
      {
        type: "p",
        text: "TaazaBhav's below-MSP comparison pages exist specifically to make this visible, crop by crop: for every MSP-covered commodity, they rank which markets are trading below the government floor today, by how much, right now — something no static price table shows on its own.",
      },
    ],
    bodyHi: [
      { type: "h2", text: "दो अलग आंकड़े, जो अक्सर उलझा देते हैं" },
      {
        type: "p",
        text: "न्यूनतम समर्थन मूल्य (एमएसपी) और मंडी भाव दोनों को अक्सर किसी फसल की \"कीमत\" कहा जाता है, और इसी वजह से लोग इन्हें आपस में मिला देते हैं — लेकिन ये अलग-अलग सवालों के जवाब हैं। एमएसपी एक वादा है: तय फसलों की सूची के लिए सरकार जो न्यूनतम कीमत चुकाने की गारंटी देती है, जो साल में एक या दो बार तय होती है। मंडी भाव एक तथ्य है: किसी खास बाज़ार ने किसी खास दिन किसी खास लॉट के लिए बोली के ज़रिए जो कीमत असल में चुकाई। किसी फसल का मंडी भाव आपूर्ति और मांग के साथ रोज़ बदलता है; उसका एमएसपी, एक बार सीज़न के लिए घोषित होने के बाद, अगली घोषणा तक नहीं बदलता।",
      },
      { type: "h2", text: "एमएसपी असल में कैसे तय होता है" },
      {
        type: "p",
        text: "एमएसपी मनमाने ढंग से तय नहीं होता। कृषि लागत एवं मूल्य आयोग (सीएसीपी) राज्य सरकारों से सलाह लेने के बाद, उत्पादन लागत, मांग-आपूर्ति की स्थिति और घरेलू/अंतरराष्ट्रीय मूल्य रुझानों के आधार पर हर तय फसल के लिए एक कीमत की सिफारिश करता है; इसके बाद आर्थिक मामलों की मंत्रिमंडलीय समिति (सीसीईए) इसे मंज़ूरी देती है। 2018-19 सीज़न से, सरकार के बताए फॉर्मूले के अनुसार एमएसपी को अखिल भारतीय भारित औसत उत्पादन लागत के कम से कम 1.5 गुना पर रखा गया है — यानी कागज़ पर कम से कम 50% का मार्जिन। एमएसपी दो मुख्य फसल सीज़न के लिए अलग-अलग घोषित होता है: खरीफ (मानसून में बोई जाने वाली फसलें — धान, कपास, सोयाबीन आदि) और रबी (सर्दियों में बोई जाने वाली फसलें — गेहूं, सरसों आदि)।",
      },
      { type: "h2", text: "किन फसलों के लिए यह असल में लागू होता है" },
      {
        type: "p",
        text: "राष्ट्रीय स्तर पर सिर्फ 22 फसलों का आधिकारिक एमएसपी होता है, साथ ही दो और (तोरिया और छिलका उतारा नारियल) जिनकी कीमत किसी संबंधित तय फसल से निकाली जाती है, अलग से तय नहीं होती। बस इतना ही — इससे ज़्यादा कुछ नहीं। प्याज़, आलू और टमाटर जैसी अधिकतर सब्ज़ियां और फल जानबूझकर इस योजना से बाहर रखे गए हैं, मुख्य रूप से इसलिए क्योंकि वे उस सरकारी खरीद मॉडल के लिए बहुत जल्दी खराब हो जाते हैं जिस पर एमएसपी निर्भर करता है। यही वजह है कि TaazaBhav उन वस्तु पेजों पर चुपचाप वह सेक्शन हटाने के बजाय साफ़ \"एमएसपी-कवर्ड नहीं\" नोट दिखाता है — यह एक असल, सही जवाब है, कोई छूटा हुआ डेटा नहीं।",
      },
      { type: "h2", text: "मंडी भाव एमएसपी से नीचे वाजिब तौर पर क्यों हो सकता है" },
      {
        type: "p",
        text: "यहीं पर सबसे ज़्यादा भ्रम होता है: एमएसपी एक गारंटी है, लेकिन यह असल में सिर्फ आधिकारिक सरकारी खरीद केंद्रों पर, और सिर्फ अधिसूचित खरीद अवधि के दौरान चुकाई जाती है — हर मंडी में, हर दिन अपने आप नहीं। किसी सामान्य दिन खुले बाज़ार में बेचने वाला किसान, ऐसी मंडी में जहां फिलहाल खरीद सक्रिय नहीं है, एक पूरी तरह सामान्य और वैध सौदे में एमएसपी से कम भी पा सकता है। इसका मतलब यह नहीं कि एमएसपी योजना बेमानी है, लेकिन इसका मतलब यह ज़रूर है कि एमएसपी से नीचे का मंडी भाव एक असल, ईमानदार संकट-बिक्री संकेत है जिस पर ध्यान देना ज़रूरी है — यह ज़रूरी नहीं कि नीति की नाकामी हो, लेकिन बेमानी भी नहीं है।",
      },
      {
        type: "p",
        text: "TaazaBhav के एमएसपी-से-नीचे तुलना पेज खासतौर पर इसे फसल-दर-फसल दिखाने के लिए बनाए गए हैं: हर एमएसपी-कवर्ड वस्तु के लिए, वे बताते हैं कि आज कौन सी मंडियां सरकारी न्यूनतम भाव से नीचे कारोबार कर रही हैं, कितना नीचे, अभी इसी वक्त — यह ऐसी जानकारी है जो कोई सामान्य स्थिर कीमत तालिका अपने आप नहीं दिखा सकती।",
      },
    ],
    faqs: [
      {
        q: "Does every crop have an MSP?",
        a: "No — only 22 crops nationally (plus two whose price is derived from a related crop). Most fruits and vegetables, including onion, potato, and tomato, are not MSP-covered.",
      },
      {
        q: "If a mandi price is below MSP, does that mean the farmer got cheated?",
        a: "Not necessarily. MSP is only guaranteed at official government procurement centres during notified windows, not at every mandi on every day. A below-MSP price in the open market is a real signal worth noticing, but it doesn't by itself mean anything went wrong.",
      },
      {
        q: "How often does MSP change?",
        a: "Once or twice a year — separately for the Kharif and Rabi marketing seasons — not daily like mandi bhav.",
      },
      {
        q: "Where can I see which markets are below MSP right now?",
        a: "TaazaBhav has a dedicated below-MSP comparison page for every MSP-covered commodity, linked from that commodity's main mandi bhav page.",
      },
    ],
    faqsHi: [
      {
        q: "क्या हर फसल का एमएसपी होता है?",
        a: "नहीं — राष्ट्रीय स्तर पर सिर्फ 22 फसलों का (साथ ही दो और जिनकी कीमत किसी संबंधित फसल से निकाली जाती है)। प्याज़, आलू और टमाटर समेत अधिकतर फल-सब्ज़ियां एमएसपी-कवर्ड नहीं हैं।",
      },
      {
        q: "अगर मंडी भाव एमएसपी से नीचे है, तो क्या इसका मतलब किसान के साथ धोखा हुआ?",
        a: "ज़रूरी नहीं। एमएसपी की गारंटी सिर्फ आधिकारिक सरकारी खरीद केंद्रों पर, अधिसूचित अवधि के दौरान होती है, हर मंडी में हर दिन नहीं। खुले बाज़ार में एमएसपी से नीचे की कीमत एक असल संकेत है जिस पर ध्यान देना चाहिए, लेकिन इसका अपने आप यह मतलब नहीं कि कुछ गलत हुआ।",
      },
      {
        q: "एमएसपी कितनी बार बदलता है?",
        a: "साल में एक या दो बार — खरीफ और रबी विपणन सीज़न के लिए अलग-अलग — मंडी भाव की तरह रोज़ नहीं।",
      },
      {
        q: "मैं अभी कौन सी मंडियां एमएसपी से नीचे हैं, यह कहां देख सकता हूं?",
        a: "TaazaBhav पर हर एमएसपी-कवर्ड वस्तु के लिए एक अलग एमएसपी-से-नीचे तुलना पेज है, जिसका लिंक उस वस्तु के मुख्य मंडी भाव पेज पर मिलता है।",
      },
    ],
    related: [
      { label: "Wheat: markets trading below MSP today", href: "/mandi-bhav/wheat/msp-comparison" },
      { label: "Paddy(Common): markets trading below MSP today", href: "/mandi-bhav/paddycommon/msp-comparison" },
      { label: "What is mandi bhav?", href: "/learn/what-is-mandi-bhav" },
    ],
    relatedHi: [
      { label: "गेहूं: आज एमएसपी से नीचे कारोबार करने वाली मंडियां", href: "/mandi-bhav/wheat/msp-comparison" },
      { label: "धान(सामान्य): आज एमएसपी से नीचे कारोबार करने वाली मंडियां", href: "/mandi-bhav/paddycommon/msp-comparison" },
      { label: "मंडी भाव क्या है?", href: "/learn/what-is-mandi-bhav" },
    ],
  },
  {
    slug: "why-mandi-prices-differ",
    title: "Why Does the Same Crop Cost Different Amounts in Different Mandis?",
    hindiTitle: "अलग-अलग मंडियों में भाव अलग क्यों",
    description:
      "There's no single national price for a crop in India — each mandi runs its own local market. Here's what actually causes the same commodity to trade at different prices across markets on the same day.",
    dek: "There's no such thing as \"the\" national price for a crop — only what each mandi actually paid today. Here's what drives the gap.",
    dekHi:
      "किसी फसल का कोई \"एक\" राष्ट्रीय भाव नहीं होता — सिर्फ यह होता है कि आज हर मंडी ने असल में क्या चुकाया। यहां जानिए इस अंतर की वजह।",
    datePublished: "2026-09-22",
    body: [
      { type: "h2", text: "The short answer: it's a local market, not one national price" },
      {
        type: "p",
        text: "Every mandi runs its own daily auction, with its own buyers, its own arrivals, and its own local conditions. There's no single central authority setting one national price for onion or wheat that every mandi then follows — by design, the price is discovered locally, market by market, which is exactly why TaazaBhav's Mandi Spread Radar (on the homepage) can regularly find the same crop trading hundreds or even thousands of rupees apart per quintal, on the very same day, in different states.",
      },
      { type: "h2", text: "The real factors that move the number" },
      {
        type: "ul",
        items: [
          "Arrivals that day — more supply reaching one mandi that morning tends to push its price down locally, independent of what any other mandi is doing.",
          "Quality and grade — the actual lots that arrived, not an abstract average; a mandi that received mostly premium-grade produce that day will show a higher modal price.",
          "Distance and freight cost to the nearest big consuming market — a mandi closer to a major city can often net a better price than a similar mandi in a more remote growing belt, partly because less of the final value gets eaten by transport.",
          "State-specific market fees and commission — the mandi tax (market fee) and the commission agent's (arthiya's) margin are both set at the state/mandi level and genuinely differ from one state to another, which shows up in the net price.",
          "Perishability and urgency — a vegetable that must sell today because it won't keep is priced very differently from a stored grain that can wait for a better bid tomorrow.",
        ],
      },
      { type: "h2", text: "Isn't e-NAM supposed to fix this?" },
      {
        type: "p",
        text: "e-NAM (National Agriculture Market), the government's online trading platform, genuinely is a real step toward exactly this — as of March 2026 it had integrated 1,656 mandis across 23 states and 4 union territories, with over 1.8 crore farmers registered and roughly ₹4.84 lakh crore traded cumulatively since it launched in 2016. It lets registered traders bid on lots listed at any connected mandi, not just the one they're physically standing in, and pays farmers directly into their bank account.",
      },
      {
        type: "p",
        text: "What it hasn't fully solved is the underlying local economics: quality assaying and grading at most connected mandis is still done locally, not against one uniform national standard, so a buyer in another state is bidding partly on trust in that mandi's own grading. And freight still has to be paid by someone — a genuinely better price two states away is only worth taking if what's left after transport is actually more than selling locally. e-NAM makes price discovery far more visible across markets than it used to be; it doesn't erase the local supply, freight, and grading factors above that still shape what a farmer actually walks away with.",
      },
      { type: "h2", text: "What TaazaBhav's Mandi Spread Radar is for" },
      {
        type: "p",
        text: "The homepage's Mandi Spread Radar exists to make this visible in practice — surfacing, commodity by commodity, which markets are paying noticeably more or less for the same crop on the same day. It's shown with the same honesty as everything else on this site: a wide spread is real information, but freight and logistics will eat into it before it's real margin for anyone trying to act on it across states.",
      },
    ],
    bodyHi: [
      { type: "h2", text: "संक्षिप्त जवाब: यह एक स्थानीय बाज़ार है, कोई एक राष्ट्रीय भाव नहीं" },
      {
        type: "p",
        text: "हर मंडी अपनी खुद की रोज़ाना नीलामी चलाती है, अपने खरीदारों, अपनी आवक और अपनी स्थानीय परिस्थितियों के साथ। कोई एक केंद्रीय प्राधिकरण प्याज़ या गेहूं के लिए एक राष्ट्रीय भाव तय नहीं करता जिसे हर मंडी माने — डिज़ाइन के हिसाब से ही, कीमत हर बाज़ार में अलग-अलग, स्थानीय स्तर पर तय होती है, और यही वजह है कि TaazaBhav का मंडी स्प्रेड रडार (होमपेज पर) अक्सर पाता है कि एक ही फसल एक ही दिन, अलग-अलग राज्यों में, प्रति क्विंटल सैकड़ों या हज़ारों रुपये के अंतर पर बिक रही है।",
      },
      { type: "h2", text: "वे असल कारण जो यह आंकड़ा तय करते हैं" },
      {
        type: "ul",
        items: [
          "उस दिन की आवक — किसी मंडी में सुबह ज़्यादा आपूर्ति पहुंचने से आमतौर पर वहां का भाव स्थानीय स्तर पर नीचे चला जाता है, चाहे बाकी मंडियों में कुछ भी हो रहा हो।",
          "गुणवत्ता और ग्रेड — जो असल लॉट पहुंचे, कोई काल्पनिक औसत नहीं; जिस मंडी में उस दिन ज़्यादातर बेहतरीन ग्रेड की उपज आई, वहां मोडल भाव ज़्यादा दिखेगा।",
          "निकटतम बड़े उपभोक्ता बाज़ार से दूरी और ढुलाई लागत — किसी बड़े शहर के नज़दीक की मंडी अक्सर किसी दूरदराज़ उत्पादक इलाके की समान मंडी से बेहतर कीमत दिला सकती है, क्योंकि अंतिम कीमत में से परिवहन में कम हिस्सा जाता है।",
          "राज्य-विशेष मंडी शुल्क और कमीशन — मंडी टैक्स (मार्केट फीस) और कमीशन एजेंट (आढ़तिया) का मार्जिन दोनों राज्य/मंडी स्तर पर तय होते हैं और एक राज्य से दूसरे राज्य में वाकई अलग होते हैं, जो अंतिम कीमत में दिखता है।",
          "खराब होने की दर और तात्कालिकता — जो सब्ज़ी आज ही बिकनी ज़रूरी है क्योंकि वह टिकेगी नहीं, उसकी कीमत उस भंडारित अनाज से बहुत अलग होती है जो कल बेहतर बोली का इंतज़ार कर सकता है।",
        ],
      },
      { type: "h2", text: "क्या ई-नाम को यह ठीक नहीं करना चाहिए था?" },
      {
        type: "p",
        text: "ई-नाम (राष्ट्रीय कृषि बाज़ार), सरकार का ऑनलाइन ट्रेडिंग प्लेटफॉर्म, वाकई इसी दिशा में एक असली कदम है — मार्च 2026 तक इसमें 23 राज्यों और 4 केंद्रशासित प्रदेशों की 1,656 मंडियां जुड़ चुकी थीं, 1.8 करोड़ से ज़्यादा किसान पंजीकृत थे, और 2016 में शुरुआत के बाद से कुल मिलाकर करीब ₹4.84 लाख करोड़ का कारोबार हो चुका था। यह पंजीकृत व्यापारियों को किसी भी जुड़ी हुई मंडी में सूचीबद्ध लॉट पर बोली लगाने देता है, न कि सिर्फ उस मंडी में जहां वे खुद मौजूद हैं, और किसानों को सीधे उनके बैंक खाते में भुगतान करता है।",
      },
      {
        type: "p",
        text: "जो चीज़ यह पूरी तरह हल नहीं कर पाया है वह है अंतर्निहित स्थानीय अर्थशास्त्र: ज़्यादातर जुड़ी मंडियों में गुणवत्ता जांच और ग्रेडिंग अब भी स्थानीय स्तर पर होती है, किसी एक समान राष्ट्रीय मानक के मुकाबले नहीं, इसलिए दूसरे राज्य का खरीदार आंशिक रूप से उस मंडी की खुद की ग्रेडिंग पर भरोसा करके बोली लगाता है। और ढुलाई का खर्च किसी न किसी को उठाना ही पड़ता है — दो राज्य दूर की वाकई बेहतर कीमत तभी फायदेमंद है जब परिवहन के बाद बचा हिस्सा स्थानीय बिक्री से असल में ज़्यादा हो। ई-नाम ने बाज़ारों के बीच मूल्य पता लगाना पहले से कहीं ज़्यादा साफ़ बना दिया है; लेकिन यह ऊपर बताए गए स्थानीय आपूर्ति, ढुलाई और ग्रेडिंग जैसे कारकों को खत्म नहीं करता, जो अब भी तय करते हैं कि किसान के हाथ असल में कितना आता है।",
      },
      { type: "h2", text: "TaazaBhav का मंडी स्प्रेड रडार किसलिए है" },
      {
        type: "p",
        text: "होमपेज का मंडी स्प्रेड रडार इसे व्यावहारिक रूप से दिखाने के लिए बनाया गया है — वस्तु-दर-वस्तु यह उजागर करते हुए कि कौन सी मंडियां एक ही दिन एक ही फसल के लिए ध्यान देने लायक ज़्यादा या कम कीमत दे रही हैं। इसे इस साइट की बाकी चीज़ों जैसी ही ईमानदारी से दिखाया जाता है: बड़ा अंतर असली जानकारी है, लेकिन राज्यों के आर-पार इस पर अमल करने से पहले ढुलाई और लॉजिस्टिक्स उसका काफी हिस्सा खा जाएंगे, इससे पहले कि वह किसी के लिए असली मुनाफा बने।",
      },
    ],
    faqs: [
      {
        q: "Why isn't there just one national price for a crop?",
        a: "Because Indian mandis operate as independent local markets — each one discovers its own price daily through its own buyers, arrivals, and bidding, rather than following one centrally fixed number.",
      },
      {
        q: "Does e-NAM mean I can just sell to whichever mandi is paying the most?",
        a: "In principle it moves toward that, and it's genuinely expanded — 1,656 mandis were connected as of March 2026 — but local quality grading and freight costs still mean the best-looking price elsewhere isn't automatically the best deal after those are accounted for.",
      },
      {
        q: "Where can I compare prices for the same crop across states?",
        a: "TaazaBhav's Mandi Spread Radar on the homepage, and each commodity's state-by-state pages, both show this directly.",
      },
    ],
    faqsHi: [
      {
        q: "किसी फसल का सिर्फ एक राष्ट्रीय भाव क्यों नहीं होता?",
        a: "क्योंकि भारतीय मंडियां स्वतंत्र स्थानीय बाज़ारों की तरह काम करती हैं — हर एक अपने खरीदारों, आवक और बोली के ज़रिए रोज़ अपनी खुद की कीमत तय करती है, न कि किसी केंद्रीय रूप से तय आंकड़े का पालन करती है।",
      },
      {
        q: "क्या ई-नाम का मतलब है कि मैं जो मंडी सबसे ज़्यादा भाव दे, वहीं बेच सकता हूं?",
        a: "सिद्धांत रूप में यह उसी दिशा में बढ़ता है, और इसका दायरा वाकई बढ़ा है — मार्च 2026 तक 1,656 मंडियां जुड़ी थीं — लेकिन स्थानीय गुणवत्ता ग्रेडिंग और ढुलाई लागत की वजह से कहीं और दिख रही सबसे अच्छी कीमत, उन्हें जोड़ने के बाद अपने आप सबसे अच्छा सौदा नहीं बन जाती।",
      },
      {
        q: "मैं एक ही फसल की कीमतों की राज्यों के बीच तुलना कहां कर सकता हूं?",
        a: "होमपेज पर TaazaBhav का मंडी स्प्रेड रडार, और हर वस्तु के राज्य-वार पेज, दोनों यह सीधे दिखाते हैं।",
      },
    ],
    related: [
      { label: "Browse mandi bhav by state", href: "/mandi-bhav/state/maharashtra" },
      { label: "MSP vs Mandi Bhav: what's the difference?", href: "/learn/msp-vs-mandi-bhav" },
      { label: "See today's Mandi Spread Radar", href: "/#mandi-spread-radar" },
      { label: "What is e-NAM and how does it actually work?", href: "/learn/what-is-enam" },
    ],
    relatedHi: [
      { label: "राज्य अनुसार मंडी भाव देखें", href: "/mandi-bhav/state/maharashtra" },
      { label: "एमएसपी बनाम मंडी भाव: क्या अंतर है?", href: "/learn/msp-vs-mandi-bhav" },
      { label: "आज का मंडी स्प्रेड रडार देखें", href: "/#mandi-spread-radar" },
      { label: "ई-नाम क्या है और यह असल में कैसे काम करता है?", href: "/learn/what-is-enam" },
    ],
  },
  {
    slug: "what-is-enam",
    title: "What Is e-NAM? How India's Online Mandi Trading Platform Actually Works",
    hindiTitle: "ई-नाम",
    description:
      "e-NAM (National Agriculture Market) in plain terms: how listing, quality assaying, online bidding, and direct payment actually work, how big the platform is as of March 2026, and what it hasn't fully solved.",
    dek: "The government's online mandi trading platform, explained step by step — registration to payment — with the current numbers, verified fresh, not repeated from memory.",
    dekHi:
      "सरकार का ऑनलाइन मंडी ट्रेडिंग प्लेटफॉर्म, चरण-दर-चरण समझाया गया — पंजीकरण से भुगतान तक — मौजूदा आंकड़ों के साथ, जो ताज़ा सत्यापित किए गए हैं, याददाश्त से नहीं दोहराए गए।",
    datePublished: "2026-09-22",
    body: [
      { type: "h2", text: "e-NAM, in one sentence" },
      {
        type: "p",
        text: "e-NAM (National Agriculture Market, ई-नाम) is the Government of India's online trading platform that connects mandis across the country into one electronic network, so a registered trader can bid on a lot listed at any connected mandi — not only the one they can physically walk into — and a farmer can get paid straight to their bank account without changing anything about how the mandi itself is run day to day. Launched in 2016, it's an overlay on the existing APMC mandi system described in the earlier articles in this series, not a replacement for it.",
      },
      { type: "h2", text: "How it actually works, step by step" },
      {
        type: "ul",
        items: [
          "Registration — a farmer, trader, commission agent, or Farmer Producer Organisation (FPO) registers once, either through the mandi's e-NAM help desk or the e-NAM mobile app, using standard KYC documents and a bank account.",
          "The lot arrives and gets assayed — produce is physically brought to the mandi as usual, and at mandis with an assaying facility, a sample is graded for quality before bidding opens, so bidders aren't relying purely on trust or a visual inspection.",
          "Online bidding — the lot is listed on the e-NAM portal, and registered buyers — including ones sitting at a different connected mandi — place bids electronically over a set bidding window, rather than only through an in-person auction.",
          "Sale confirmation — the mandi's licensed trader/commission agent confirms the winning bid, the same role they'd play in a conventional auction.",
          "Direct payment — payment moves electronically to the farmer's bank account via NEFT, RTGS, or UPI, rather than as cash handled through intermediaries.",
        ],
      },
      { type: "h2", text: "How big it actually is, as of March 2026" },
      {
        type: "p",
        text: "As of March 2026, e-NAM had integrated 1,656 mandis across 23 states and 4 union territories. Since its 2016 launch, over 1.80 crore farmers, 2.73 lakh traders, and 4,724 FPOs had registered on the platform, with roughly 13.25 crore tonnes traded cumulatively and a cumulative trade value of about ₹4.84 lakh crore — up from about ₹3.19 lakh crore as of 2024, which gives a sense of how fast participation has been growing rather than just how large the total is.",
      },
      { type: "h2", text: "What's built on top of the trading platform" },
      {
        type: "p",
        text: "Beyond listing-and-bidding, e-NAM now connects to a few adjacent pieces worth knowing about. The Platform of Platforms (PoP) links e-NAM to third-party logistics, warehousing, and financial-service providers, so a trade doesn't stop at \"sold\" — moving and storing the produce can be arranged through the same ecosystem. The electronic Negotiable Warehouse Receipt (e-NWR) system lets a farmer deposit produce in an accredited warehouse and get a digital receipt that itself can be used as loan collateral or sold — a way to avoid being forced to sell immediately at harvest, when prices are typically at their weakest. And the e-NAM mobile app carries price information for 247 commodities, on top of running trades, so it also functions as a straightforward price-discovery tool even for someone not actively buying or selling that day.",
      },
      { type: "h2", text: "What e-NAM hasn't fully solved" },
      {
        type: "p",
        text: "The bigger the network gets, the more this matters: quality assaying is still done locally, mandi by mandi, against each mandi's own grading practice rather than one uniform national standard — so a buyer bidding on a lot two states away is trusting that mandi's grading, not a nationally standardized certificate. And freight still has to be paid by someone; a better price shown on the platform at a distant mandi is only a real gain once transport cost is actually subtracted, which e-NAM's listing screen doesn't do for you. Neither of these makes e-NAM not worth using — connecting 1,656 mandis into one biddable network is a genuinely large logistical achievement — but they're the reason it hasn't simply erased the local price differences covered in the previous article.",
      },
    ],
    bodyHi: [
      { type: "h2", text: "ई-नाम, एक वाक्य में" },
      {
        type: "p",
        text: "ई-नाम (राष्ट्रीय कृषि बाज़ार) भारत सरकार का ऑनलाइन ट्रेडिंग प्लेटफॉर्म है जो देशभर की मंडियों को एक इलेक्ट्रॉनिक नेटवर्क में जोड़ता है, ताकि कोई पंजीकृत व्यापारी किसी भी जुड़ी हुई मंडी में सूचीबद्ध लॉट पर बोली लगा सके — न कि सिर्फ उस मंडी में जहां वह खुद जा सकता है — और किसान को सीधे उसके बैंक खाते में भुगतान मिल सके, बिना यह बदले कि मंडी खुद रोज़मर्रा में कैसे चलती है। 2016 में शुरू हुआ यह प्लेटफॉर्म, इस सीरीज़ के पहले लेखों में बताई गई मौजूदा एपीएमसी मंडी व्यवस्था के ऊपर एक परत है, उसकी जगह लेने वाला नहीं।",
      },
      { type: "h2", text: "यह असल में चरण-दर-चरण कैसे काम करता है" },
      {
        type: "ul",
        items: [
          "पंजीकरण — कोई किसान, व्यापारी, कमीशन एजेंट, या किसान उत्पादक संगठन (एफपीओ) मंडी के ई-नाम हेल्प डेस्क या ई-नाम मोबाइल ऐप के ज़रिए, मानक केवाईसी दस्तावेज़ों और बैंक खाते के साथ, एक बार पंजीकरण करता है।",
          "लॉट पहुंचता है और उसकी जांच होती है — उपज हमेशा की तरह मंडी में शारीरिक रूप से लाई जाती है, और जहां जांच की सुविधा है, वहां बोली शुरू होने से पहले एक नमूने की गुणवत्ता जांची जाती है, ताकि बोली लगाने वाले सिर्फ भरोसे या नज़र से देखकर अंदाज़ा न लगाएं।",
          "ऑनलाइन बोली — लॉट को ई-नाम पोर्टल पर सूचीबद्ध किया जाता है, और पंजीकृत खरीदार — जिनमें किसी दूसरी जुड़ी मंडी में बैठे खरीदार भी शामिल हैं — एक तय बोली अवधि में इलेक्ट्रॉनिक तरीके से बोली लगाते हैं, न कि सिर्फ प्रत्यक्ष नीलामी के ज़रिए।",
          "बिक्री की पुष्टि — मंडी का लाइसेंसी व्यापारी/कमीशन एजेंट जीतने वाली बोली की पुष्टि करता है, वही भूमिका जो वह पारंपरिक नीलामी में निभाता।",
          "सीधा भुगतान — भुगतान एनईएफटी, आरटीजीएस या यूपीआई के ज़रिए इलेक्ट्रॉनिक तरीके से सीधे किसान के बैंक खाते में जाता है, बिचौलियों के ज़रिए नकद के बजाय।",
        ],
      },
      { type: "h2", text: "मार्च 2026 तक यह असल में कितना बड़ा है" },
      {
        type: "p",
        text: "मार्च 2026 तक, ई-नाम में 23 राज्यों और 4 केंद्रशासित प्रदेशों की 1,656 मंडियां जुड़ चुकी थीं। 2016 में शुरुआत के बाद से, प्लेटफॉर्म पर 1.80 करोड़ से ज़्यादा किसान, 2.73 लाख व्यापारी और 4,724 एफपीओ पंजीकृत हो चुके थे, कुल मिलाकर करीब 13.25 करोड़ टन कारोबार हुआ और कुल कारोबार मूल्य करीब ₹4.84 लाख करोड़ रहा — जो 2024 में करीब ₹3.19 लाख करोड़ था, यानी यह सिर्फ कुल आंकड़े का नहीं बल्कि भागीदारी कितनी तेज़ी से बढ़ रही है, इसका भी अंदाज़ा देता है।",
      },
      { type: "h2", text: "ट्रेडिंग प्लेटफॉर्म के ऊपर क्या बनाया गया है" },
      {
        type: "p",
        text: "लिस्टिंग और बोली के अलावा, ई-नाम अब कुछ और जुड़ी चीज़ों से भी जुड़ा है जो जानने लायक हैं। प्लेटफॉर्म ऑफ प्लेटफॉर्म्स (पीओपी) ई-नाम को थर्ड-पार्टी लॉजिस्टिक्स, वेयरहाउसिंग और वित्तीय-सेवा प्रदाताओं से जोड़ता है, ताकि सौदा सिर्फ \"बिक गया\" पर न रुके — उपज को ले जाना और भंडारित करना भी उसी इकोसिस्टम के ज़रिए तय किया जा सके। इलेक्ट्रॉनिक निगोशिएबल वेयरहाउस रसीद (ई-एनडब्ल्यूआर) प्रणाली किसान को मान्यता प्राप्त गोदाम में उपज जमा करने और एक डिजिटल रसीद पाने देती है, जिसे खुद कर्ज़ की गारंटी के रूप में इस्तेमाल किया जा सकता है या बेचा जा सकता है — यह फसल कटाई के तुरंत बाद बेचने की मजबूरी से बचने का एक तरीका है, जब कीमतें आमतौर पर सबसे कमज़ोर होती हैं। और ई-नाम मोबाइल ऐप सौदे चलाने के अलावा 247 वस्तुओं की कीमत जानकारी भी रखता है, इसलिए यह उस दिन खरीद-बिक्री न कर रहे किसी व्यक्ति के लिए भी एक सीधा मूल्य-पता लगाने का ज़रिया बन जाता है।",
      },
      { type: "h2", text: "ई-नाम ने पूरी तरह क्या हल नहीं किया" },
      {
        type: "p",
        text: "नेटवर्क जितना बड़ा होता जाता है, यह बात उतनी ही मायने रखती है: गुणवत्ता जांच अब भी मंडी-दर-मंडी स्थानीय स्तर पर, हर मंडी के अपने ग्रेडिंग तरीके के हिसाब से होती है, किसी एक समान राष्ट्रीय मानक के मुकाबले नहीं — इसलिए दो राज्य दूर के लॉट पर बोली लगाने वाला खरीदार उस मंडी की ग्रेडिंग पर भरोसा कर रहा होता है, किसी राष्ट्रीय स्तर पर मानकीकृत प्रमाणपत्र पर नहीं। और ढुलाई का खर्च किसी न किसी को उठाना ही पड़ता है; किसी दूर की मंडी में प्लेटफॉर्म पर दिखती बेहतर कीमत तभी असली फायदा है जब परिवहन लागत असल में घटाई जाए, जो ई-नाम की लिस्टिंग स्क्रीन खुद नहीं करती। इनमें से कोई भी बात ई-नाम को बेकार नहीं बनाती — 1,656 मंडियों को एक बोली-योग्य नेटवर्क में जोड़ना वाकई एक बड़ी लॉजिस्टिक उपलब्धि है — लेकिन यही वजह है कि इसने पिछले लेख में बताए गए स्थानीय कीमत अंतर को पूरी तरह खत्म नहीं किया।",
      },
    ],
    faqs: [
      {
        q: "Who can register on e-NAM?",
        a: "Farmers, traders, commission agents, and Farmer Producer Organisations (FPOs) can all register, typically through a connected mandi's e-NAM help desk or the e-NAM mobile app, using standard KYC documents and a bank account.",
      },
      {
        q: "Does e-NAM replace the local mandi auction?",
        a: "No — it runs alongside the existing APMC mandi system. Produce still physically arrives at a mandi and is still handled by the mandi's licensed traders and commission agents; e-NAM adds electronic bidding (including from buyers at other connected mandis) and direct digital payment on top of that.",
      },
      {
        q: "How many mandis are actually connected?",
        a: "1,656 mandis across 23 states and 4 union territories, as of March 2026 — up from far fewer at launch in 2016. It's grown steadily, so this figure is worth treating as a point-in-time number rather than fixed.",
      },
      {
        q: "Does trading on e-NAM guarantee a farmer the best possible price?",
        a: "It widens who can bid on a lot, which tends to help price discovery, but it doesn't account for freight cost to a distant buyer or guarantee any particular price — quality assaying is still done locally, and a higher price shown on the platform isn't automatically a better net outcome once transport is factored in.",
      },
    ],
    faqsHi: [
      {
        q: "ई-नाम पर कौन पंजीकरण कर सकता है?",
        a: "किसान, व्यापारी, कमीशन एजेंट और किसान उत्पादक संगठन (एफपीओ) — सभी पंजीकरण कर सकते हैं, आमतौर पर किसी जुड़ी मंडी के ई-नाम हेल्प डेस्क या ई-नाम मोबाइल ऐप के ज़रिए, मानक केवाईसी दस्तावेज़ों और बैंक खाते के साथ।",
      },
      {
        q: "क्या ई-नाम स्थानीय मंडी नीलामी की जगह लेता है?",
        a: "नहीं — यह मौजूदा एपीएमसी मंडी व्यवस्था के साथ-साथ चलता है। उपज अब भी शारीरिक रूप से मंडी में पहुंचती है और मंडी के लाइसेंसी व्यापारियों व कमीशन एजेंटों द्वारा संभाली जाती है; ई-नाम इसके ऊपर इलेक्ट्रॉनिक बोली (दूसरी जुड़ी मंडियों के खरीदारों समेत) और सीधा डिजिटल भुगतान जोड़ता है।",
      },
      {
        q: "असल में कितनी मंडियां जुड़ी हुई हैं?",
        a: "मार्च 2026 तक, 23 राज्यों और 4 केंद्रशासित प्रदेशों की 1,656 मंडियां — 2016 में शुरुआत के समय की तुलना में कहीं ज़्यादा। यह लगातार बढ़ा है, इसलिए इस आंकड़े को स्थिर न मानकर एक समय-विशेष संख्या के रूप में देखना बेहतर है।",
      },
      {
        q: "क्या ई-नाम पर कारोबार करने से किसान को सबसे अच्छी कीमत की गारंटी मिलती है?",
        a: "यह किसी लॉट पर बोली लगाने वालों का दायरा बढ़ाता है, जिससे मूल्य तय करने में मदद मिलती है, लेकिन यह दूर के खरीदार तक ढुलाई की लागत का हिसाब नहीं रखता या किसी खास कीमत की गारंटी नहीं देता — गुणवत्ता जांच अब भी स्थानीय स्तर पर होती है, और प्लेटफॉर्म पर दिख रही ज़्यादा कीमत परिवहन जोड़ने के बाद अपने आप बेहतर नतीजा नहीं बन जाती।",
      },
    ],
    related: [
      { label: "Why does the same crop cost different amounts in different mandis?", href: "/learn/why-mandi-prices-differ" },
      { label: "MSP vs Mandi Bhav: what's the difference?", href: "/learn/msp-vs-mandi-bhav" },
      { label: "Browse mandi bhav by state", href: "/mandi-bhav/state/punjab" },
    ],
    relatedHi: [
      { label: "अलग-अलग मंडियों में एक ही फसल की कीमत अलग क्यों होती है?", href: "/learn/why-mandi-prices-differ" },
      { label: "एमएसपी बनाम मंडी भाव: क्या अंतर है?", href: "/learn/msp-vs-mandi-bhav" },
      { label: "राज्य अनुसार मंडी भाव देखें", href: "/mandi-bhav/state/punjab" },
    ],
  },
  {
    // Added 26 Sep 2026 — tied to the live Best Mandi and Sahi Daam tools.
    // Every number below is a worked example (clearly labelled), not a
    // claim about any real mandi, so there's nothing external to verify.
    slug: "how-to-choose-best-mandi",
    title: "How to Choose the Best Mandi to Sell Your Crop",
    hindiTitle: "फसल बेचने के लिए सबसे अच्छी मंडी कैसे चुनें",
    description:
      "The mandi with the highest rate isn't always the best place to sell. Learn how transport, mandi fee and commission change your take-home price — with a worked example and a free calculator.",
    dek: "The highest rate on the board isn't always the most money in your hand. Here's how to compare mandis the way that actually pays.",
    dekHi: "बोर्ड पर सबसे ऊँचा भाव हमेशा हाथ में सबसे ज़्यादा पैसा नहीं होता। मंडियों की तुलना सही तरीके से कैसे करें, यहां जानिए।",
    datePublished: "2026-09-26",
    body: [
      { type: "h2", text: "Rate vs take-home: the one idea that matters" },
      {
        type: "p",
        text: "A mandi's modal price is what buyers paid per quintal there today. What you actually keep is that rate minus the cost of getting your crop there and minus what the mandi and the arhatiya (commission agent) deduct. A mandi 80 km away paying ₹200 more per quintal can leave you with less money than the one next door — or more. The only way to know is to do the subtraction.",
      },
      { type: "h2", text: "The simple formula" },
      {
        type: "ul",
        items: [
          "Take-home per quintal = mandi rate − transport per quintal − (mandi fee + commission)",
          "Transport per quintal = your freight rate (₹ per quintal per km) × road distance",
          "Mandi fee + commission is usually a percentage of the sale value; it varies by state and crop, so use your local figure",
        ],
      },
      { type: "h2", text: "A worked example (illustrative numbers)" },
      {
        type: "p",
        text: "Say you have 10 quintals, your freight costs ₹1.5 per quintal per km, and fee plus commission is 4%. Mandi A is 10 km away and pays ₹2,400. Mandi B is 90 km away and pays ₹2,600. Mandi A: 2,400 − 15 (transport) − 96 (4%) = ₹2,289 per quintal. Mandi B: 2,600 − 135 − 104 = ₹2,361 per quintal. Mandi B leaves you ₹72 more per quintal — ₹720 more on 10 quintals. But if Mandi B paid ₹2,500 instead, it would come to ₹2,265, and the nearby mandi would win.",
      },
      { type: "h2", text: "Things the formula doesn't show — check them too" },
      {
        type: "ul",
        items: [
          "Is the price fresh? Vegetables and fruit can move a lot in a day; prefer today's or yesterday's report.",
          "Quality and variety: the modal price is for the grade that traded most. Your lot may fetch more or less.",
          "Waiting time and arrivals: a crowded mandi on a heavy-arrival day can pay less by the time your lot is auctioned.",
          "Payment terms: when and how you get paid matters as much as the rate.",
        ],
      },
      { type: "h2", text: "Do it in 30 seconds on TaazaBhav" },
      {
        type: "p",
        text: "The Best Mandi for Me tool on the homepage does this sum for every mapped mandi within 300 km: pick your crop, share your location or pick your nearest mandi, and enter your freight rate and fee. It ranks mandis by take-home price and shows the working for each. The Sahi Daam calculator does the same sum for one mandi you choose.",
      },
    ],
    bodyHi: [
      { type: "h2", text: "भाव बनाम हाथ में आने वाला पैसा: असली बात यही है" },
      {
        type: "p",
        text: "किसी मंडी का मॉडल भाव वह है जो आज वहां ख़रीदारों ने प्रति क्विंटल दिया। आपके हाथ में असल में उतना आता है जितना उस भाव में से ढुलाई का ख़र्च और मंडी शुल्क व आढ़तिया कमीशन घटाने के बाद बचे। 80 किमी दूर की मंडी जो ₹200 प्रति क्विंटल ज़्यादा दे रही है, वह बगल वाली मंडी से कम पैसा भी दे सकती है — या ज़्यादा। पता करने का एक ही तरीका है: हिसाब लगाना।",
      },
      { type: "h2", text: "आसान फ़ॉर्मूला" },
      {
        type: "ul",
        items: [
          "हाथ में (प्रति क्विंटल) = मंडी भाव − प्रति क्विंटल भाड़ा − (मंडी शुल्क + कमीशन)",
          "प्रति क्विंटल भाड़ा = आपका भाड़ा (₹ प्रति क्विंटल प्रति किमी) × सड़क की दूरी",
          "मंडी शुल्क + कमीशन आम तौर पर बिक्री रकम का प्रतिशत होता है; यह राज्य और फसल के हिसाब से बदलता है, इसलिए अपनी मंडी का आंकड़ा लें",
        ],
      },
      { type: "h2", text: "एक उदाहरण (सिर्फ़ समझाने के लिए आंकड़े)" },
      {
        type: "p",
        text: "मान लीजिए आपके पास 10 क्विंटल है, भाड़ा ₹1.5 प्रति क्विंटल प्रति किमी है, और शुल्क व कमीशन मिलाकर 4% है। मंडी A 10 किमी दूर है और ₹2,400 देती है। मंडी B 90 किमी दूर है और ₹2,600 देती है। मंडी A: 2,400 − 15 (भाड़ा) − 96 (4%) = ₹2,289 प्रति क्विंटल। मंडी B: 2,600 − 135 − 104 = ₹2,361 प्रति क्विंटल। यानी मंडी B में प्रति क्विंटल ₹72 ज़्यादा — 10 क्विंटल पर ₹720 ज़्यादा। लेकिन अगर मंडी B ₹2,500 ही देती, तो हिसाब ₹2,265 आता और पास वाली मंडी बेहतर रहती।",
      },
      { type: "h2", text: "जो फ़ॉर्मूला नहीं दिखाता — वह भी जांचें" },
      {
        type: "ul",
        items: [
          "भाव ताज़ा है या नहीं? सब्ज़ी-फल का भाव एक दिन में बहुत बदल सकता है; आज या कल की रिपोर्ट को तरजीह दें।",
          "गुणवत्ता और किस्म: मॉडल भाव उस ग्रेड का है जो सबसे ज़्यादा बिका। आपका माल ज़्यादा या कम पा सकता है।",
          "इंतज़ार और आवक: भारी आवक वाले दिन भीड़ वाली मंडी में आपकी बोली आने तक भाव गिर सकता है।",
          "भुगतान की शर्तें: पैसा कब और कैसे मिलेगा, यह भी भाव जितना ही ज़रूरी है।",
        ],
      },
      { type: "h2", text: "TaazaBhav पर 30 सेकंड में" },
      {
        type: "p",
        text: "होमपेज पर \"मेरे लिए सबसे अच्छी मंडी\" टूल 300 किमी के अंदर हर मैप की गई मंडी के लिए यही हिसाब लगाता है: फसल चुनें, अपनी लोकेशन दें या नज़दीकी मंडी चुनें, और अपना भाड़ा व शुल्क डालें। यह मंडियों को हाथ में आने वाली रकम के हिसाब से क्रम में रखता है और हर एक का पूरा हिसाब दिखाता है। सही दाम कैलकुलेटर आपकी चुनी हुई एक मंडी के लिए यही हिसाब करता है।",
      },
    ],
    faqs: [
      {
        q: "Should I always sell at the mandi with the highest price?",
        a: "Not always. Subtract transport and the mandi fee plus commission first. A nearer mandi with a slightly lower rate often leaves more money in your hand.",
      },
      {
        q: "How much is mandi fee and commission?",
        a: "It differs by state and crop and can change, so use the figure your local mandi or arhatiya charges. TaazaBhav's tools let you type your own percentage.",
      },
      {
        q: "Is TaazaBhav's price exactly what I will get?",
        a: "No. It's the modal price reported by the mandi to the government's Agmarknet system — a guide to what traded most. Your price depends on quality, variety and the day's auction. Confirm at the mandi before selling.",
      },
    ],
    faqsHi: [
      {
        q: "क्या हमेशा सबसे ऊँचे भाव वाली मंडी में ही बेचना चाहिए?",
        a: "हमेशा नहीं। पहले भाड़ा और मंडी शुल्क व कमीशन घटाइए। थोड़े कम भाव वाली नज़दीकी मंडी अक्सर हाथ में ज़्यादा पैसा छोड़ती है।",
      },
      {
        q: "मंडी शुल्क और कमीशन कितना होता है?",
        a: "यह राज्य और फसल के हिसाब से अलग होता है और बदल भी सकता है, इसलिए अपनी मंडी या आढ़तिया जो लेते हैं वही आंकड़ा लें। TaazaBhav के टूल में आप अपना प्रतिशत ख़ुद डाल सकते हैं।",
      },
      {
        q: "क्या TaazaBhav का भाव ठीक वही है जो मुझे मिलेगा?",
        a: "नहीं। यह मंडी द्वारा सरकार के एगमार्कनेट सिस्टम को भेजा गया मॉडल भाव है — यानी जो सबसे ज़्यादा बिका उसका अंदाज़ा। आपका भाव गुणवत्ता, किस्म और उस दिन की बोली पर निर्भर करता है। बेचने से पहले मंडी में पुष्टि करें।",
      },
    ],
    related: [
      { label: "Find your best mandi now", href: "/#mandi-locator" },
      { label: "Sahi Daam calculator", href: "/#sahi-daam" },
      { label: "Why does the same crop cost different amounts in different mandis?", href: "/learn/why-mandi-prices-differ" },
      { label: "What is mandi bhav?", href: "/learn/what-is-mandi-bhav" },
    ],
    relatedHi: [
      { label: "अभी अपनी सबसे अच्छी मंडी देखें", href: "/#mandi-locator" },
      { label: "सही दाम कैलकुलेटर", href: "/#sahi-daam" },
      { label: "अलग-अलग मंडियों में एक ही फसल की कीमत अलग क्यों होती है?", href: "/learn/why-mandi-prices-differ" },
      { label: "मंडी भाव क्या है?", href: "/learn/what-is-mandi-bhav" },
    ],
  },
  {
    // Added 26 Sep 2026. Every figure below was copied from the two PIB
    // Cabinet press releases on 26 Sep 2026 and cross-checked against
    // lib/msp.ts:
    //   Kharif MS 2026-27 (13 May 2026): https://www.pib.gov.in/PressReleasePage.aspx?PRID=2260617
    //   Rabi MS 2026-27 (1 Oct 2025):    https://www.pib.gov.in/PressReleasePage.aspx?PRID=2173567
    // Copra and jute MSPs are announced in separate releases and are
    // deliberately NOT listed here until verified the same way.
    //
    // 4 Oct 2026 (GSC export): this page had 601 impressions at position ~9
    // but 0.3% CTR — most searches were "paddy msp 2026-27" and "msp of
    // paddy 2026-27 in up". Title now leads with the paddy figure, a paddy/UP
    // section was added, and the new Rabi 2027-28 MSP was added from
    //   Rabi MS 2027-28 (30 Sep 2026): https://www.pib.gov.in/PressReleasePage.aspx?PRID=2316956
    // lib/msp.ts is NOT changed: wheat bought now is still Rabi 2026-27.
    slug: "msp-2026-27-list",
    title: "MSP 2026-27 List (Paddy ₹2,441) + New Rabi MSP 2027-28",
    hindiTitle: "एमएसपी 2026-27 पूरी सूची",
    description:
      "Paddy MSP 2026-27: ₹2,441 common, ₹2,461 Grade A (same in UP and all states). Full Kharif list + new Rabi 2027-28 MSP: wheat ₹2,610. Source: PIB.",
    dek: "Official MSP in ₹ per quintal: paddy and every Kharif crop for 2026-27, and the new Rabi 2027-28 MSP announced on 30 September 2026.",
    dekHi: "आधिकारिक एमएसपी, ₹ प्रति क्विंटल: धान और हर ख़रीफ़ फसल 2026-27, और 30 सितंबर 2026 को घोषित नया रबी एमएसपी 2027-28।",
    datePublished: "2026-09-26",
    dateModified: "2026-10-04",
    body: [
      {
        type: "p",
        text: "Minimum Support Price (MSP) is the price at which the government offers to buy notified crops from farmers at official procurement centres. It is announced once a season by the Cabinet. The figures below are copied from the Government of India's press releases (PIB) and are in ₹ per quintal.",
      },
      { type: "h2", text: "Paddy (dhan) MSP 2026-27 — the same in UP and every state" },
      {
        type: "ul",
        items: [
          "Paddy (Common): ₹2,441 per quintal; Paddy (Grade A): ₹2,461 — each ₹72 more than 2025-26.",
          "The MSP is fixed by the Centre, so it is the same in Uttar Pradesh, Punjab, Haryana, Bihar and every other state. A few states pay their own bonus on top.",
          "In Uttar Pradesh, paddy is bought at government purchase centres. Register on the UP Food & Civil Supplies portal (fcs.up.gov.in) before you take your crop.",
          "Before you sell, compare the MSP with today's paddy mandi bhav near you on TaazaBhav (Paddy page).",
        ],
      },
      { type: "h2", text: "Kharif crops — MSP 2026-27 (announced 13 May 2026)" },
      {
        type: "ul",
        items: [
          "Paddy (Common): ₹2,441 (+₹72)",
          "Paddy (Grade A): ₹2,461 (+₹72)",
          "Jowar (Hybrid): ₹4,023 (+₹324)",
          "Jowar (Maldandi): ₹4,073 (+₹324)",
          "Bajra: ₹2,900 (+₹125)",
          "Ragi: ₹5,205 (+₹319)",
          "Maize: ₹2,410 (+₹10)",
          "Tur / Arhar: ₹8,450 (+₹450)",
          "Moong: ₹8,780 (+₹12)",
          "Urad: ₹8,200 (+₹400)",
          "Groundnut: ₹7,517 (+₹254)",
          "Sunflower seed: ₹8,343 (+₹622)",
          "Soybean (Yellow): ₹5,708 (+₹380)",
          "Sesamum (Til): ₹10,346 (+₹500)",
          "Nigerseed: ₹10,052 (+₹515)",
          "Cotton (Medium staple): ₹8,267 (+₹557)",
          "Cotton (Long staple): ₹8,667 (+₹557)",
        ],
      },
      { type: "h2", text: "NEW: Rabi crops — MSP 2027-28 (announced 30 September 2026)" },
      {
        type: "p",
        text: "This is the MSP for the rabi crop being sown now (Oct–Dec 2026), bought from about April 2027. Wheat bought before then still gets the 2026-27 MSP listed further below.",
      },
      {
        type: "ul",
        items: [
          "Wheat: ₹2,610 (+₹25)",
          "Barley: ₹2,286 (+₹136)",
          "Gram (Chana): ₹5,958 (+₹83)",
          "Lentil (Masur): ₹7,390 (+₹390)",
          "Rapeseed & Mustard: ₹6,613 (+₹413)",
          "Safflower: ₹7,215 (+₹675)",
        ],
      },
      { type: "h2", text: "Rabi crops — MSP 2026-27 (announced 1 October 2025)" },
      {
        type: "ul",
        items: [
          "Wheat: ₹2,585 (+₹160)",
          "Barley: ₹2,150 (+₹170)",
          "Gram (Chana): ₹5,875 (+₹225)",
          "Lentil (Masur): ₹7,000 (+₹300)",
          "Rapeseed & Mustard: ₹6,200 (+₹250)",
          "Safflower: ₹6,540 (+₹600)",
        ],
      },
      { type: "h2", text: "What MSP does — and doesn't — mean for your sale" },
      {
        type: "ul",
        items: [
          "MSP is paid only when the government buys at its procurement centres, during notified procurement windows, for produce that meets quality norms. It is not the price every mandi must pay.",
          "In an ordinary mandi auction, the price can be above or below MSP on any day.",
          "Vegetables and fruits such as onion, potato and tomato are not covered by MSP at all.",
          "Copra and jute also have MSPs, announced in separate releases; they are not listed here.",
        ],
      },
      { type: "h2", text: "Check today's mandi price against MSP" },
      {
        type: "p",
        text: "On TaazaBhav's homepage, tap \"Below MSP\" to see which crops are trading under their MSP today. Each MSP crop's page also shows how the day's mandi prices compare with its MSP.",
      },
    ],
    bodyHi: [
      {
        type: "p",
        text: "न्यूनतम समर्थन मूल्य (एमएसपी) वह कीमत है जिस पर सरकार अधिसूचित फसलें अपने सरकारी ख़रीद केंद्रों पर किसानों से ख़रीदने की पेशकश करती है। इसकी घोषणा हर सीज़न में एक बार कैबिनेट करती है। नीचे के आंकड़े भारत सरकार की प्रेस विज्ञप्तियों (पीआईबी) से लिए गए हैं और ₹ प्रति क्विंटल में हैं।",
      },
      { type: "h2", text: "धान का एमएसपी 2026-27 — यूपी समेत हर राज्य में एक जैसा" },
      {
        type: "ul",
        items: [
          "धान (सामान्य): ₹2,441 प्रति क्विंटल; धान (ग्रेड A): ₹2,461 — दोनों 2025-26 से ₹72 ज़्यादा।",
          "एमएसपी केंद्र सरकार तय करती है, इसलिए यह उत्तर प्रदेश, पंजाब, हरियाणा, बिहार और हर राज्य में एक जैसा है। कुछ राज्य इसके ऊपर अपना बोनस देते हैं।",
          "उत्तर प्रदेश में धान सरकारी क्रय केंद्रों पर ख़रीदा जाता है। फसल ले जाने से पहले खाद्य एवं रसद विभाग के पोर्टल (fcs.up.gov.in) पर पंजीकरण कराएं।",
          "बेचने से पहले TaazaBhav पर अपने पास की मंडी का आज का धान भाव एमएसपी से मिला लें (धान पेज)।",
        ],
      },
      { type: "h2", text: "ख़रीफ़ फसलें — एमएसपी 2026-27 (घोषणा 13 मई 2026)" },
      {
        type: "ul",
        items: [
          "धान (सामान्य): ₹2,441 (+₹72)",
          "धान (ग्रेड A): ₹2,461 (+₹72)",
          "ज्वार (हाइब्रिड): ₹4,023 (+₹324)",
          "ज्वार (मालदंडी): ₹4,073 (+₹324)",
          "बाजरा: ₹2,900 (+₹125)",
          "रागी: ₹5,205 (+₹319)",
          "मक्का: ₹2,410 (+₹10)",
          "तूर / अरहर: ₹8,450 (+₹450)",
          "मूंग: ₹8,780 (+₹12)",
          "उड़द: ₹8,200 (+₹400)",
          "मूंगफली: ₹7,517 (+₹254)",
          "सूरजमुखी बीज: ₹8,343 (+₹622)",
          "सोयाबीन (पीला): ₹5,708 (+₹380)",
          "तिल: ₹10,346 (+₹500)",
          "रामतिल (नाइजरसीड): ₹10,052 (+₹515)",
          "कपास (मध्यम रेशा): ₹8,267 (+₹557)",
          "कपास (लंबा रेशा): ₹8,667 (+₹557)",
        ],
      },
      { type: "h2", text: "नया: रबी फसलें — एमएसपी 2027-28 (घोषणा 30 सितंबर 2026)" },
      {
        type: "p",
        text: "यह अभी (अक्टूबर–दिसंबर 2026) बोई जा रही रबी फसल का एमएसपी है, जिसकी ख़रीद लगभग अप्रैल 2027 से होगी। उससे पहले ख़रीदे जाने वाले गेहूं पर नीचे दिया 2026-27 का एमएसपी ही लागू है।",
      },
      {
        type: "ul",
        items: [
          "गेहूं: ₹2,610 (+₹25)",
          "जौ: ₹2,286 (+₹136)",
          "चना: ₹5,958 (+₹83)",
          "मसूर: ₹7,390 (+₹390)",
          "रेपसीड और सरसों: ₹6,613 (+₹413)",
          "कुसुम: ₹7,215 (+₹675)",
        ],
      },
      { type: "h2", text: "रबी फसलें — एमएसपी 2026-27 (घोषणा 1 अक्टूबर 2025)" },
      {
        type: "ul",
        items: [
          "गेहूं: ₹2,585 (+₹160)",
          "जौ: ₹2,150 (+₹170)",
          "चना: ₹5,875 (+₹225)",
          "मसूर: ₹7,000 (+₹300)",
          "रेपसीड और सरसों: ₹6,200 (+₹250)",
          "कुसुम: ₹6,540 (+₹600)",
        ],
      },
      { type: "h2", text: "एमएसपी का आपकी बिक्री के लिए क्या मतलब है — और क्या नहीं" },
      {
        type: "ul",
        items: [
          "एमएसपी तभी मिलता है जब सरकार अपने ख़रीद केंद्रों पर, तय ख़रीद अवधि में, गुणवत्ता मानकों पर खरी उपज ख़रीदती है। यह वह कीमत नहीं है जो हर मंडी को देनी ही हो।",
          "सामान्य मंडी बोली में किसी भी दिन भाव एमएसपी से ऊपर या नीचे हो सकता है।",
          "प्याज़, आलू, टमाटर जैसी सब्ज़ियां और फल एमएसपी में शामिल नहीं हैं।",
          "खोपरा और जूट का भी एमएसपी होता है, जिसकी घोषणा अलग विज्ञप्तियों में होती है; वे यहां शामिल नहीं हैं।",
        ],
      },
      { type: "h2", text: "आज का मंडी भाव एमएसपी से मिलाएं" },
      {
        type: "p",
        text: "TaazaBhav के होमपेज पर \"MSP से नीचे\" दबाएं और देखें कि आज कौन-सी फसलें अपने एमएसपी से नीचे बिक रही हैं। हर एमएसपी वाली फसल के पेज पर भी दिखता है कि आज के मंडी भाव उसके एमएसपी के मुकाबले कहां हैं।",
      },
    ],
    faqs: [
      {
        q: "What is the paddy MSP for 2026-27 in UP?",
        a: "The same as everywhere in India: ₹2,441 per quintal for common paddy and ₹2,461 for Grade A (PIB, 13 May 2026). Register on fcs.up.gov.in to sell at a UP government purchase centre.",
      },
      {
        q: "What is the wheat MSP for 2027-28?",
        a: "₹2,610 per quintal for Rabi Marketing Season 2027-28, up ₹25 (PIB, 30 September 2026). Mustard is ₹6,613 and gram (chana) ₹5,958.",
      },
      {
        q: "What is the wheat MSP for 2026-27?",
        a: "₹2,585 per quintal for Rabi Marketing Season 2026-27, up ₹160 from the previous year (PIB, 1 October 2025).",
      },
      {
        q: "What is the paddy MSP for 2026-27?",
        a: "₹2,441 per quintal for common paddy and ₹2,461 for Grade A, each up ₹72 (PIB, 13 May 2026).",
      },
      {
        q: "Will every mandi pay me the MSP?",
        a: "No. MSP is what the government pays at its procurement centres during procurement. Private mandi auctions can pay more or less on any given day.",
      },
    ],
    faqsHi: [
      {
        q: "यूपी में 2026-27 के लिए धान का एमएसपी कितना है?",
        a: "पूरे देश जैसा ही: सामान्य धान ₹2,441 और ग्रेड A ₹2,461 प्रति क्विंटल (पीआईबी, 13 मई 2026)। यूपी के सरकारी क्रय केंद्र पर बेचने के लिए fcs.up.gov.in पर पंजीकरण कराएं।",
      },
      {
        q: "2027-28 के लिए गेहूं का एमएसपी कितना है?",
        a: "रबी विपणन सीज़न 2027-28 के लिए ₹2,610 प्रति क्विंटल, ₹25 ज़्यादा (पीआईबी, 30 सितंबर 2026)। सरसों ₹6,613 और चना ₹5,958।",
      },
      {
        q: "2026-27 के लिए गेहूं का एमएसपी कितना है?",
        a: "रबी विपणन सीज़न 2026-27 के लिए ₹2,585 प्रति क्विंटल, पिछले साल से ₹160 ज़्यादा (पीआईबी, 1 अक्टूबर 2025)।",
      },
      {
        q: "2026-27 के लिए धान का एमएसपी कितना है?",
        a: "सामान्य धान ₹2,441 और ग्रेड A ₹2,461 प्रति क्विंटल, दोनों में ₹72 की बढ़ोतरी (पीआईबी, 13 मई 2026)।",
      },
      {
        q: "क्या हर मंडी मुझे एमएसपी देगी?",
        a: "नहीं। एमएसपी वह कीमत है जो सरकार ख़रीद के दौरान अपने ख़रीद केंद्रों पर देती है। निजी मंडी बोली में किसी दिन भाव ज़्यादा या कम हो सकता है।",
      },
    ],
    related: [
      { label: "MSP vs Mandi Bhav: what's the difference?", href: "/learn/msp-vs-mandi-bhav" },
      { label: "Wheat mandi bhav today", href: "/mandi-bhav/wheat" },
      { label: "Paddy mandi bhav today", href: "/mandi-bhav/paddycommon" },
      { label: "How to choose the best mandi to sell your crop", href: "/learn/how-to-choose-best-mandi" },
    ],
    relatedHi: [
      { label: "एमएसपी बनाम मंडी भाव: क्या अंतर है?", href: "/learn/msp-vs-mandi-bhav" },
      { label: "आज का गेहूं मंडी भाव", href: "/mandi-bhav/wheat" },
      { label: "आज का धान मंडी भाव", href: "/mandi-bhav/paddycommon" },
      { label: "फसल बेचने के लिए सबसे अच्छी मंडी कैसे चुनें", href: "/learn/how-to-choose-best-mandi" },
    ],
  },
];

export function getLearnArticle(slug: string): LearnArticle | null {
  return LEARN_ARTICLES.find((a) => a.slug === slug) ?? null;
}
