from gtts import gTTS


def make_audio(script_text, out_path="output.mp3", lang="hi"):
    tts = gTTS(text=script_text, lang=lang, slow=False)
    tts.save(out_path)
    return out_path