# -*- coding: utf-8 -*-
from datetime import date
from price_history import compute_trend
from hindi_names import commodity_hi, state_hi, spoken_market, price_int

LANG_TEMPLATES = {
    "hi": {
        "intro": "नमस्कार दोस्तों! आज {date} है, और यह हैं {state} की "
                 "मंडियों में {commodity} के ताज़ा भाव।",
        "line":  "{market} मंडी में {commodity} का भाव — न्यूनतम {min} "
                 "रुपये, अधिकतम {max} रुपये, और औसत {modal} रुपये "
                 "प्रति क्विंटल रहा।",
        "outro": "यह अपडेट रोज़ सुबह मिलेगा। चैनल सब्सक्राइब करें और "
                 "बेल आइकन दबाना न भूलें। धन्यवाद!",
        "trend": "{market} में {commodity} का भाव कल के मुकाबले {pct}% {trend} {modal} रुपये तक पहुँच गया।",
        "trend_word": {"up": "बढ़कर", "down": "घटकर", "flat": "लगभग स्थिर रहकर"},
    },
    "mr": {
        "intro": "नमस्कार मित्रांनो! आज {date} आहे, आणि हे आहेत {state} "
                 "मधील बाजारपेठांमध्ये {commodity} चे ताजे भाव.",
        "line":  "{market} बाजारात {commodity} चा भाव — किमान {min} "
                 "रुपये, कमाल {max} रुपये, आणि सरासरी {modal} रुपये "
                 "प्रति क्विंटल राहिला.",
        "outro": "हा अपडेट दररोज सकाळी मिळेल. चॅनल सबस्क्राइब करा आणि "
                 "बेल आयकॉन दाबायला विसरू नका. धन्यवाद!",
        "trend": "{market} मध्ये {commodity} चा भाव कालच्या तुलनेत {pct}% {trend} {modal} रुपये झाला.",
        "trend_word": {"up": "वाढून", "down": "घटून", "flat": "जवळपास स्थिर राहून"},
    },
    "pa": {
        "intro": "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ ਦੋਸਤੋ! ਅੱਜ {date} ਹੈ, ਅਤੇ ਇਹ ਹਨ {state} "
                 "ਦੀਆਂ ਮੰਡੀਆਂ ਵਿੱਚ {commodity} ਦੇ ਤਾਜ਼ਾ ਭਾਅ।",
        "line":  "{market} ਮੰਡੀ ਵਿੱਚ {commodity} ਦਾ ਭਾਅ — ਘੱਟੋ-ਘੱਟ "
                 "{min} ਰੁਪਏ, ਵੱਧ ਤੋਂ ਵੱਧ {max} ਰੁਪਏ, ਅਤੇ ਔਸਤ {modal} "
                 "ਰੁਪਏ ਪ੍ਰਤੀ ਕੁਇੰਟਲ ਰਿਹਾ।",
        "outro": "ਇਹ ਅੱਪਡੇਟ ਰੋਜ਼ ਸਵੇਰੇ ਮਿਲੇਗਾ। ਚੈਨਲ ਸਬਸਕ੍ਰਾਈਬ ਕਰੋ ਅਤੇ "
                 "ਬੈੱਲ ਆਈਕਨ ਦਬਾਉਣਾ ਨਾ ਭੁੱਲੋ। ਧੰਨਵਾਦ!",
        "trend": "{market} ਵਿੱਚ {commodity} ਦਾ ਭਾਅ ਕੱਲ੍ਹ ਦੇ ਮੁਕਾਬਲੇ {pct}% {trend} {modal} ਰੁਪਏ ਹੋ ਗਿਆ।",
        "trend_word": {"up": "ਵਧ ਕੇ", "down": "ਘਟ ਕੇ", "flat": "ਲਗਭਗ ਸਥਿਰ ਰਹਿ ਕੇ"},
    },
    "gu": {
        "intro": "નમસ્તે મિત્રો! આજે {date} છે, અને આ છે {state} ની "
                 "મંડીઓમાં {commodity} ના તાજા ભાવ.",
        "line":  "{market} મંડીમાં {commodity} નો ભાવ — લઘુત્તમ {min} "
                 "રૂપિયા, મહત્તમ {max} રૂપિયા, અને સરેરાશ {modal} "
                 "રૂપિયા પ્રતિ ક્વિન્ટલ રહ્યો.",
        "outro": "આ અપડેટ દરરોજ સવારે મળશે. ચેનલને સબ્સ્ક્રાઇબ કરો અને "
                 "બેલ આઇકન દબાવવાનું ભૂલશો નહીં. આભાર!",
        "trend": "{market} માં {commodity} નો ભાવ ગઈકાલની સરખામણીમાં {pct}% {trend} {modal} રૂપિયા થયો.",
        "trend_word": {"up": "વધીને", "down": "ઘટીને", "flat": "લગભગ સ્થિર રહીને"},
    },
    "kn": {
        "intro": "ನಮಸ್ಕಾರ ಸ್ನೇಹಿತರೆ! ಇಂದು {date}, ಮತ್ತು ಇವು {state} "
                 "ಮಂಡಿಗಳಲ್ಲಿ {commodity} ನ ತಾಜಾ ದರಗಳು.",
        "line":  "{market} ಮಂಡಿಯಲ್ಲಿ {commodity} ದರ — ಕನಿಷ್ಠ {min} "
                 "ರೂಪಾಯಿ, ಗರಿಷ್ಠ {max} ರೂಪಾಯಿ, ಮತ್ತು ಸರಾಸರಿ {modal} "
                 "ರೂಪಾಯಿ ಪ್ರತಿ ಕ್ವಿಂಟಲ್.",
        "outro": "ಈ ಅಪ್‌ಡೇಟ್ ಪ್ರತಿದಿನ ಬೆಳಿಗ್ಗೆ ಸಿಗುತ್ತದೆ. ಚಾನೆಲ್ "
                 "ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ ಮತ್ತು ಬೆಲ್ ಐಕಾನ್ ಒತ್ತಲು "
                 "ಮರೆಯಬೇಡಿ. ಧನ್ಯವಾದಗಳು!",
        "trend": "{market} ನಲ್ಲಿ {commodity} ಬೆಲೆ ನಿನ್ನೆಗೆ ಹೋಲಿಸಿದರೆ {pct}% {trend} {modal} ರೂಪಾಯಿ ಆಗಿದೆ.",
        "trend_word": {"up": "ಹೆಚ್ಚಾಗಿ", "down": "ಕಡಿಮೆಯಾಗಿ", "flat": "ಬಹುತೇಕ ಸ್ಥಿರವಾಗಿ"},
    },
    "ta": {
        "intro": "வணக்கம் நண்பர்களே! இன்று {date}, இவை {state} "
                 "சந்தைகளில் {commodity} இன் புதிய விலைகள்.",
        "line":  "{market} சந்தையில் {commodity} விலை — குறைந்தபட்சம் "
                 "{min} ரூபாய், அதிகபட்சம் {max} ரூபாய், மற்றும் "
                 "சராசரி {modal} ரூபாய் ஒரு குவிண்டலுக்கு.",
        "outro": "இந்த புதுப்பிப்பு தினமும் காலையில் கிடைக்கும். "
                 "சேனலை subscribe செய்யவும், bell ஐகானை அழுத்த "
                 "மறக்காதீர்கள். நன்றி!",
        "trend": "{market} இல் {commodity} விலை நேற்றை விட {pct}% {trend} {modal} ரூபாயாக உள்ளது.",
        "trend_word": {"up": "உயர்ந்து", "down": "குறைந்து", "flat": "கிட்டத்தட்ட மாற்றமின்றி"},
    },
    "te": {
        "intro": "నమస్కారం మిత్రులారా! ఈరోజు {date}, మరియు ఇవి "
                 "{state} మార్కెట్లలో {commodity} తాజా ధరలు.",
        "line":  "{market} మార్కెట్‌లో {commodity} ధర — కనిష్టం {min} "
                 "రూపాయలు, గరిష్టం {max} రూపాయలు, మరియు సగటు {modal} "
                 "రూపాయలు క్వింటాలుకు.",
        "outro": "ఈ అప్‌డేట్ ప్రతిరోజు ఉదయం లభిస్తుంది. ఛానెల్‌ను "
                 "సబ్‌స్క్రైబ్ చేయండి మరియు బెల్ ఐకాన్ నొక్కడం "
                 "మర్చిపోకండి. ధన్యవాదాలు!",
        "trend": "{market} లో {commodity} ధర నిన్నటితో పోలిస్తే {pct}% {trend} {modal} రూపాయలకు చేరింది.",
        "trend_word": {"up": "పెరిగి", "down": "తగ్గి", "flat": "దాదాపు స్థిరంగా"},
    },
    "bn": {
        "intro": "নমস্কার বন্ধুরা! আজ {date}, এবং এইগুলো হলো {state} "
                 "এর মান্ডিতে {commodity} এর সাম্প্রতিক দাম।",
        "line":  "{market} মান্ডিতে {commodity} এর দাম — সর্বনিম্ন "
                 "{min} টাকা, সর্বোচ্চ {max} টাকা, এবং গড় {modal} "
                 "টাকা প্রতি কুইন্টাল।",
        "outro": "এই আপডেট প্রতিদিন সকালে পাবেন। চ্যানেলটি সাবস্ক্রাইব "
                 "করুন এবং বেল আইকন চাপতে ভুলবেন না। ধন্যবাদ!",
        "trend": "{market} এ {commodity} এর দাম গতকালের তুলনায় {pct}% {trend} {modal} টাকা হয়েছে.",
        "trend_word": {"up": "বেড়ে", "down": "কমে", "flat": "প্রায় স্থিতিশীল থেকে"},
    },
    "ml": {
        "intro": "നമസ്കാരം സുഹൃത്തുക്കളേ! ഇന്ന് {date}, ഇവയാണ് {state} "
                 "ചന്തകളിലെ {commodity} യുടെ പുതിയ വിലകൾ.",
        "line":  "{market} ചന്തയിൽ {commodity} വില — കുറഞ്ഞത് {min} "
                 "രൂപ, കൂടിയത് {max} രൂപ, ശരാശരി {modal} രൂപ ഒരു "
                 "ക്വിന്റലിന്.",
        "outro": "ഈ അപ്ഡേറ്റ് എല്ലാ ദിവസവും രാവിലെ ലഭിക്കും. ചാനൽ "
                 "സബ്സ്ക്രൈബ് ചെയ്യുക, ബെൽ ഐക്കൺ അമർത്താൻ "
                 "മറക്കരുത്. നന്ദി!",
        "trend": "{market} ൽ {commodity} വില ഇന്നലത്തേതിനെ അപേക്ഷിച്ച് {pct}% {trend} {modal} രൂപയായി.",
        "trend_word": {"up": "വർധിച്ച്", "down": "കുറഞ്ഞ്", "flat": "ഏകദേശം സ്ഥിരമായി"},
    },
}

def _build_parts(records, state, commodity, run_date, lang="hi", yesterday_prices=None):
    """Builds the individual narration segments (intro / market lines / trend /
    outro) exactly once. Both build_script() (the audio narration) and
    build_script_and_captions() (narration + matching on-screen captions)
    call this, so the spoken words and the captions can never drift apart --
    the caption for a segment is always the literal sentence being spoken.

    run_date: the canonical business date (a datetime.date) for the intro
    line's "aaj {date} hai" -- Phase 1B-B. Must come from the caller (main.py's
    single per-run snapshot), never from an independent date.today() here:
    a real production incident showed this file's own former date.today()
    call could disagree with the date already shown in the video's own
    title/thumbnail for the same run."""
    if lang == "hi":
        return _build_parts_hi(records, state, commodity, run_date, yesterday_prices)
    tpl = LANG_TEMPLATES.get(lang, LANG_TEMPLATES["hi"])
    today = run_date.strftime("%d %B %Y")

    intro = tpl["intro"].format(date=today, state=state, commodity=commodity)

    market_lines = []
    for r in records[:3]:
        market_lines.append(tpl["line"].format(
            market=r.get("market", "").strip(),
            commodity=commodity,
            min=r.get("min_price", "N/A"),
            max=r.get("max_price", "N/A"),
            modal=r.get("modal_price", "N/A"),
        ))

    trend = None
    trend_data = None  # raw {direction, pct} for the Bull vs Bear visual segment
    if yesterday_prices and records:
        top = records[0]
        trend_result = compute_trend(
            yesterday_prices, top.get("market", "").strip(),
            top.get("modal_price"),
        )
        if trend_result:
            direction, pct = trend_result
            trend = tpl["trend"].format(
                market=top.get("market", "").strip(),
                commodity=commodity,
                pct=pct,
                trend=tpl["trend_word"][direction],
                modal=top.get("modal_price", "N/A"),
            )
            trend_data = {"direction": direction, "pct": pct}

    outro = tpl["outro"]
    return intro, market_lines, trend, trend_data, outro

# ---------------------------------------------------------------------------
# Hindi story-first script (Batch 2, 26 Sep 2026).
#
# Why: the old script opened every video with "नमस्कार दोस्तों! आज {date}
# है..." and then read 9 numbers (min/max/modal x 3 markets). Views fell
# from 100-220 to 2-60 per Short in two weeks: nothing in the first 2
# seconds changed from one day to the next, and nobody can hold 9 numbers.
#
# Now: sentence 1 is today's story (the gap between the best and worst
# mandi, or the best mandi), then one short line per market (modal price
# only), the existing day-over-day trend line, and an outro that sends
# people to the website instead of asking for the bell icon. Every slot has
# 3 wordings picked by the date, so no two days sound the same.
#
# Relies on records being sorted highest modal price first (fetch_prices.
# clean_records(), Batch 1) -- records[0] is the best mandi, records[-1]
# the lowest of the ones fetched. The market lines still narrate
# records[:3] in order, because make_video.py draws segment i from
# records[i]; voice and picture must stay in step.
#
# The spoken date keeps the "%d %B %Y" form: the canonical-date tests
# (tests/test_generate_script.py) check for it, and it proves which day's
# prices these are.
# ---------------------------------------------------------------------------
SPREAD_STORY_MIN = 0.25  # >= 25% gap between best and lowest mandi = "spread" story

HOOKS_SPREAD = [
    "{s} में आज {c} का भाव {low} से {high} रुपये तक — मंडी बदलने से {gap} रुपये क्विंटल का फ़र्क।",
    "एक ही राज्य, एक ही {c} — {low_m} में {low} रुपये, और {high_m} में {high} रुपये।",
    "{s} की मंडियों में {c} पर आज {gap} रुपये क्विंटल का अंतर है। देखिए सबसे अच्छा भाव कहाँ मिला।",
]
HOOKS_BEST = [
    "आज {s} में {c} का सबसे अच्छा भाव {high_m} मंडी में मिला — {high} रुपये क्विंटल।",
    "{c} बेचना है? आज {s} में सबसे ऊँचा भाव {high_m} में है — {high} रुपये।",
    "{s} में आज {c} का टॉप भाव: {high_m}, {high} रुपये प्रति क्विंटल।",
]
DATE_LINE = "यह {date} के ताज़ा सरकारी भाव हैं।"
MARKET_LINES = [
    "{m} मंडी में {modal} रुपये।",
    "{m} में भाव {modal} रुपये क्विंटल।",
    "{m} — {modal} रुपये।",
]
OUTROS = [
    "अपनी मंडी का पूरा भाव ताज़ा भाव डॉट कॉम पर देखें।",
    "भाड़ा और खर्चा जोड़कर ही मंडी चुनें। हर मंडी का भाव ताज़ा भाव डॉट कॉम पर।",
    "कल सुबह फिर मिलेंगे नए भाव के साथ। पूरी लिस्ट ताज़ा भाव डॉट कॉम पर।",
]


def _pick(options, run_date, salt=0):
    return options[(run_date.toordinal() + salt) % len(options)]


def _build_parts_hi(records, state, commodity, run_date, yesterday_prices=None):
    tpl = LANG_TEMPLATES["hi"]
    c = commodity_hi(commodity)
    s = state_hi(state)
    today = run_date.strftime("%d %B %Y")

    priced = [r for r in records if price_int(r.get("modal_price")) is not None]
    hook = None
    if priced:
        high_r, low_r = priced[0], priced[-1]
        high, low = price_int(high_r.get("modal_price")), price_int(low_r.get("modal_price"))
        fields = dict(
            s=s, c=c, high=high, low=low, gap=high - low,
            high_m=spoken_market(high_r.get("market", "")),
            low_m=spoken_market(low_r.get("market", "")),
        )
        if len(priced) >= 2 and low > 0 and (high - low) / low >= SPREAD_STORY_MIN:
            hook = _pick(HOOKS_SPREAD, run_date).format(**fields)
        else:
            hook = _pick(HOOKS_BEST, run_date).format(**fields)
    if hook is None:
        hook = f"आज {s} में {c} के ताज़ा भाव।"
    intro = hook + " " + DATE_LINE.format(date=today)

    market_lines = []
    for i, r in enumerate(records[:3]):
        market_lines.append(_pick(MARKET_LINES, run_date, salt=i).format(
            m=spoken_market(r.get("market", "")),
            modal=price_int(r.get("modal_price")) if price_int(r.get("modal_price")) is not None else "N/A",
        ))

    trend = None
    trend_data = None
    if yesterday_prices and records:
        top = records[0]
        trend_result = compute_trend(
            yesterday_prices, top.get("market", "").strip(),
            top.get("modal_price"),
        )
        if trend_result:
            direction, pct = trend_result
            trend = tpl["trend"].format(
                market=spoken_market(top.get("market", "")),
                commodity=c,
                pct=pct,
                trend=tpl["trend_word"][direction],
                modal=price_int(top.get("modal_price")),
            )
            trend_data = {"direction": direction, "pct": pct}

    outro = _pick(OUTROS, run_date)
    return intro, market_lines, trend, trend_data, outro


def build_script(records, state, commodity, lang="hi", yesterday_prices=None, run_date=None):
    """Unchanged from before: one script string, for make_audio.py.

    run_date is optional here (unlike build_script_and_captions(), which the
    real pipeline calls and which requires it) specifically so the existing
    manual smoke-test scripts (test_script.py, test_preview.py) that call
    this function directly, standalone, with no pipeline run_date to supply,
    keep working unchanged -- falls back to date.today() only in that
    standalone case."""
    if run_date is None:
        run_date = date.today()
    intro, market_lines, trend, trend_data, outro = _build_parts(records, state, commodity, run_date, lang, yesterday_prices)
    lines = [intro, ""]
    lines.extend(market_lines)
    if trend:
        lines.append("")
        lines.append(trend)
        lines.append("")
    lines.append(outro)
    return "\n".join(lines)

def build_script_and_captions(records, state, commodity, run_date, lang="hi", yesterday_prices=None):
    """Same narration text as build_script() (so make_audio.py doesn't
    change at all), PLUS the individual pieces split out for use as
    on-screen captions in make_video.py -- so the captions always say
    exactly what the voice is saying, word for word.

    run_date (required, Phase 1B-B): the canonical business date for this
    pipeline run (a datetime.date), supplied explicitly by main.py's single
    per-run snapshot. This is the function main.py actually calls, so
    unlike build_script() it has no date.today() fallback -- the real
    pipeline must always supply this, and forgetting to would be a bug
    worth failing loudly on rather than silently recomputing the date here.

    Returns (script_text, captions) where captions is:
    {"intro": str, "markets": [str, ...], "trend": str or None,
     "trend_data": {"direction": "up"/"down"/"flat", "pct": float} or None}
    trend_data carries the raw numbers (not the sentence) for the Bull vs
    Bear visual segment in make_video.py -- it's None whenever there's no
    day-over-day comparison available (e.g. first day, no price history yet).
    """
    intro, market_lines, trend, trend_data, outro = _build_parts(records, state, commodity, run_date, lang, yesterday_prices)
    lines = [intro, ""]
    lines.extend(market_lines)
    if trend:
        lines.append("")
        lines.append(trend)
        lines.append("")
    lines.append(outro)
    script_text = "\n".join(lines)

    captions = {
        "intro": intro,
        "markets": market_lines,
        "trend": trend,
        "trend_data": trend_data,
    }
    return script_text, captions
