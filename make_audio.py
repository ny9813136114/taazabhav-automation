import edge_tts
import asyncio

# Female Neural voices for each language (consistent, natural sound)
VOICE_MAP = {
    "hi": "hi-IN-SwaraNeural",
    "mr": "mr-IN-AarohiNeural",
    "pa": "pa-IN-VaaniNeural",
    "gu": "gu-IN-DhwaniNeural",
    "kn": "kn-IN-SapnaNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "bn": "bn-IN-TanishaaNeural",
    "ml": "ml-IN-SobhanaNeural",
}

def make_audio(script_text, out_path="output.mp3", lang="hi"):
    voice = VOICE_MAP.get(lang, "hi-IN-SwaraNeural")

    async def _generate():
        communicate = edge_tts.Communicate(script_text, voice)
        await communicate.save(out_path)

    asyncio.run(_generate())
    return out_path