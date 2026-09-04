# -*- coding: utf-8 -*-
from datetime import date
from price_history import compute_trend

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


def build_script(records, state, commodity, lang="hi", yesterday_prices=None):
    tpl = LANG_TEMPLATES.get(lang, LANG_TEMPLATES["hi"])
    today = date.today().strftime("%d %B %Y")

    lines = [
        tpl["intro"].format(date=today, state=state, commodity=commodity),
        "",
    ]

    for r in records[:3]:
        lines.append(tpl["line"].format(
            market=r.get("market", "").strip(),
            commodity=commodity,
            min=r.get("min_price", "N/A"),
            max=r.get("max_price", "N/A"),
            modal=r.get("modal_price", "N/A"),
        ))

    if yesterday_prices and records:
        top = records[0]
        trend = compute_trend(
            yesterday_prices, top.get("market", "").strip(),
            top.get("modal_price"),
        )
        if trend:
            direction, pct = trend
            lines.append("")
            lines.append(tpl["trend"].format(
                market=top.get("market", "").strip(),
                commodity=commodity,
                pct=pct,
                trend=tpl["trend_word"][direction],
                modal=top.get("modal_price", "N/A"),
            ))

    lines.append("")
    lines.append(tpl["outro"])
    return "\n".join(lines)