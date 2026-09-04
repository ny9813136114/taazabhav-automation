import os
import wave
import numpy as np
from moviepy import (
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    CompositeAudioClip,
    VideoClip,
    ImageSequenceClip,
    vfx,
    afx,
)
from render_card import (
    render_segment_intro,
    render_segment_market,
    render_segment_trend,
    render_segment_countdown,
    render_segment_spotlight,
    _top_price,
)

FADE = 0.6
SR = 44100


# ---------------------------------------------------------------------------
# Synthesized SFX (no external audio files needed -- generated on the fly so
# the pipeline stays 100% automated with zero manual asset sourcing).
# ---------------------------------------------------------------------------

def _write_wav(path, audio_float, sr=SR):
    audio_int16 = (np.clip(audio_float, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(audio_int16.tobytes())


def _make_ding(duration=0.22, f0=1400, f1=2600, sr=SR):
    n = int(duration * sr)
    t = np.linspace(0, duration, n, endpoint=False)
    freq = np.linspace(f0, f1, n)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    tone = np.sin(phase) * 0.6 + np.sin(phase * 2) * 0.25
    envelope = np.exp(-6 * t / duration)
    audio = tone * envelope
    return audio / (np.max(np.abs(audio)) + 1e-6) * 0.9


def _make_whoosh(duration=0.32, sr=SR):
    n = int(duration * sr)
    t = np.linspace(0, duration, n, endpoint=False)
    noise = np.random.uniform(-1, 1, n)
    kernel = np.ones(60) / 60
    noise_filtered = np.convolve(noise, kernel, mode="same")
    sweep_freq = np.linspace(2200, 300, n)
    phase = 2 * np.pi * np.cumsum(sweep_freq) / sr
    tone = np.sin(phase)
    mix = noise_filtered * 0.7 + tone * 0.3
    envelope = np.sin(np.pi * t / duration) ** 1.5
    audio = mix * envelope
    return audio / (np.max(np.abs(audio)) + 1e-6) * 0.8


def _ensure_sfx_files():
    ding_path, whoosh_path = "_sfx_ding.wav", "_sfx_whoosh.wav"
    _write_wav(ding_path, _make_ding())
    _write_wav(whoosh_path, _make_whoosh())
    return ding_path, whoosh_path


# ---------------------------------------------------------------------------
# Motion helpers
# ---------------------------------------------------------------------------

# Max safe zoom before the center-crop starts eating into real content: the
# top badge sits 60px from the top edge and the caption bar sits ~102px from
# the bottom edge (the tightest of the two), which caps us at amount<=0.0625
# (1920 * amount / 2 <= 60). Keeping a safety cushion below that.
SAFE_ZOOM_AMOUNT = 0.05


def zoom(t, d, amount=SAFE_ZOOM_AMOUNT):
    return 1 + amount * (t / d)


def _scaled_crop_frame(pil_img, scale, size=(1080, 1920)):
    """Resize a PIL image by `scale` (>=1.0) and center-crop back to `size`.
    Always returns an array of EXACTLY `size` -- this sidesteps the MoviePy
    vfx.Resize + CrossFadeIn interaction bug where a dynamically-resized
    clip's declared .size doesn't match its actual per-frame array size,
    which shows up as black bars creeping in at the frame edges."""
    w, h = size
    sw, sh = int(w * scale + 0.5), int(h * scale + 0.5)
    resized = pil_img.resize((sw, sh))
    left = (sw - w) // 2
    top = (sh - h) // 2
    cropped = resized.crop((left, top, left + w, top + h))
    return np.array(cropped)


def _pop_in_clip(pil_img, duration, fps=24, start_scale=1.0 + SAFE_ZOOM_AMOUNT):
    """Punchy 'snap into place' entrance: starts zoomed in, eases down to
    normal scale. Used as the pattern-interrupt cut at the start of every
    segment instead of a flat crossfade -- research on Shorts retention
    flags a pattern-interrupt (zoom/cut) every 5-7s as a key attention reset."""
    n = max(int(duration * fps), 1)
    frames = []
    for i in range(n):
        progress = (i + 1) / n
        eased = 1 - (1 - progress) ** 3  # cubic ease-out
        scale = 1 + (start_scale - 1) * (1 - eased)
        frames.append(_scaled_crop_frame(pil_img, scale))
    return ImageSequenceClip(frames, fps=fps)


# format_mode -> which renderer draws the 3 narrated market segments. All
# four share the exact same narration/captions/timing (only "trend" also
# appends one extra bonus segment at the end) -- this is purely a visual
# swap, which is what keeps content-format variety low-risk: nothing about
# script generation, audio, or segment timing changes per format.
def _render_market_segment(format_mode, commodity, state, records, i, num_markets, date_str, caption, progress):
    if format_mode == "countdown":
        return render_segment_countdown(
            commodity, state, records, i, num_markets, date_str, caption=caption, reveal_progress=progress
        )
    elif format_mode == "spotlight":
        return render_segment_spotlight(
            commodity, state, records, i, num_markets, date_str, caption=caption, reveal_progress=progress
        )
    else:
        return render_segment_market(
            commodity, state, records, i, num_markets, date_str, caption=caption, bar_progress=progress
        )


def make_counter_clip(commodity, state, records, date_str, duration=1.0, fps=15, caption=None):
    try:
        final_val = float(_top_price(records))
    except (TypeError, ValueError):
        final_val = 0
    n = max(int(duration * fps), 1)
    frame_arrays = []
    for i in range(n):
        progress = (i + 1) / n
        eased = 1 - (1 - progress) ** 3
        current = int(final_val * eased)
        img = render_segment_intro(commodity, state, records, date_str, price_override=current, caption=caption)
        frame_arrays.append(np.array(img))
    return ImageSequenceClip(frame_arrays, fps=fps)


def make_video(
    audio_path,
    records,
    state,
    commodity,
    lang,
    output_path="output.mp4",
    date_str="",
    intro_caption=None,
    market_captions=None,
    format_mode="ticker",
    trend_data=None,
    trend_caption=None,
):
    """market_captions: optional list of caption strings, one per market segment
    (same order as the market segments themselves). Pass the matching line from
    the narration script here once it's available -- falls back to no caption
    (card renders exactly as before) when omitted.

    format_mode: "ticker" (default, unchanged data-table look), "trend"
    (adds one Bull vs Bear day-over-day segment after the market segments --
    but only when trend_data is actually available; if format_mode="trend"
    but trend_data is None, e.g. first day with no history yet, this
    silently falls back to "ticker" behaviour since there's nothing to
    show), "countdown" (the same 3 narrated market segments shown as a
    dramatic #1/#2/#3 rank reveal instead of a list), or "spotlight" (the
    same 3 narrated market segments shown as a min/max/modal range gauge).
    countdown/spotlight only change how the 3 market segments are drawn --
    narration, captions and timing are identical to "ticker" in every mode.
    trend_data: {"direction": "up"/"down"/"flat", "pct": float} or None.
    trend_caption: on-screen caption for the trend segment (the matching
    spoken "trend" sentence from generate_script.py), optional.
    """
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    num_markets = min(3, len(records))
    show_trend = format_mode == "trend" and trend_data is not None
    num_segments = num_markets + (1 if show_trend else 0)
    intro_duration = min(8, duration * 0.3)
    remaining = max(duration - intro_duration, 1)
    segment_duration = remaining / max(num_segments, 1)

    clips = []
    tmp_files = []
    sfx_events = []  # (path, start_time)

    ding_path, whoosh_path = _ensure_sfx_files()
    tmp_files.extend([ding_path, whoosh_path])

    counter_duration = min(1.0, intro_duration * 0.3)
    counter_clip = make_counter_clip(
        commodity, state, records, date_str, duration=counter_duration, fps=15, caption=intro_caption
    ).with_start(0)
    clips.append(counter_clip)
    sfx_events.append((ding_path, max(counter_duration - 0.05, 0)))  # price "lands"

    intro_static_duration = max(intro_duration - counter_duration, 0.1)
    intro_img = render_segment_intro(commodity, state, records, date_str, caption=intro_caption)
    intro_path = "_seg_intro.png"
    intro_img.save(intro_path)
    tmp_files.append(intro_path)
    intro_clip = (
        ImageClip(intro_path)
        .with_duration(intro_static_duration)
        .with_start(counter_duration)
        .with_effects([vfx.Resize(lambda t: zoom(t, intro_static_duration))])
        .with_position("center")
    )
    clips.append(intro_clip)

    bar_race_duration = 0.7
    t = intro_duration
    for i in range(num_markets):
        caption = None
        if market_captions and i < len(market_captions):
            caption = market_captions[i]

        # Bars start at 0 for the pop-in (keeps focus on the price/market
        # name landing), then race up to full during the bar_race phase,
        # then stay full for the slow drift -- real chart animation via
        # MoviePy, not just camera movement over a static card.
        seg_img_bars_zero = _render_market_segment(
            format_mode, commodity, state, records, i, num_markets, date_str, caption, 0.0
        )
        seg_img_final = _render_market_segment(
            format_mode, commodity, state, records, i, num_markets, date_str, caption, 1.0
        )
        seg_path = f"_seg_{i}.png"
        seg_img_final.save(seg_path)
        tmp_files.append(seg_path)

        start_t = max(t - FADE, 0)
        this_bar_race_duration = min(bar_race_duration, max(segment_duration * 0.3, 0.2))
        drift_duration = max(segment_duration - this_bar_race_duration, 0.3)

        # Phase 1: punch-zoom pop-in + crossfade (bars still at 0).
        pop_clip = (
            _pop_in_clip(seg_img_bars_zero, duration=FADE, fps=24)
            .with_start(start_t)
            .with_effects([vfx.CrossFadeIn(FADE)])
        )
        clips.append(pop_clip)
        # (whoosh transition SFX removed -- didn't land well; ding-only for now)

        # Phase 2: bars race from 0 to their value, card held still.
        bar_frames = []
        n_bar_frames = max(int(this_bar_race_duration * 20), 1)
        for bf in range(n_bar_frames):
            progress = (bf + 1) / n_bar_frames
            eased = 1 - (1 - progress) ** 3
            frame_img = _render_market_segment(
                format_mode, commodity, state, records, i, num_markets, date_str, caption, eased
            )
            bar_frames.append(np.array(frame_img))
        bar_race_clip = ImageSequenceClip(bar_frames, fps=20).with_start(start_t + FADE)
        clips.append(bar_race_clip)

        # Phase 3: slow Ken Burns drift, bars fully grown.
        drift_clip = (
            ImageClip(seg_path)
            .with_duration(drift_duration)
            .with_start(start_t + FADE + this_bar_race_duration)
            .with_effects([vfx.Resize(lambda tt, d=drift_duration: zoom(tt, d))])
            .with_position("center")
        )
        clips.append(drift_clip)

        t += segment_duration

    if show_trend:
        direction = trend_data["direction"]
        pct = trend_data["pct"]

        trend_img_zero = render_segment_trend(
            commodity, state, records, date_str, direction, pct, caption=trend_caption, reveal_progress=0.0
        )
        trend_img_final = render_segment_trend(
            commodity, state, records, date_str, direction, pct, caption=trend_caption, reveal_progress=1.0
        )
        trend_path = "_seg_trend.png"
        trend_img_final.save(trend_path)
        tmp_files.append(trend_path)

        start_t = max(t - FADE, 0)
        this_reveal_duration = min(bar_race_duration, max(segment_duration * 0.3, 0.2))
        drift_duration = max(segment_duration - this_reveal_duration, 0.3)

        # Phase 1: punch-zoom pop-in + crossfade (percentage still at 0).
        pop_clip = (
            _pop_in_clip(trend_img_zero, duration=FADE, fps=24)
            .with_start(start_t)
            .with_effects([vfx.CrossFadeIn(FADE)])
        )
        clips.append(pop_clip)
        sfx_events.append((ding_path, max(start_t + FADE - 0.05, 0)))  # trend number "lands"

        # Phase 2: percentage counts up from 0 to its real value.
        reveal_frames = []
        n_reveal_frames = max(int(this_reveal_duration * 20), 1)
        for rf in range(n_reveal_frames):
            progress = (rf + 1) / n_reveal_frames
            eased = 1 - (1 - progress) ** 3
            frame_img = render_segment_trend(
                commodity, state, records, date_str, direction, pct, caption=trend_caption, reveal_progress=eased
            )
            reveal_frames.append(np.array(frame_img))
        reveal_clip = ImageSequenceClip(reveal_frames, fps=20).with_start(start_t + FADE)
        clips.append(reveal_clip)

        # Phase 3: slow Ken Burns drift, percentage fully revealed.
        drift_clip = (
            ImageClip(trend_path)
            .with_duration(drift_duration)
            .with_start(start_t + FADE + this_reveal_duration)
            .with_effects([vfx.Resize(lambda tt, d=drift_duration: zoom(tt, d))])
            .with_position("center")
        )
        clips.append(drift_clip)

        t += segment_duration

    def progress_frame(tt):
        arr = np.zeros((26, 1080, 3), dtype="uint8")
        arr[:, :] = [60, 70, 95]
        w = max(int((tt / duration) * 1080), 1)
        arr[:, :w] = [34, 197, 94]
        return arr

    progress_clip = VideoClip(progress_frame, duration=duration).with_position((0, 1870))
    clips.append(progress_clip)

    final = CompositeVideoClip(clips, size=(1080, 1920)).with_duration(duration)

    audio_tracks = [audio]
    for sfx_path, start_time in sfx_events:
        sfx_clip = AudioFileClip(sfx_path).with_start(start_time).with_effects([afx.MultiplyVolume(0.55)])
        audio_tracks.append(sfx_clip)
    mixed_audio = CompositeAudioClip(audio_tracks).with_duration(duration)

    final = final.with_audio(mixed_audio)
    final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

    for f in tmp_files:
        if os.path.exists(f):
            os.remove(f)

    return output_path
