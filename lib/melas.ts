// Kisan Mela & Agri Expo calendar (27 Sep 2026).
//
// Static, hand-verified list — no database, no egress. Every event links to
// the source it was checked against. "confirmed" = the organiser (or a
// reputable listing, see `listing`) has announced 2026-27 dates.
// "expected" = dates not announced yet; we show the expected month and the
// last edition's dates, never invented dates.
//
// Slugs are evergreen (no year) so an event page keeps its Google ranking
// from one year to the next — update the dates here each season.
//
// To add or update an event: edit MELAS below, keep `verified` current.

export type MelaType = "university" | "icar" | "govt" | "expo" | "machinery" | "dairy-poultry" | "horticulture";

export type Mela = {
  slug: string;
  en: string;
  hi: string;
  organiser: string;
  type: MelaType;
  city: string;
  district: string;
  state: string;
  venue: string;
  status: "confirmed" | "expected";
  start?: string; // YYYY-MM-DD
  end?: string;
  month: string; // YYYY-MM (expected or actual)
  last: string; // last edition, plain text
  entry?: string; // "Free" etc. — omitted when unknown
  highlights: string;
  source: string;
  sourceNote: string;
  listing?: boolean; // dates come from a trade listing, not the organiser's own page
  note?: string; // extra caution shown on the page
  seoName?: string; // the name people type into Google ("GKVK Krishi Mela") — used in the <title> (4 Oct 2026, GSC queries)
  previousStart?: string; // YYYY-MM-DD — set when the organiser moved the date; Event JSON-LD then says EventRescheduled
};

export const MELA_VERIFIED = "2026-10-04";

export const MELA_TYPES: Record<MelaType, { en: string; hi: string }> = {
  university: { en: "University Kisan Mela", hi: "विश्वविद्यालय किसान मेला" },
  icar: { en: "ICAR Kisan Mela", hi: "आईसीएआर किसान मेला" },
  govt: { en: "Government Krishi Mela", hi: "सरकारी कृषि मेला" },
  expo: { en: "Agri Expo", hi: "कृषि प्रदर्शनी" },
  machinery: { en: "Machinery Show", hi: "कृषि यंत्र प्रदर्शनी" },
  "dairy-poultry": { en: "Dairy & Poultry", hi: "डेयरी व पोल्ट्री" },
  horticulture: { en: "Horticulture", hi: "बागवानी" },
};

const PAU_SRC = "https://www.rozanaspokesman.com/farming/progressive-farming/160126/pau-releases-official-dates-for-state-wide-kisan-melas.html";
const PAU_NOTE = "Rozana Spokesman, 16 Jan 2026 (PAU's official March schedule)";

export const MELAS: Mela[] = [
  // ---------- Confirmed 2026-27 dates ----------
  { slug: "pantnagar-kisan-mela-october", seoName: "Pantnagar Kisan Mela", en: "All India Kisan Mela, Pantnagar (120th)", hi: "अखिल भारतीय किसान मेला, पंतनगर (120वां)", organiser: "G.B. Pant University of Agriculture & Technology (GBPUAT)", type: "university", city: "Pantnagar", district: "Udham Singh Nagar", state: "Uttarakhand", venue: "GBPUAT campus, Pantnagar", status: "confirmed", start: "2026-10-03", end: "2026-10-06", month: "2026-10", last: "13–16 Mar 2026 (119th)", highlights: "Rabi seed sale, tractors and combines, fertilisers, veterinary products", source: "https://www.gbpuat.ac.in/mela/index.html", sourceNote: "GBPUAT official Kisan Mela page" },
  { slug: "csa-kanpur-kisan-mela", seoName: "CSA Kanpur Kisan Mela", en: "CSA Kisan Mela & Agro-Industrial Exhibition, Kanpur", hi: "किसान मेला एवं कृषि औद्योगिक प्रदर्शनी, सीएसए कानपुर", organiser: "Chandra Shekhar Azad University of Agriculture & Technology", type: "university", city: "Kanpur", district: "Kanpur Nagar", state: "Uttar Pradesh", venue: "CSA University campus, Kanpur", status: "confirmed", start: "2026-10-15", end: "2026-10-17", month: "2026-10", last: "24–25 Oct 2024", highlights: "About 200 stalls; natural and organic farming, millets", source: "https://www.amarujala.com/uttar-pradesh/kanpur/kanpur-farmers-fair-to-be-held-at-csa-from-october-15-17-farmers-from-seven-states-to-attend-2026-09-26", sourceNote: "Amar Ujala Kanpur, 26 Sep 2026" },
  { slug: "dairy-industry-expo-kolhapur", en: "Dairy Industry Expo, Kolhapur", hi: "डेयरी इंडस्ट्री एक्सपो, कोल्हापुर", organiser: "Dairy Industry Expo", type: "dairy-poultry", city: "Kolhapur", district: "Kolhapur", state: "Maharashtra", venue: "Kolhapur (venue to be announced)", status: "confirmed", start: "2026-10-16", end: "2026-10-18", month: "2026-10", last: "—", highlights: "Dairy farming and milk processing expo with conferences", source: "https://west.dairyindustryexpo.com/", sourceNote: "Organiser website", note: "Venue not yet published — check the organiser's site." },
  { slug: "uas-bangalore-krishi-mela", en: "Krishi Mela, UAS Bangalore (GKVK)", hi: "कृषि मेला, जीकेवीके बेंगलुरु", seoName: "GKVK Krishi Mela Bangalore", organiser: "University of Agricultural Sciences, Bangalore", type: "university", city: "Bengaluru", district: "Bengaluru Urban", state: "Karnataka", venue: "GKVK Campus, Bengaluru", status: "confirmed", start: "2026-11-13", end: "2026-11-13", previousStart: "2026-11-12", month: "2026-11", last: "13–16 Nov 2025", highlights: "One-day mela this year. Theme: Diversified Agriculture — Next Generation; climate-smart and organic farming, soilless cultivation, farm machinery, agritourism", source: "https://www.uasbangalore.edu.in/krishimela-2026/", sourceNote: "UAS Bangalore official Krishimela 2026 page (checked 4 Oct 2026: \"One Day UAS Bangalore Krishimela is scheduled on 13th November 2026\")", note: "UAS Bangalore has changed the dates more than once (a July stall form said 15–18 Oct; the page later said 12–15 Nov). The official page now says a one-day mela on 13 Nov 2026. Confirm with UAS Bangalore before you travel." },
  { slug: "agroworld-expo-jalgaon", en: "Agroworld Expo, Jalgaon", hi: "एग्रोवर्ल्ड कृषि प्रदर्शनी, जलगांव", organiser: "Agro World, Jalgaon", type: "expo", city: "Jalgaon", district: "Jalgaon", state: "Maharashtra", venue: "Jalgaon (venue to be announced)", status: "confirmed", start: "2026-11-20", end: "2026-11-23", month: "2026-11", last: "Nov 2025", highlights: "Farm machinery, seeds, fertilisers and irrigation — Khandesh's big farmer show", source: "https://www.tradeindia.com/tradeshows/150788/agroworld-expo-2026.html", sourceNote: "TradeIndia trade-show listing", listing: true },
  { slug: "cii-agrotech-chandigarh", en: "CII AgroTech India, Chandigarh", hi: "सीआईआई एग्रोटेक इंडिया, चंडीगढ़", organiser: "Confederation of Indian Industry (CII)", type: "expo", city: "Chandigarh", district: "Chandigarh", state: "Chandigarh", venue: "Parade Ground, Sector 17, Chandigarh", status: "confirmed", start: "2026-11-20", end: "2026-11-23", month: "2026-11", last: "2024 (16th edition; held every two years)", highlights: "About 250 exhibitors, Kisan Goshtis, livestock show", source: "https://www.tradeindia.com/tradeshows/150556/cii-agrotech-india-2026.html", sourceNote: "TradeIndia listing; CII site confirms the 2026 edition and venue", listing: true },
  { slug: "poultry-india-hyderabad", en: "Poultry India, Hyderabad", hi: "पोल्ट्री इंडिया प्रदर्शनी, हैदराबाद", organiser: "Indian Poultry Equipment Manufacturers' Association (IPEMA)", type: "dairy-poultry", city: "Hyderabad", district: "Ranga Reddy", state: "Telangana", venue: "HITEX Exhibition Centre, Hyderabad", status: "confirmed", start: "2026-11-25", end: "2026-11-27", month: "2026-11", last: "Nov 2025 (17th)", entry: "Free (register online)", highlights: "18th edition; 550+ exhibitors; Knowledge Day on 24 Nov", source: "https://www.poultryindia.co.in/", sourceNote: "IPEMA official site" },
  { slug: "krishithon-nashik", en: "Krishithon, Nashik", hi: "कृषिथॉन, नाशिक", organiser: "Media Exhibitors Pvt. Ltd.", type: "expo", city: "Nashik", district: "Nashik", state: "Maharashtra", venue: "Madsanghavi, near Toll Plaza, Sambhajinagar Road, Nashik", status: "confirmed", start: "2026-11-26", end: "2026-11-30", month: "2026-11", last: "Nov 2025", highlights: "19th edition; live demo plots, agri-tech pavilion, startup corner", source: "https://agritrademedia.com/details.php?slug=krithithon-2026", sourceNote: "Agri trade media listing; krishithon.com confirms edition and venue", listing: true },
  { slug: "agrovision-nagpur", en: "Agrovision, Nagpur", hi: "एग्रोविज़न, नागपुर", organiser: "Agrovision Foundation", type: "expo", city: "Nagpur", district: "Nagpur", state: "Maharashtra", venue: "RTMNU Campus, Amravati Road, Nagpur", status: "confirmed", start: "2026-11-27", end: "2026-11-30", month: "2026-11", last: "Nov 2025", highlights: "Vidarbha's biggest farm show; livestock, startup and MSME pavilions, workshops", source: "https://www.agrovisionindia.in/aboutevent.php", sourceNote: "Agrovision official 'About event' page" },
  { slug: "kisan-agri-show-pune", en: "KISAN Agri Show, Pune (Moshi)", hi: "किसान कृषि प्रदर्शनी, पुणे (मोशी)", organiser: "KISAN Forum Pvt Ltd", type: "expo", city: "Pune", district: "Pune", state: "Maharashtra", venue: "PIECC, Moshi, Pune", status: "confirmed", start: "2026-12-09", end: "2026-12-13", month: "2026-12", last: "Dec 2025", highlights: "34th edition; 600+ exhibitors, 10 theme pavilions", source: "https://2026.kisan.in/", sourceNote: "KISAN 2026 official site" },
  { slug: "global-potato-summit", en: "Global Potato Summit, Gandhinagar", hi: "ग्लोबल आलू शिखर सम्मेलन, गांधीनगर", organiser: "Media Today Group", type: "horticulture", city: "Gandhinagar", district: "Gandhinagar", state: "Gujarat", venue: "Mahatma Mandir Convention & Exhibition Centre", status: "confirmed", start: "2026-12-16", end: "2026-12-17", month: "2026-12", last: "—", highlights: "Potato seed, storage and processing machinery expo with conference", source: "https://www.potatopro.com/potato-conferences-tradeshows/global-potato-summit-2026", sourceNote: "PotatoPro event listing", listing: true, note: "One listing gives a different venue — confirm with the organiser before travelling." },
  { slug: "horti-agri-india-expo-delhi", en: "Horti Agri India Expo, New Delhi", hi: "हॉर्टी एग्री इंडिया एक्सपो, नई दिल्ली", organiser: "SV Global Expo", type: "horticulture", city: "New Delhi", district: "South West Delhi", state: "Delhi", venue: "Yashobhoomi Convention Centre, Dwarka Sector 25", status: "confirmed", start: "2027-03-05", end: "2027-03-07", month: "2027-03", last: "12–14 Mar 2026", highlights: "Polyhouse, protected cultivation, floriculture; 250+ exhibitors", source: "https://hortiagriindiaexpo.com/", sourceNote: "Official 2027 edition site" },

  // ---------- Expected (dates not announced yet) ----------
  { slug: "svpuat-meerut-kisan-mela", seoName: "Meerut Kisan Mela (SVPUAT)", en: "SVPUAT Kisan Mela, Meerut", hi: "किसान मेला, मोदीपुरम मेरठ", organiser: "Sardar Vallabhbhai Patel University of Agriculture & Technology", type: "university", city: "Meerut", district: "Meerut", state: "Uttar Pradesh", venue: "SVPUAT campus, Modipuram", status: "expected", month: "2026-10", last: "14–16 Oct 2025", highlights: "Improved seeds, modern equipment, livestock and dairy exhibits", source: "https://www.tractorjunction.com/agriculture-news/3-major-kisan-mela-to-be-held-in-october-2025/", sourceNote: "TractorJunction, Oct 2025" },
  { slug: "rashtriya-krishi-mela-raipur", en: "Rashtriya Krishi Mela, Raipur", hi: "राष्ट्रीय कृषि मेला, रायपुर", organiser: "Indira Gandhi Krishi Vishwavidyalaya / Govt of Chhattisgarh", type: "university", city: "Raipur", district: "Raipur", state: "Chhattisgarh", venue: "IGKV campus, Krishak Nagar, Raipur", status: "expected", month: "2026-10", last: "22–25 Oct 2024", highlights: "State agriculture department stalls, machinery, crop demos", source: "https://www.patrika.com/raipur-news/cg-news-national-agricultural-fair-in-agricultural-university-from-22nd-19080148", sourceNote: "Patrika Raipur, Oct 2024" },
  { slug: "gujarat-rabi-krushi-mahotsav", en: "Rabi Krushi Mahotsav, Gujarat", hi: "रबी कृषि महोत्सव, गुजरात", organiser: "Government of Gujarat, Agriculture Department", type: "govt", city: "All talukas", district: "All districts", state: "Gujarat", venue: "Held in 246+ talukas across Gujarat", status: "expected", month: "2026-10", last: "14–15 Oct 2025; 6–7 Dec 2024", entry: "Free", highlights: "Rabi crop advice, natural farming, scheme benefits, farmer awards", source: "https://cmogujarat.gov.in/en/latest-news/ravi-krishi-mahotsav-2024-sardar-krushinagar-dantiwada", sourceNote: "CMO Gujarat", note: "Held in October or December depending on the year." },
  { slug: "shivamogga-krishi-mela", en: "Krishi-Thotagarike Mela, Shivamogga", hi: "कृषि-बागवानी मेला, शिवमोग्गा", organiser: "Keladi Shivappa Nayaka University of Agricultural & Horticultural Sciences", type: "university", city: "Shivamogga", district: "Shivamogga", state: "Karnataka", venue: "College of Agriculture, Navile, Shivamogga", status: "expected", month: "2026-11", last: "7–10 Nov 2025", highlights: "Protected cultivation, beekeeping, fisheries, machinery; ~300 exhibitors", source: "https://uahs.edu.in/krishimela-2025/", sourceNote: "UAHS official Krishimela 2025 page" },
  { slug: "global-agrotech-lucknow", en: "Global AgroTech, Lucknow", hi: "ग्लोबल एग्रोटेक, लखनऊ", organiser: "Indian Chamber of Food and Agriculture (ICFA)", type: "expo", city: "Lucknow", district: "Lucknow", state: "Uttar Pradesh", venue: "ICAR-Indian Institute of Sugarcane Research, Lucknow", status: "expected", month: "2026-12", last: "—", entry: "Free (register online)", highlights: "UP agri summit and expo, progressive farmer awards", source: "https://globalagrotech.in/", sourceNote: "Organiser website", note: "The organiser's site shows conflicting dates — we'll list exact dates once they're clear." },
  { slug: "pdkv-akola-agrotech", en: "Agrotech Krishi Pradarshani, Akola", hi: "एग्रोटेक कृषि प्रदर्शनी, अकोला", organiser: "Dr. Panjabrao Deshmukh Krishi Vidyapeeth (PDKV)", type: "university", city: "Akola", district: "Akola", state: "Maharashtra", venue: "PDKV campus, Akola", status: "expected", month: "2026-12", last: "27–29 Dec 2025", highlights: "University farm technologies, seeds, implements", source: "https://www.pdkv.ac.in/?page_id=27318", sourceNote: "PDKV official gallery, Agrotech 2025" },
  { slug: "bharat-agri-tech-indore", en: "Bharat Agri Tech, Indore", hi: "भारत एग्री टेक, इंदौर", organiser: "Yuva Udaan Events Pvt Ltd", type: "expo", city: "Indore", district: "Indore", state: "Madhya Pradesh", venue: "College of Agriculture, Indore", status: "expected", month: "2027-01", last: "2025 (College of Agriculture, Indore)", highlights: "Central India's farm show; machinery, drones, dairy, horticulture demos", source: "https://www.kisaanhelpline.com/yono/bharat-agri-tech-2027", sourceNote: "Kisaanhelpline listing", listing: true, note: "Two sources give slightly different January dates." },
  { slug: "krushi-odisha", en: "Krushi Odisha, Bhubaneswar", hi: "कृषि ओडिशा मेला, भुवनेश्वर", organiser: "Govt of Odisha, Dept of Agriculture & Farmers' Empowerment", type: "govt", city: "Bhubaneswar", district: "Khordha", state: "Odisha", venue: "Biju Patnaik Sports Ground, Baramunda", status: "expected", month: "2027-01", last: "22–24 Jan 2026", highlights: "Farm machinery demos, scientist–farmer interaction", source: "https://ommcomnews.com/odisha-news/krushi-odisha-2026-to-be-held-from-jan-22nd-to-24th-in-bhubaneswar/", sourceNote: "OmmCom News, Jan 2026" },
  { slug: "pdfa-dairy-expo-jagraon", seoName: "PDFA Dairy Expo Jagraon", en: "PDFA International Dairy & Agri Expo, Jagraon", hi: "पीडीएफए अंतरराष्ट्रीय डेयरी एवं कृषि एक्सपो, जगराओं", organiser: "Progressive Dairy Farmers Association (PDFA), Punjab", type: "dairy-poultry", city: "Jagraon", district: "Ludhiana", state: "Punjab", venue: "Cattle Fair Ground, Jagraon", status: "expected", month: "2027-02", last: "7–9 Feb 2026 (19th)", highlights: "India's largest cattle show; 400+ exhibitors", source: "https://www.kisaanhelpline.com/19th-pdfa-international-dairy-agri-expo-2026", sourceNote: "Listing of the 2026 edition", listing: true },
  { slug: "krishi-darshan-expo-hisar", en: "Krishi Darshan Expo, Hisar", hi: "कृषि दर्शन एक्सपो, हिसार", organiser: "Krishi Darshan Expo (with Ministry of Agriculture support)", type: "machinery", city: "Hisar", district: "Hisar", state: "Haryana", venue: "NRFMTTI, Sirsa Road, Hisar", status: "expected", month: "2027-02", last: "14–16 Feb 2026", highlights: "Tractors, implements, harvesters with live demos; 350+ exhibitors", source: "https://www.tractorjunction.com/agriculture-news/krishi-darshan-expo-2026-to-be-held-from-february-14/", sourceNote: "TractorJunction, 2026 edition" },
  { slug: "india-horti-expo-karnal", en: "India International Horti Expo, Karnal", hi: "भारत अंतरराष्ट्रीय बागवानी एक्सपो, करनाल", organiser: "IIHE with Indian Nurserymen Association", type: "horticulture", city: "Karnal", district: "Karnal", state: "Haryana", venue: "New Grain Market, Karnal", status: "expected", month: "2027-02", last: "19–21 Feb 2026", highlights: "Nursery, horticulture and floriculture show", source: "https://indiainternationalhortiexpo.com/", sourceNote: "Official site (2026 edition)" },
  { slug: "pusa-krishi-vigyan-mela", en: "Pusa Krishi Vigyan Mela, New Delhi", hi: "पूसा कृषि विज्ञान मेला, नई दिल्ली", organiser: "ICAR-Indian Agricultural Research Institute (IARI)", type: "icar", city: "New Delhi", district: "New Delhi", state: "Delhi", venue: "IARI Mela Ground, Pusa Campus", status: "expected", month: "2027-02", last: "25–27 Feb 2026", entry: "Free", highlights: "New IARI seed varieties, free soil and water testing, drones", source: "https://icar.org.in/en/icar-iari-new-delhi-organises-pusa-krishi-vigyan-mela-2026", sourceNote: "ICAR official news, 2026 edition" },
  { slug: "skuast-jammu-kisan-mela", en: "SKUAST-Jammu Agriculture Summit & Kisan Mela", hi: "कृषि सम्मेलन एवं किसान मेला, चट्ठा जम्मू", organiser: "SKUAST-Jammu", type: "university", city: "Jammu", district: "Jammu", state: "Jammu and Kashmir", venue: "SKUAST-J Main Campus, Chatha", status: "expected", month: "2027-02", last: "11–13 Feb 2026", highlights: "Precision farming, machinery, farmer awards", source: "https://statetimes.in/amp/three-day-agriculture-summit-kisan-mela-2026-to-be-held-from-feb-11-at-skuast-j/", sourceNote: "State Times, Feb 2026" },
  { slug: "skuast-kashmir-gongul", en: "Gon'gul AgriTech Mela, SKUAST-Kashmir", hi: "गोंगुल कृषि-टेक मेला, शालीमार श्रीनगर", organiser: "SKUAST-Kashmir", type: "university", city: "Srinagar", district: "Srinagar", state: "Jammu and Kashmir", venue: "SKUAST-K Shalimar campus", status: "expected", month: "2027-02", last: "14–16 Feb 2026 (11th)", highlights: "Fruit, vegetable, seed and flower shows; buyer–seller meet", source: "https://asianmail.in/2026/01/15/skuast-k-to-hold-11th-agritech-mela-gongul-at-shalimar-from-feb-14/", sourceNote: "Asian Mail, Jan 2026" },
  { slug: "rlbcau-jhansi-kisan-mela", en: "RLBCAU Kisan Mela, Jhansi", hi: "किसान मेला एवं कृषि प्रदर्शनी, झांसी", organiser: "Rani Lakshmi Bai Central Agricultural University", type: "university", city: "Jhansi", district: "Jhansi", state: "Uttar Pradesh", venue: "RLBCAU campus, Jhansi", status: "expected", month: "2027-02", last: "14–16 Feb 2026", highlights: "150+ stalls, 15 ICAR institutes, millet pavilion, machinery demos", source: "https://rlbcau.ac.in/wp-content/uploads/2026/03/Kisan-Mela-cum-Agricultural-Exhibition-2026-Viksit-Krishi-Viksit-Bharat-@-2047.pdf", sourceNote: "RLBCAU official report, Mar 2026" },
  { slug: "rpcau-pusa-kisan-mela", en: "RPCAU Kisan Mela, Pusa (Bihar)", hi: "किसान मेला, पूसा समस्तीपुर", organiser: "Dr. Rajendra Prasad Central Agricultural University", type: "university", city: "Pusa", district: "Samastipur", state: "Bihar", venue: "RPCAU campus, Pusa", status: "expected", month: "2027-02", last: "15–17 Feb 2025", highlights: "Climate-resilient farming technologies, seeds, exhibitions", source: "https://rpcau.ac.in/wp-content/uploads/2025/01/Kishan-Mela-2025.pdf", sourceNote: "RPCAU official Kisan Mela 2025 notice" },
  { slug: "iari-assam-kisan-mela", en: "ICAR-IARI Assam Kisan Mela, Gogamukh", hi: "किसान मेला, आईएआरआई असम", organiser: "ICAR-IARI Assam", type: "icar", city: "Gogamukh", district: "Dhemaji", state: "Assam", venue: "Dirpai Chapori, Gogamukh", status: "expected", month: "2027-02", last: "28 Feb 2026", highlights: "Natural farming, equipment, livestock innovations", source: "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2233528", sourceNote: "PIB press release, 27 Feb 2026" },
  { slug: "ciari-andaman-kisan-mela", en: "ICAR-CIARI Kisan Mela, Sri Vijaya Puram", hi: "किसान मेला, श्री विजयपुरम", organiser: "ICAR-Central Island Agricultural Research Institute", type: "icar", city: "Sri Vijaya Puram", district: "South Andaman", state: "Andaman and Nicobar", venue: "ICAR-CIARI campus", status: "expected", month: "2027-02", last: "27 Feb 2026", highlights: "Island horticulture, fisheries, hatchery demos", source: "https://icar.org.in/en/kisan-mela-2026-cum-exhibition-inaugurated-icar-ciari-sri-vijaya-puram", sourceNote: "ICAR official news" },
  { slug: "sasya-shyamala-kvk-krishi-mela", en: "Sasya Shyamala KVK Krishi Mela, South 24 Parganas", hi: "कृषि मेला, दक्षिण 24 परगना", organiser: "Sasya Shyamala Krishi Vigyan Kendra (RKMVERI)", type: "icar", city: "Narendrapur", district: "South 24 Parganas", state: "West Bengal", venue: "SSKVK, RKMVERI", status: "expected", month: "2027-02", last: "13–14 Feb 2026", highlights: "Coastal farming, salt-tolerant crops, aquaculture meet", source: "https://kvk.rkmvu.ac.in/krishi-mela-2026-feb-13-2026/", sourceNote: "SSKVK official event page" },
  { slug: "iihr-national-horticulture-fair", seoName: "IIHR National Horticulture Fair", en: "National Horticulture Fair, IIHR Bengaluru", hi: "राष्ट्रीय बागवानी मेला, बेंगलुरु", organiser: "ICAR-Indian Institute of Horticultural Research", type: "icar", city: "Bengaluru", district: "Bengaluru Urban", state: "Karnataka", venue: "ICAR-IIHR, Hesaraghatta", status: "expected", month: "2027-02", last: "27 Feb – 1 Mar 2025", entry: "Free (register online)", highlights: "250+ stalls, Arka varieties, seed and plant sale, terrace farming", source: "https://nhf.iihr.res.in/", sourceNote: "IIHR National Horticulture Fair site" },
  { slug: "ndri-national-dairy-mela-karnal", en: "National Dairy Mela & Agri Expo, NDRI Karnal", hi: "राष्ट्रीय डेयरी मेला एवं एग्री एक्सपो, करनाल", organiser: "ICAR-National Dairy Research Institute", type: "dairy-poultry", city: "Karnal", district: "Karnal", state: "Haryana", venue: "NDRI Mela Ground, Karnal", status: "expected", month: "2027-03", last: "6–8 Mar 2026", highlights: "Cattle competitions, milk-yield contests, dairy technology", source: "https://www.tribuneindia.com/news/haryana/karnal-institute-to-host-dairy-mela-from-today/", sourceNote: "The Tribune, 6 Mar 2026" },
  { slug: "mega-rythu-mela-hyderabad", en: "Mega Rythu Mela, Hyderabad", hi: "मेगा किसान मेला (रैतु मेला), हैदराबाद", organiser: "Professor Jayashankar Telangana Agricultural University with State Agriculture Dept", type: "university", city: "Hyderabad", district: "Rangareddy", state: "Telangana", venue: "PJTAU campus, Rajendranagar", status: "expected", month: "2027-03", last: "From 8 Mar 2026", highlights: "Drones, precision farming, seeds, crop nutrition demos", source: "https://www.ntnews.com/telangana/mega-rythu-mela-at-telangana-agricultural-university-from-march-8-2321593", sourceNote: "Namasthe Telangana, Mar 2026" },
  { slug: "bau-ranchi-agrotech-kisan-mela", en: "Agrotech Kisan Mela, BAU Ranchi", hi: "एग्रोटेक किसान मेला, रांची", organiser: "Birsa Agricultural University", type: "university", city: "Ranchi", district: "Ranchi", state: "Jharkhand", venue: "BAU campus, Kanke", status: "expected", month: "2027-03", last: "From 14 Mar 2026 (3 days)", highlights: "120+ stalls, millets, climate-smart farming", source: "https://www.etvbharat.com/hi/state/agrotech-kisan-mela-2026-begins-at-birsa-agriculture-university-in-ranchi-jharkhand-news-jhs26031404234", sourceNote: "ETV Bharat, 14 Mar 2026" },
  { slug: "hau-hisar-kharif-krishi-mela", en: "Kharif Krishi Mela, HAU Hisar", hi: "खरीफ कृषि मेला, एचएयू हिसार", organiser: "CCS Haryana Agricultural University", type: "university", city: "Hisar", district: "Hisar", state: "Haryana", venue: "HAU Krishi Mela Ground", status: "expected", month: "2027-03", last: "23–24 Mar 2026", highlights: "Kharif seed sale, machinery, progressive farmer awards", source: "https://www.amarujala.com/haryana/hisar/agriculture-fair-at-hau-on-march-23-24-hisar-news-c-21-hsr1020-826695-2026-03-12", sourceNote: "Amar Ujala Hisar, 12 Mar 2026" },
  { slug: "pantnagar-kisan-mela-march", seoName: "Pantnagar Kisan Mela", en: "All India Kisan Mela, Pantnagar (Spring)", hi: "अखिल भारतीय किसान मेला (वसंत), पंतनगर", organiser: "G.B. Pant University of Agriculture & Technology (GBPUAT)", type: "university", city: "Pantnagar", district: "Udham Singh Nagar", state: "Uttarakhand", venue: "GBPUAT campus, Pantnagar", status: "expected", month: "2027-03", last: "13–16 Mar 2026 (119th)", highlights: "Kharif and zaid seeds, machinery, 350+ stalls", source: "https://www.gbpuat.ac.in/mela/index.html", sourceNote: "GBPUAT official Kisan Mela page" },
  { slug: "pau-kisan-mela-ludhiana", en: "PAU Kisan Mela, Ludhiana", hi: "पीएयू किसान मेला, लुधियाना", organiser: "Punjab Agricultural University", type: "university", city: "Ludhiana", district: "Ludhiana", state: "Punjab", venue: "PAU campus, Ludhiana", status: "expected", month: "2027-03", last: "20–21 Mar 2026 (Kharif); 18–19 Sep 2026 (Rabi)", highlights: "Kharif seeds, fruit plants, machinery", source: PAU_SRC, sourceNote: PAU_NOTE },
  { slug: "pau-kisan-mela-amritsar", en: "PAU Kisan Mela, Amritsar (Nag Kalan-Jahangir)", hi: "पीएयू किसान मेला, नागकलां-जहांगीर (अमृतसर)", organiser: "Punjab Agricultural University", type: "university", city: "Nag Kalan-Jahangir", district: "Amritsar", state: "Punjab", venue: "PAU Regional Research Station, Nag Kalan-Jahangir", status: "expected", month: "2027-03", last: "10 Mar 2026", highlights: "Kharif seed sale, crop advice, demonstrations", source: PAU_SRC, sourceNote: PAU_NOTE },
  { slug: "pau-kisan-mela-patiala", en: "PAU Kisan Mela, Rauni (Patiala)", hi: "पीएयू किसान मेला, रौणी (पटियाला)", organiser: "Punjab Agricultural University", type: "university", city: "Rauni", district: "Patiala", state: "Punjab", venue: "PAU station, Rauni", status: "expected", month: "2027-03", last: "12 Mar 2026", highlights: "Kharif seed sale, crop advice, demonstrations", source: PAU_SRC, sourceNote: PAU_NOTE },
  { slug: "pau-kisan-mela-ballowal-saunkhri", en: "PAU Kisan Mela, Ballowal Saunkhri", hi: "पीएयू किसान मेला, बल्लोवाल सौंखड़ी", organiser: "Punjab Agricultural University", type: "university", city: "Ballowal Saunkhri", district: "Shaheed Bhagat Singh Nagar", state: "Punjab", venue: "PAU Regional Research Station, Ballowal Saunkhri", status: "expected", month: "2027-03", last: "14 Mar 2026", highlights: "Kandi-area crops, Kharif seeds, crop advice", source: PAU_SRC, sourceNote: PAU_NOTE },
  { slug: "pau-kisan-mela-faridkot", en: "PAU Kisan Mela, Faridkot", hi: "पीएयू किसान मेला, फरीदकोट", organiser: "Punjab Agricultural University", type: "university", city: "Faridkot", district: "Faridkot", state: "Punjab", venue: "PAU Regional Research Station, Faridkot", status: "expected", month: "2027-03", last: "17 Mar 2026", highlights: "Kharif seed sale, cotton advice, demonstrations", source: PAU_SRC, sourceNote: PAU_NOTE },
  { slug: "pau-kisan-mela-bathinda", en: "PAU Kisan Mela, Bathinda", hi: "पीएयू किसान मेला, बठिंडा", organiser: "Punjab Agricultural University", type: "university", city: "Bathinda", district: "Bathinda", state: "Punjab", venue: "PAU Regional Research Station, Bathinda", status: "expected", month: "2027-03", last: "24 Mar 2026", highlights: "Malwa cotton belt mela; Kharif seed sale", source: PAU_SRC, sourceNote: PAU_NOTE },
  { slug: "pau-kisan-mela-gurdaspur", en: "PAU Kisan Mela, Gurdaspur", hi: "पीएयू किसान मेला, गुरदासपुर", organiser: "Punjab Agricultural University", type: "university", city: "Gurdaspur", district: "Gurdaspur", state: "Punjab", venue: "PAU Regional Research Station, Gurdaspur", status: "expected", month: "2027-03", last: "27 Mar 2026", highlights: "Kharif seed sale, sugarcane and horticulture advice", source: PAU_SRC, sourceNote: PAU_NOTE },
  { slug: "gadvasu-pashu-palan-mela", en: "GADVASU Pashu Palan Mela, Ludhiana", hi: "पशु पालन मेला, लुधियाना", organiser: "Guru Angad Dev Veterinary & Animal Sciences University", type: "dairy-poultry", city: "Ludhiana", district: "Ludhiana", state: "Punjab", venue: "GADVASU campus, Ludhiana", status: "expected", month: "2027-03", last: "Sep 2026; 24–25 Mar 2024", highlights: "Livestock breeds, free milk and feed tests, 100+ companies", source: "https://www.gadvasu.in/news/7637", sourceNote: "GADVASU official news" },
];

// ---------- helpers ----------

const MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_HI = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"];

export function monthLabel(ym: string, lang: "en" | "hi" = "en"): string {
  const [y, m] = ym.split("-").map(Number);
  return `${(lang === "hi" ? MONTHS_HI : MONTHS_EN)[m - 1]} ${y}`;
}

function dayMonth(iso: string, lang: "en" | "hi") {
  const [, m, d] = iso.split("-").map(Number);
  return `${d} ${(lang === "hi" ? MONTHS_HI : MONTHS_EN)[m - 1]}`;
}

/** "3–6 Oct 2026" or "Expected: Mar 2027" */
export function melaWhen(e: Mela, lang: "en" | "hi" = "en"): string {
  if (e.status === "confirmed" && e.start) {
    const y = e.start.slice(0, 4);
    if (!e.end || e.end === e.start) return `${dayMonth(e.start, lang)} ${y}`;
    const sameMonth = e.start.slice(0, 7) === e.end.slice(0, 7);
    return sameMonth
      ? `${Number(e.start.slice(8))}–${dayMonth(e.end, lang)} ${y}`
      : `${dayMonth(e.start, lang)} – ${dayMonth(e.end, lang)} ${y}`;
  }
  return lang === "hi" ? `संभावित: ${monthLabel(e.month, "hi")}` : `Expected: ${monthLabel(e.month)}`;
}

/** Sort key: confirmed start date, else the 15th of the expected month. */
function sortKey(e: Mela) {
  return e.start ?? `${e.month}-15`;
}

/** Events that haven't finished yet (by end date, or by expected month). */
export function upcomingMelas(today: string): Mela[] {
  const month = today.slice(0, 7);
  return MELAS.filter((e) => (e.status === "confirmed" && e.end ? e.end >= today : e.month >= month)).sort((a, b) =>
    sortKey(a).localeCompare(sortKey(b))
  );
}

export function getMela(slug: string): Mela | undefined {
  return MELAS.find((e) => e.slug === slug);
}

export function melaStates(): string[] {
  return [...new Set(MELAS.map((e) => e.state))].sort();
}

export function daysUntil(e: Mela, today: string): number | null {
  if (e.status !== "confirmed" || !e.start) return null;
  return Math.round((Date.parse(e.start) - Date.parse(today)) / 86400000);
}

export function todayIST(): string {
  return new Date(Date.now() + 5.5 * 3600 * 1000).toISOString().slice(0, 10);
}

// Link a mela's state to its mandi-price hub. Agmarknet spells two states
// differently from common usage; states with no mandi data get no link.
const MANDI_STATE: Record<string, string> = { Delhi: "NCT of Delhi", Chhattisgarh: "Chattisgarh" };
const MANDI_STATES = new Set([
  "Andaman and Nicobar", "Andhra Pradesh", "Assam", "Bihar", "Chandigarh", "Chattisgarh", "Goa", "Gujarat", "Haryana",
  "Himachal Pradesh", "Jammu and Kashmir", "Karnataka", "Keralam", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
  "Nagaland", "NCT of Delhi", "Odisha", "Pondicherry", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana", "Tripura",
  "Uttar Pradesh", "Uttarakhand", "West Bengal",
]);
export function mandiStateFor(state: string): string | null {
  const s = MANDI_STATE[state] ?? state;
  return MANDI_STATES.has(s) ? s : null;
}

const STATE_HI_EXTRA: Record<string, string> = { Delhi: "दिल्ली", Chhattisgarh: "छत्तीसगढ़", Jharkhand: "झारखंड" };
export function melaStateHi(state: string, translate: (s: string) => string): string {
  return STATE_HI_EXTRA[state] ?? translate(state);
}
