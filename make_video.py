from moviepy import ColorClip, AudioFileClip, TextClip, CompositeVideoClip

BOLD_FONT = "assets/fonts/NotoSansDevanagari-Bold.ttf"
REGULAR_FONT = "assets/fonts/NotoSansDevanagari-Regular.ttf"


def make_video(audio_path, records, state, commodity, lang, output_path="output.mp4"):
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    bg = ColorClip(size=(1920, 1080), color=(20, 60, 20)).with_duration(duration)

    title = TextClip(
        font=BOLD_FONT,
        text=f"{commodity} Bhav - {state}",
        font_size=70, color="white",
        size=(1800, None), method="caption"
    ).with_position(("center", 80)).with_duration(duration)

    rows_text = "\n".join(
        f"{r.get('market', '')}: Rs.{r.get('modal_price', 'N/A')}/quintal"
        for r in records[:8]
    )
    body = TextClip(
        font=REGULAR_FONT,
        text=rows_text,
        font_size=42, color="yellow",
        size=(1600, None), method="caption"
    ).with_position(("center", 300)).with_duration(duration)

    final = CompositeVideoClip([bg, title, body]).with_audio(audio)
    final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    return output_path