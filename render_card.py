import math
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# Legacy assets (still used by render_vertical_card / render_thumbnail below).
BOLD_FONT = "assets/fonts/NotoSansDevanagari-Bold.ttf"
REGULAR_FONT = "assets/fonts/NotoSansDevanagari-Regular.ttf"

# Fusion-style assets (the approved "A + B" design). Real Google Fonts --
# download once and drop into assets/fonts/ (see handoff notes).
BALOO_BOLD = "assets/fonts/Baloo2-Bold.ttf"
MONO_SEMIBOLD = "assets/fonts/IBMPlexMono-SemiBold.ttf"
WORK_SANS_BOLD = "assets/fonts/WorkSans-Bold.ttf"
WORK_SANS_MEDIUM = "assets/fonts/WorkSans-Medium.ttf"

BG_COLOR = (15, 23, 42)
CARD_COLOR = (30, 41, 59)
BORDER_COLOR = (51, 65, 85)
ACCENT_GREEN = (16, 185, 129)
ACCENT_RED = (244, 63, 94)
GOLD = (250, 204, 21)
WHITE = (255, 255, 255)
GREY = (148, 163, 184)

DARK = (58, 20, 0)          # #3A1400 -- ink used everywhere in the fusion design
CREAM = (255, 233, 199)     # #FFE9C7
CREAM_LIGHT = (255, 246, 232)  # #FFF6E8 -- list box fill

FUSION_STYLE = {
    "onion": {"bg": (255, 159, 69), "icon": (232, 93, 160), "label": (255, 217, 125), "accent": "sprout"},
    "potato": {"bg": (242, 200, 121), "icon": (185, 140, 85), "label": (255, 240, 194), "accent": "spots"},
    "tomato": {"bg": (255, 122, 89), "icon": (226, 60, 60), "label": (255, 211, 194), "accent": "calyx"},
    "wheat": {"bg": (246, 214, 93), "icon": (216, 167, 46), "label": (255, 243, 176), "accent": "grain"},
}
FUSION_DEFAULT = {"bg": (255, 159, 69), "icon": (122, 140, 255), "label": (233, 236, 255), "accent": None}


def _font(path, size):
    return ImageFont.truetype(path, size)


def _top_price(records):
    prices = [int(r.get("modal_price", 0)) for r in records if r.get("modal_price")]
    return max(prices) if prices else 0


def _style_for(commodity):
    name = commodity.strip().lower()
    for key, style in FUSION_STYLE.items():
        if key in name:
            return style
    return FUSION_DEFAULT


def _boost_saturation(img_rgb, factor=1.1):
    return ImageEnhance.Color(img_rgb).enhance(factor)


# ---------------------------------------------------------------------------
# Small drawing helpers
# ---------------------------------------------------------------------------

def _rounded_badge(text, font, fg, bg, pad_x=14, pad_y=7, radius=999, border=None, angle=0):
    """Returns an RGBA image of a pill-shaped badge, optionally rotated."""
    tmp = Image.new("RGBA", (1, 1))
    td = ImageDraw.Draw(tmp)
    tw = td.textlength(text, font=font)
    asc, desc = font.getmetrics()
    th = asc + desc
    w, h = int(tw + pad_x * 2), int(th + pad_y * 2)
    badge = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(badge)
    outline = (*DARK, 255) if border else None
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=min(radius, h // 2), fill=(*bg, 255),
                         outline=outline, width=border or 0)
    d.text((pad_x, pad_y - desc // 3), text, font=font, fill=(*fg, 255))
    if angle:
        badge = badge.rotate(angle, expand=True, resample=Image.BICUBIC)
    return badge


def _flat_icon(size, fill_color, accent=None):
    """Flat illustrated commodity icon: filled shape + white highlight + dark outline."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy, rx, ry = size // 2, int(size * 0.56), int(size * 0.37), int(size * 0.34)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(*fill_color, 255), outline=(*DARK, 255), width=max(size // 22, 3))
    hlx, hly = int(size * 0.36), int(size * 0.42)
    d.ellipse([hlx - size * 0.12, hly - size * 0.09, hlx + size * 0.12, hly + size * 0.09], fill=(255, 255, 255, 90))
    d.line([cx, cy - ry, cx - size * 0.03, cy - ry - size * 0.19], fill=(*DARK, 255), width=max(size // 22, 3))
    sprout = (78, 159, 63, 255)
    d.line([cx - size * 0.02, cy - ry - size * 0.19, cx - size * 0.09, cy - ry - size * 0.30], fill=sprout, width=max(size // 15, 4))
    d.line([cx, cy - ry - size * 0.17, cx + size * 0.06, cy - ry - size * 0.28], fill=sprout, width=max(size // 15, 4))

    if accent == "spots":
        for dx, dy in [(-0.35, -0.05), (0.28, 0.15), (-0.05, 0.35), (0.35, -0.2)]:
            r = size * 0.03
            d.ellipse([cx + dx * rx - r, cy + dy * ry - r, cx + dx * rx + r, cy + dy * ry + r], fill=(*DARK, 200))
    elif accent == "calyx":
        for ang in range(-90, 271, 72):
            x2 = cx + rx * 0.55 * math.cos(math.radians(ang))
            y2 = (cy - ry * 0.7) + ry * 0.55 * math.sin(math.radians(ang))
            d.line([cx, cy - ry * 0.7, x2, y2], fill=sprout, width=max(size // 20, 3))
    elif accent == "grain":
        for i in range(-2, 3):
            xx = cx + i * rx * 0.28
            d.ellipse([xx - size * 0.02, cy - ry * 0.5, xx + size * 0.02, cy - ry * 0.2], fill=(255, 240, 180, 230))
    return img


def _decorative_rings(w, h, cx, cy, color=(*DARK, 36)):
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for r in (int(h * 0.15), int(h * 0.11)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=4)
    return layer


def _rounded_panel(w, h, radius, fill, outline=None, width=0):
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=(*fill, 255),
                         outline=(*outline, 255) if outline else None, width=width)
    return layer


def _dashed_rounded_panel(w, h, radius, fill, dash_color, dash_len=14, gap_len=10, width=3):
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=(*fill, 255))
    # dashed outline: walk the perimeter of the rounded rect approximately via straight edges
    pts = [(radius, 0), (w - radius, 0), (w, radius), (w, h - radius), (w - radius, h),
           (radius, h), (0, h - radius), (0, radius)]

    def _dashed_line(p0, p1):
        x0, y0 = p0
        x1, y1 = p1
        length = math.hypot(x1 - x0, y1 - y0)
        if length == 0:
            return
        steps = max(int(length / (dash_len + gap_len)), 1)
        for i in range(steps + 1):
            t0 = i * (dash_len + gap_len) / length
            t1 = min(t0 + dash_len / length, 1)
            if t0 >= 1:
                break
            sx, sy = x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0
            ex, ey = x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1
            d.line([sx, sy, ex, ey], fill=(*dash_color, 255), width=width)

    _dashed_line((radius, 0), (w - radius, 0))
    _dashed_line((w, radius), (w, h - radius))
    _dashed_line((w - radius, h), (radius, h))
    _dashed_line((0, h - radius), (0, radius))
    return layer


def _wrap_text(text, font, max_width, measure_fn):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if measure_fn(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_caption(base, text, W=1080, H=1920, font_size=34, max_lines=3, y0=None):
    """Captions mirror the actual (Hindi/Devanagari) narration, so this MUST
    use a Devanagari-capable font -- Work Sans / Baloo 2 / IBM Plex Mono
    (used elsewhere on the card for English words and digits) don't cover
    Devanagari glyphs and would render as blank boxes."""
    if not text:
        return None
    font = _font(BOLD_FONT, font_size)
    tmp_draw = ImageDraw.Draw(base)
    pad_x = 60
    max_w = W - 2 * pad_x - 50
    lines = _wrap_text(text, font, max_w, tmp_draw.textlength)[:max_lines]
    line_h = int(font_size * 1.4)
    box_h = line_h * len(lines) + 50
    if y0 is None:
        y0 = H - 280
    panel = _dashed_rounded_panel(W - 2 * pad_x, box_h, 28, CREAM, DARK, width=3)
    base.alpha_composite(panel, (pad_x, int(y0)))
    d = ImageDraw.Draw(base)
    ty = y0 + 24
    for line in lines:
        tw = d.textlength(line, font=font)
        d.text(((W - tw) // 2, ty), line, fill=(*DARK, 255), font=font)
        ty += line_h
    return y0, y0 + box_h


# ---------------------------------------------------------------------------
# Legacy layout -- kept for reference only, nothing in the current pipeline
# calls this anymore (make_thumbnail.py uses the Fusion-style render_thumbnail
# below).
# ---------------------------------------------------------------------------

def render_vertical_card(commodity, state, records, date_str, max_markets=6):
    """1080x1920 background used for the Shorts video. (legacy / not used by current pipeline)"""
    width, height = 1080, 1920
    img = Image.new("RGB", (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    pad = 60
    y = 70

    draw.rectangle([pad, y, pad + 340, y + 80], fill=ACCENT_RED)
    draw.text((pad + 25, y + 20), f"आज  {date_str}", fill=WHITE, font=_font(BOLD_FONT, 34))
    y += 80 + 50

    draw.text((pad, y), f"{commodity} Mandi Bhav", fill=WHITE, font=_font(BOLD_FONT, 72))
    y += 90
    draw.text((pad, y), f"{state} APMC Mandi", fill=GREY, font=_font(REGULAR_FONT, 38))
    y += 90

    top_price = _top_price(records)
    box_h = 180
    draw.rectangle([pad, y, width - pad, y + box_h], fill=CARD_COLOR, outline=BORDER_COLOR, width=3)
    draw.text((pad + 35, y + 40), f"Rs. {top_price}/Quintal", fill=GOLD, font=_font(BOLD_FONT, 88))
    y += box_h + 60

    f_market = _font(BOLD_FONT, 38)
    f_price = _font(REGULAR_FONT, 38)
    row_h = 95
    for r in records[:max_markets]:
        market = str(r.get("market", ""))[:24]
        price_text = f"Rs.{r.get('modal_price', 'N/A')}"
        draw.rectangle([pad, y, width - pad, y + row_h - 12], fill=CARD_COLOR)
        draw.text((pad + 28, y + 20), market, fill=WHITE, font=f_market)
        tw = draw.textlength(price_text, font=f_price)
        draw.text((width - pad - 28 - tw, y + 22), price_text, fill=ACCENT_GREEN, font=f_price)
        y += row_h

    draw.text((pad, height - 110), "TaazaBhav", fill=ACCENT_GREEN, font=_font(BOLD_FONT, 42))
    return img


# ---------------------------------------------------------------------------
# Fusion-style thumbnail (1280x720) -- matches the same palette/fonts/icon
# style used across all the video segments instead of the old flat design.
# Built to still read clearly at small feed/search sizes: one big flat icon,
# one big commodity name, one big price -- nothing smaller/secondary that
# would turn to mush when YouTube shrinks it.
# ---------------------------------------------------------------------------

def render_thumbnail(commodity, state, records, date_str):
    W, H = 1280, 720
    style = _style_for(commodity)
    base = Image.new("RGBA", (W, H), (*style["bg"], 255))
    pad = 50

    rings = _decorative_rings(W, H, int(W * 0.88), int(H * 0.2))
    base.alpha_composite(rings, (0, 0))

    brand = _rounded_badge("TAAZABHAV", _font(BALOO_BOLD, 30), CREAM, DARK, pad_x=20, pad_y=12, angle=-3)
    base.alpha_composite(brand, (pad, 34))
    date_badge = _rounded_badge(date_str.upper(), _font(BALOO_BOLD, 24), DARK, CREAM, pad_x=18, pad_y=11, border=3)
    base.alpha_composite(date_badge, (W - pad - date_badge.width, 38))

    icon_size = 260
    icon = _flat_icon(icon_size, style["icon"], style["accent"])
    icon_x = pad
    icon_y = (H - icon_size) // 2 + 20
    base.alpha_composite(icon, (icon_x, icon_y))

    d = ImageDraw.Draw(base)
    name_font = _font(BALOO_BOLD, 92)
    name_x = icon_x + icon_size + 16
    d.text((name_x, icon_y + 4), commodity, fill=(*DARK, 255), font=name_font)
    sub_font = _font(WORK_SANS_MEDIUM, 36)
    d.text((name_x, icon_y + 112), f"{state} Mandi Bhav", fill=(91, 38, 0, 255), font=sub_font)

    top_price = _top_price(records)
    price_font = _font(BALOO_BOLD, 108)
    label_font = _font(BALOO_BOLD, 30)
    price_text = f"Rs. {top_price}"
    ptw = d.textlength(price_text, font=price_font)
    card_w = int(max(ptw, 440) + 90)
    card_h = 220
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=34, fill=(*DARK, 255))
    cd.text((36, 22), "AAJ KA BHAV", fill=(*style["label"], 255), font=label_font)
    cd.text((36, 62), price_text, fill=(*CREAM, 255), font=price_font)
    card = card.rotate(-2, expand=True, resample=Image.BICUBIC)
    card_x = W - pad - card.width
    card_y = H - pad - card.height
    base.alpha_composite(card, (card_x, card_y))

    return _boost_saturation(base.convert("RGB"))


# ---------------------------------------------------------------------------
# Fusion layout (approved: A "Market Ticker" data-table + B "Mandi Mela" energy)
# ---------------------------------------------------------------------------

def render_segment_intro(commodity, state, records, date_str, price_override=None, caption=None):
    W, H = 1080, 1920
    style = _style_for(commodity)
    base = Image.new("RGBA", (W, H), (*style["bg"], 255))
    pad = 60

    rings = _decorative_rings(W, H, int(W * 0.86), int(H * 0.07))
    base.alpha_composite(rings, (0, 0))

    brand = _rounded_badge("TAAZABHAV", _font(BALOO_BOLD, 30), CREAM, DARK, pad_x=22, pad_y=13, angle=-3)
    base.alpha_composite(brand, (pad, 62))
    date_badge = _rounded_badge(date_str.upper(), _font(BALOO_BOLD, 26), DARK, CREAM, pad_x=20, pad_y=12, border=3)
    base.alpha_composite(date_badge, (W - pad - date_badge.width, 66))

    icon_size = 210
    icon = _flat_icon(icon_size, style["icon"], style["accent"])
    icon_x = pad
    icon_y = 178
    base.alpha_composite(icon, (icon_x, icon_y))

    d = ImageDraw.Draw(base)
    name_font = _font(BALOO_BOLD, 76)
    d.text((icon_x + icon_size + 26, icon_y + 40), commodity, fill=(*DARK, 255), font=name_font)
    sub_font = _font(WORK_SANS_MEDIUM, 32)
    d.text((icon_x + icon_size + 26, icon_y + 130), f"{state} Mandi", fill=(91, 38, 0, 255), font=sub_font)

    # price card (slightly rotated, matches the approved mockup)
    top_price = price_override if price_override is not None else _top_price(records)
    price_font = _font(BALOO_BOLD, 128)
    label_font = _font(BALOO_BOLD, 30)
    unit_font = _font(WORK_SANS_MEDIUM, 30)
    price_text = f"Rs. {top_price}"
    ptw = ImageDraw.Draw(base).textlength(price_text, font=price_font)
    card_w, card_h = int(max(ptw, 600) + 100), 300
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=40, fill=(*DARK, 255))
    cd.text((44, 30), "AAJ KA BHAV", fill=(*style["label"], 255), font=label_font)
    cd.text((44, 78), price_text, fill=(*CREAM, 255), font=price_font)
    cd.text((44, 226), f"per Quintal  •  {records[0].get('market','') if records else ''}", fill=(232, 201, 163, 255), font=unit_font)
    card = card.rotate(-1.3, expand=True, resample=Image.BICUBIC)
    card_y = icon_y + icon_size + 40
    base.alpha_composite(card, (pad - 6, card_y))

    y = card_y + card.height + 34

    d = ImageDraw.Draw(base)
    d.text((pad, y), "OTHER MANDIS TODAY", fill=(*DARK, 255), font=_font(BALOO_BOLD, 32))
    y += 58

    list_w = W - 2 * pad
    row_h = 92
    n_rows = min(3, len(records))
    list_h = row_h * n_rows + 20
    list_panel = _rounded_panel(list_w, list_h, 30, CREAM_LIGHT, outline=DARK, width=4)
    base.alpha_composite(list_panel, (pad, int(y)))
    d = ImageDraw.Draw(base)
    row_font = _font(WORK_SANS_BOLD, 32)
    price_row_font = _font(MONO_SEMIBOLD, 34)
    ry = y + 10
    for i, r in enumerate(records[:n_rows]):
        name = str(r.get("market", ""))[:20]
        price = r.get("modal_price", "N/A")
        if i > 0:
            d.line([(pad + 30, ry), (pad + list_w - 30, ry)], fill=(240, 223, 192, 255), width=2)
        d.text((pad + 30, ry + 26), name, fill=(91, 38, 0, 255), font=row_font)
        pt = f"Rs.{price}"
        tw = d.textlength(pt, font=price_row_font)
        d.text((pad + list_w - 30 - tw, ry + 24), pt, fill=(*DARK, 255), font=price_row_font)
        ry += row_h
    y += list_h + 30

    if caption:
        draw_caption(base, caption, W, H, font_size=34, max_lines=3, y0=max(y, H - 260))

    return _boost_saturation(base.convert("RGB"))


def render_segment_market(commodity, state, records, index, total, date_str, caption=None, bar_progress=1.0):
    W, H = 1080, 1920
    style = _style_for(commodity)
    base = Image.new("RGBA", (W, H), (*style["bg"], 255))
    pad = 60

    rings = _decorative_rings(W, H, int(W * 0.88), int(H * 0.06))
    base.alpha_composite(rings, (0, 0))

    brand = _rounded_badge("TAAZABHAV", _font(BALOO_BOLD, 26), CREAM, DARK, pad_x=18, pad_y=11, angle=-3)
    base.alpha_composite(brand, (pad, 58))

    dot_r, gap = 9, 30
    dot_x = W - pad - total * gap
    d = ImageDraw.Draw(base)
    for i in range(total):
        color = style["icon"] if i == index else (*DARK, 70)
        cx = dot_x + i * gap
        d.ellipse([cx, 66, cx + dot_r * 2, 66 + dot_r * 2], fill=color if i == index else color)

    icon_size = 150
    icon = _flat_icon(icon_size, style["icon"], style["accent"])
    icon_x = (W - icon_size) // 2
    icon_y = 150
    base.alpha_composite(icon, (icon_x, icon_y))

    d = ImageDraw.Draw(base)
    name_font = _font(BALOO_BOLD, 52)
    tw = d.textlength(commodity, font=name_font)
    d.text(((W - tw) // 2, icon_y + icon_size + 20), commodity, fill=(*DARK, 255), font=name_font)

    market = records[index]
    market_name = str(market.get("market", ""))[:24]
    price = market.get("modal_price", "N/A")

    card_y = icon_y + icon_size + 100
    card_h = 300
    card = _rounded_panel(W - 2 * pad, card_h, 40, DARK)
    base.alpha_composite(card, (pad, card_y))
    d = ImageDraw.Draw(base)
    mn_font = _font(BALOO_BOLD, 44)
    tw = d.textlength(market_name, font=mn_font)
    d.text(((W - tw) // 2, card_y + 34), market_name, fill=(*CREAM, 255), font=mn_font)
    price_text = f"Rs. {price}"
    price_font = _font(BALOO_BOLD, 92)
    tw = d.textlength(price_text, font=price_font)
    d.text(((W - tw) // 2, card_y + 100), price_text, fill=(*style["label"], 255), font=price_font)
    unit_font = _font(WORK_SANS_MEDIUM, 28)
    unit_text = "per Quintal"
    tw = d.textlength(unit_text, font=unit_font)
    d.text(((W - tw) // 2, card_y + 224), unit_text, fill=(232, 201, 163, 255), font=unit_font)

    y = card_y + card_h + 44
    d.text((pad, y), "OTHER MANDIS TODAY", fill=(*DARK, 255), font=_font(BALOO_BOLD, 30))
    y += 56

    others = [(i, r) for i, r in enumerate(records[:6]) if i != index]

    def _price_of(r):
        try:
            return float(r.get("modal_price", 0))
        except (TypeError, ValueError):
            return 0.0

    max_p = max([_price_of(r) for _, r in others] + [1.0])
    row_h = 88
    list_w = W - 2 * pad
    row_font = _font(WORK_SANS_BOLD, 30)
    price_row_font = _font(MONO_SEMIBOLD, 30)
    for i, r in others:
        name = str(r.get("market", ""))[:20]
        p = r.get("modal_price", "N/A")
        row_h_fill = row_h - 16
        panel = _rounded_panel(list_w, row_h_fill, 18, CREAM_LIGHT, outline=DARK, width=3)
        base.alpha_composite(panel, (pad, int(y)))
        frac = min(_price_of(r) / max_p, 1.0) * max(min(bar_progress, 1.0), 0.0)
        bar_w = int((list_w - 6) * frac)
        if bar_w > 6:
            bar = _rounded_panel(bar_w, row_h_fill - 6, 15, style["icon"])
            base.alpha_composite(bar, (pad + 3, int(y) + 3))
        d = ImageDraw.Draw(base)
        d.text((pad + 26, y + 18), name, fill=(*DARK, 255), font=row_font)
        pt = f"Rs.{p}"
        tw = d.textlength(pt, font=price_row_font)
        d.text((W - pad - 26 - tw, y + 18), pt, fill=(*DARK, 255), font=price_row_font)
        y += row_h
        if y > H - 300:
            break

    if caption:
        draw_caption(base, caption, W, H, font_size=32, max_lines=3, y0=H - 250)

    return _boost_saturation(base.convert("RGB"))


# ---------------------------------------------------------------------------
# Bull vs Bear -- day-over-day trend segment (content-variety format).
# Only rendered when real yesterday-vs-today price history is available.
# ---------------------------------------------------------------------------

def render_segment_trend(commodity, state, records, date_str, direction, pct, caption=None, reveal_progress=1.0):
    """direction is "up" / "down" / "flat" (matches price_history.compute_trend()'s
    return value), pct is the percentage change. reveal_progress (0..1) drives a
    count-up animation of the percentage number, same pattern as the opening
    price counter."""
    W, H = 1080, 1920
    style = _style_for(commodity)
    base = Image.new("RGBA", (W, H), (*style["bg"], 255))
    pad = 60

    rings = _decorative_rings(W, H, int(W * 0.88), int(H * 0.06))
    base.alpha_composite(rings, (0, 0))

    brand = _rounded_badge("TAAZABHAV", _font(BALOO_BOLD, 26), CREAM, DARK, pad_x=18, pad_y=11, angle=-3)
    base.alpha_composite(brand, (pad, 58))
    date_badge = _rounded_badge(date_str.upper(), _font(BALOO_BOLD, 22), DARK, CREAM, pad_x=16, pad_y=10, border=3)
    base.alpha_composite(date_badge, (W - pad - date_badge.width, 62))

    icon_size = 150
    icon = _flat_icon(icon_size, style["icon"], style["accent"])
    icon_x = (W - icon_size) // 2
    icon_y = 170
    base.alpha_composite(icon, (icon_x, icon_y))

    d = ImageDraw.Draw(base)
    name_font = _font(BALOO_BOLD, 52)
    tw = d.textlength(commodity, font=name_font)
    d.text(((W - tw) // 2, icon_y + icon_size + 20), commodity, fill=(*DARK, 255), font=name_font)

    top_market = str(records[0].get("market", ""))[:22] if records else ""
    today_price = records[0].get("modal_price", "N/A") if records else "N/A"

    if direction == "up":
        trend_color = (52, 199, 89)     # green -- bullish
        trend_label = "TREND: UP"
    elif direction == "down":
        trend_color = (239, 68, 68)     # red -- bearish
        trend_label = "TREND: DOWN"
    else:
        trend_color = (161, 161, 170)   # grey -- flat
        trend_label = "TREND: STEADY"

    card_y = icon_y + icon_size + 110
    card_h = 480
    card = _rounded_panel(W - 2 * pad, card_h, 40, DARK)
    base.alpha_composite(card, (pad, card_y))
    d = ImageDraw.Draw(base)

    sub_font = _font(WORK_SANS_MEDIUM, 28)
    sub_text = f"{top_market}  •  KAL KE MUKABLE"
    tw = d.textlength(sub_text, font=sub_font)
    d.text(((W - tw) // 2, card_y + 40), sub_text, fill=(232, 201, 163, 255), font=sub_font)

    # Animated arrow (or flat dash) + count-up percentage, centered together.
    shown_pct = abs(pct) * max(min(reveal_progress, 1.0), 0.0)
    pct_text = f"{shown_pct:.1f}%"
    pct_font = _font(BALOO_BOLD, 104)
    pct_w = d.textlength(pct_text, font=pct_font)
    arrow_size = 66
    gap = 22
    total_w = arrow_size + gap + pct_w
    start_x = (W - total_w) / 2
    arrow_cx = start_x + arrow_size / 2
    arrow_cy = card_y + 210

    if direction == "up":
        h = arrow_size * 0.9
        d.polygon(
            [(arrow_cx, arrow_cy - h / 2), (arrow_cx - arrow_size / 2, arrow_cy + h / 2),
             (arrow_cx + arrow_size / 2, arrow_cy + h / 2)],
            fill=(*trend_color, 255),
        )
    elif direction == "down":
        h = arrow_size * 0.9
        d.polygon(
            [(arrow_cx, arrow_cy + h / 2), (arrow_cx - arrow_size / 2, arrow_cy - h / 2),
             (arrow_cx + arrow_size / 2, arrow_cy - h / 2)],
            fill=(*trend_color, 255),
        )
    else:
        d.rounded_rectangle(
            [arrow_cx - arrow_size / 2, arrow_cy - 9, arrow_cx + arrow_size / 2, arrow_cy + 9],
            radius=8, fill=(*trend_color, 255),
        )

    d.text((start_x + arrow_size + gap, card_y + 158), pct_text, fill=(*trend_color, 255), font=pct_font)

    label_font = _font(BALOO_BOLD, 36)
    tw = d.textlength(trend_label, font=label_font)
    d.text(((W - tw) // 2, card_y + 300), trend_label, fill=(*CREAM, 255), font=label_font)

    price_font = _font(MONO_SEMIBOLD, 34)
    price_text = f"Aaj: Rs. {today_price} / Quintal"
    tw = d.textlength(price_text, font=price_font)
    d.text(((W - tw) // 2, card_y + 370), price_text, fill=(232, 201, 163, 255), font=price_font)

    if caption:
        draw_caption(base, caption, W, H, font_size=32, max_lines=3, y0=H - 250)

    return _boost_saturation(base.convert("RGB"))


# ---------------------------------------------------------------------------
# Top Countdown -- reinterprets the SAME 3 narrated market segments as a
# dramatic rank-reveal (#3/#2/#1 among the narrated set) instead of the
# ticker format's data-table list. No script/caption/timing changes needed:
# it's a pure visual swap on top of the exact same narration.
# ---------------------------------------------------------------------------

def render_segment_countdown(commodity, state, records, index, total, date_str, caption=None, reveal_progress=1.0):
    """index/total match render_segment_market's signature so make_video.py
    can swap renderers by format_mode without touching timing logic. Markets
    are ranked #1 (highest modal price) .. #{total} among the narrated set
    (records[:total]); reveal_progress (0..1) counts the price up as it
    lands, same pattern as the opening price counter."""
    W, H = 1080, 1920
    style = _style_for(commodity)
    base = Image.new("RGBA", (W, H), (*style["bg"], 255))
    pad = 60

    rings = _decorative_rings(W, H, int(W * 0.88), int(H * 0.08))
    base.alpha_composite(rings, (0, 0))

    brand = _rounded_badge("TAAZABHAV", _font(BALOO_BOLD, 24), CREAM, DARK, pad_x=16, pad_y=10, angle=-3)
    base.alpha_composite(brand, (pad, 50))
    date_badge = _rounded_badge(date_str.upper(), _font(BALOO_BOLD, 20), DARK, CREAM, pad_x=14, pad_y=9, border=3)
    base.alpha_composite(date_badge, (W - pad - date_badge.width, 54))

    top_n = records[:total]

    def _price_of(r):
        try:
            return float(r.get("modal_price", 0))
        except (TypeError, ValueError):
            return 0.0

    ranked_idx = sorted(range(len(top_n)), key=lambda i: _price_of(top_n[i]), reverse=True)
    rank = ranked_idx.index(index) + 1

    y = 190
    rank_font = _font(BALOO_BOLD, 210)
    rank_badge = _rounded_badge(f"#{rank}", rank_font, CREAM, DARK, pad_x=34, pad_y=22, radius=56, angle=-2)
    base.alpha_composite(rank_badge, ((W - rank_badge.width) // 2, y))
    y += rank_badge.height + 26

    d = ImageDraw.Draw(base)
    label_font = _font(BALOO_BOLD, 32)
    label_text = f"AAJ KA TOP {total} MANDI"
    tw = d.textlength(label_text, font=label_font)
    d.text(((W - tw) // 2, y), label_text, fill=(*DARK, 255), font=label_font)
    y += 60

    icon_size = 120
    icon = _flat_icon(icon_size, style["icon"], style["accent"])
    base.alpha_composite(icon, ((W - icon_size) // 2, int(y)))
    d = ImageDraw.Draw(base)
    name_font = _font(BALOO_BOLD, 46)
    tw = d.textlength(commodity, font=name_font)
    d.text(((W - tw) // 2, y + icon_size + 14), commodity, fill=(*DARK, 255), font=name_font)
    y += icon_size + 14 + 70

    market = top_n[index]
    market_name = str(market.get("market", ""))[:24]
    final_price = market.get("modal_price", "N/A")
    try:
        final_price_val = float(final_price)
        shown_price = int(final_price_val * max(min(reveal_progress, 1.0), 0.0))
        price_text = f"Rs. {shown_price}"
    except (TypeError, ValueError):
        price_text = f"Rs. {final_price}"

    card_h = 300
    card = _rounded_panel(W - 2 * pad, card_h, 40, DARK)
    base.alpha_composite(card, (pad, int(y)))
    d = ImageDraw.Draw(base)
    mn_font = _font(BALOO_BOLD, 42)
    tw = d.textlength(market_name, font=mn_font)
    d.text(((W - tw) // 2, y + 34), market_name, fill=(*CREAM, 255), font=mn_font)
    price_font = _font(BALOO_BOLD, 88)
    tw = d.textlength(price_text, font=price_font)
    d.text(((W - tw) // 2, y + 100), price_text, fill=(*style["label"], 255), font=price_font)
    unit_font = _font(WORK_SANS_MEDIUM, 28)
    unit_text = "per Quintal"
    tw = d.textlength(unit_text, font=unit_font)
    d.text(((W - tw) // 2, y + 224), unit_text, fill=(232, 201, 163, 255), font=unit_font)

    if caption:
        draw_caption(base, caption, W, H, font_size=32, max_lines=3, y0=H - 250)

    return _boost_saturation(base.convert("RGB"))


# ---------------------------------------------------------------------------
# Mandi Spotlight -- reinterprets the SAME 3 narrated market segments as a
# focused min/max/modal range gauge instead of the ticker format's plain
# price + list. Uses min_price/max_price fields already fetched (and
# already narrated in the "line" template) but not otherwise shown visually.
# ---------------------------------------------------------------------------

def render_segment_spotlight(commodity, state, records, index, total, date_str, caption=None, reveal_progress=1.0):
    """index/total match render_segment_market's signature. reveal_progress
    (0..1) slides the gauge fill and the modal-price pointer in from empty
    to their real values, same phased pop-in/reveal/drift pattern as the
    other formats."""
    W, H = 1080, 1920
    style = _style_for(commodity)
    base = Image.new("RGBA", (W, H), (*style["bg"], 255))
    pad = 60

    rings = _decorative_rings(W, H, int(W * 0.88), int(H * 0.06))
    base.alpha_composite(rings, (0, 0))

    brand = _rounded_badge("TAAZABHAV", _font(BALOO_BOLD, 26), CREAM, DARK, pad_x=18, pad_y=11, angle=-3)
    base.alpha_composite(brand, (pad, 58))

    dot_r, gap = 9, 30
    dot_x = W - pad - total * gap
    d = ImageDraw.Draw(base)
    for i in range(total):
        color = style["icon"] if i == index else (*DARK, 70)
        cx = dot_x + i * gap
        d.ellipse([cx, 66, cx + dot_r * 2, 66 + dot_r * 2], fill=color)

    icon_size = 140
    icon = _flat_icon(icon_size, style["icon"], style["accent"])
    icon_x = (W - icon_size) // 2
    icon_y = 150
    base.alpha_composite(icon, (icon_x, icon_y))

    d = ImageDraw.Draw(base)
    name_font = _font(BALOO_BOLD, 50)
    tw = d.textlength(commodity, font=name_font)
    d.text(((W - tw) // 2, icon_y + icon_size + 18), commodity, fill=(*DARK, 255), font=name_font)

    market = records[index]
    market_name = str(market.get("market", ""))[:24]

    def _num(v, default=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    min_p = _num(market.get("min_price"))
    max_p = _num(market.get("max_price"), default=min_p)
    modal_p = _num(market.get("modal_price"), default=min_p)
    if max_p < min_p:
        max_p = min_p

    card_y = icon_y + icon_size + 92
    card_h = 480
    card = _rounded_panel(W - 2 * pad, card_h, 40, DARK)
    base.alpha_composite(card, (pad, card_y))
    d = ImageDraw.Draw(base)

    mn_font = _font(BALOO_BOLD, 40)
    tw = d.textlength(market_name, font=mn_font)
    d.text(((W - tw) // 2, card_y + 32), market_name, fill=(*CREAM, 255), font=mn_font)

    sub_font = _font(WORK_SANS_MEDIUM, 26)
    sub_text = "AAJ KA RANGE"
    tw = d.textlength(sub_text, font=sub_font)
    d.text(((W - tw) // 2, card_y + 96), sub_text, fill=(232, 201, 163, 255), font=sub_font)

    progress = max(min(reveal_progress, 1.0), 0.0)
    gauge_x0 = pad + 70
    gauge_x1 = W - pad - 70
    gauge_y = card_y + 210
    gauge_w = gauge_x1 - gauge_x0
    gauge_h = 26

    track = _rounded_panel(gauge_w, gauge_h, gauge_h // 2, (91, 55, 30))
    base.alpha_composite(track, (gauge_x0, gauge_y))
    fill_w = int(gauge_w * progress)
    if fill_w > 6:
        fill = _rounded_panel(fill_w, gauge_h, gauge_h // 2, style["icon"])
        base.alpha_composite(fill, (gauge_x0, gauge_y))

    span = max(max_p - min_p, 1.0)
    modal_frac = min(max((modal_p - min_p) / span, 0.0), 1.0)
    pointer_x = gauge_x0 + gauge_w * modal_frac * progress
    d = ImageDraw.Draw(base)
    pointer_r = 20
    d.ellipse(
        [pointer_x - pointer_r, gauge_y + gauge_h / 2 - pointer_r,
         pointer_x + pointer_r, gauge_y + gauge_h / 2 + pointer_r],
        fill=(*CREAM, 255), outline=(*DARK, 255), width=4,
    )

    lbl_font = _font(MONO_SEMIBOLD, 28)
    d.text((gauge_x0, gauge_y + gauge_h + 20), f"MIN {int(min_p)}", fill=(232, 201, 163, 255), font=lbl_font)
    max_text = f"MAX {int(max_p)}"
    tw = d.textlength(max_text, font=lbl_font)
    d.text((gauge_x1 - tw, gauge_y + gauge_h + 20), max_text, fill=(232, 201, 163, 255), font=lbl_font)

    modal_shown = int(modal_p * progress)
    modal_text = f"Rs. {modal_shown}"
    modal_font = _font(BALOO_BOLD, 84)
    tw = d.textlength(modal_text, font=modal_font)
    d.text(((W - tw) // 2, gauge_y + gauge_h + 80), modal_text, fill=(*style["label"], 255), font=modal_font)
    unit_font = _font(WORK_SANS_MEDIUM, 26)
    unit_text = "AVERAGE (MODAL) per Quintal"
    tw = d.textlength(unit_text, font=unit_font)
    d.text(((W - tw) // 2, gauge_y + gauge_h + 190), unit_text, fill=(232, 201, 163, 255), font=unit_font)

    if caption:
        draw_caption(base, caption, W, H, font_size=32, max_lines=3, y0=H - 250)

    return _boost_saturation(base.convert("RGB"))
