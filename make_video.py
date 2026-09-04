import os
from moviepy import AudioFileClip, ImageClip, CompositeVideoClip
from render_card import render_vertical_card


def make_video(audio_path, records, state, commodity, lang, output_path="output.mp4", date_str=""):
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    frame = render_vertical_card(commodity, state, records, date_str)
    frame_path = "_frame_tmp.png"
    frame.save(frame_path)

    bg = ImageClip(frame_path).with_duration(duration)
    final = CompositeVideoClip([bg]).with_audio(audio)
    final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

    if os.path.exists(frame_path):
        os.remove(frame_path)

    return output_path