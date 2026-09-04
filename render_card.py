from PIL import Image, ImageDraw, ImageFont

BOLD_FONT = "assets/fonts/NotoSansDevanagari-Bold.ttf"
REGULAR_FONT = "assets/fonts/NotoSansDevanagari-Regular.ttf"

BG_COLOR = (15, 23, 42)
CARD_COLOR = (30, 41, 59)
BORDER_COLOR = (51, 65, 85)
ACCENT_GREEN = (16, 185, 129)
ACCENT_RED = (244, 63, 94)
GOLD = (250, 204, 21)
WHITE = (255, 255, 255)
GREY = (148, 163, 184)


def _font(path, size):
    return ImageFont.truetype(path, size)


def _top_price(records):
    prices = [int(r.get("modal_price", 0)) for r in records if r.get("modal_price")]
    return max(prices) if prices else 0


def render_vertical_card(commodity, state, records, date_str, max_markets=6):
    """1080x1920 background used for the Shorts video."""
    width, height = 1080, 1920
    img = Image.new("RGB", (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    pad = 60
    y = 70

    draw.rectangle([pad, y, pad + 340, y + 80], fill=ACCENT_RED)
    draw.text((pad + 25, y + 20), f"LIVE  {date_str}", fill=WHITE, font=_font(BOLD_FONT, 34))
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


def render_thumbnail(commodity, state, records, date_str):
    """1280x720 compact, high-contrast thumbnail."""
    width, height = 1280, 720
    img = Image.new("RGB", (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    pad = 60

    draw.rectangle([pad, 40, pad + 420, 115], fill=ACCENT_RED)
    draw.text((pad + 20, 55), f"LIVE  {date_str}", fill=WHITE, font=_font(BOLD_FONT, 34))

    draw.text((pad, 160), f"{commodity.upper()} MANDI BHAV", fill=WHITE, font=_font(BOLD_FONT, 66))
    draw.text((pad, 250), f"{state} APMC Mandi", fill=GREY, font=_font(REGULAR_FONT, 40))

    top_price = _top_price(records)
    draw.rectangle([pad, 340, 900, 500], fill=CARD_COLOR, outline=BORDER_COLOR, width=3)
    draw.text((pad + 30, 375), f"Rs. {top_price}/Quintal", fill=GOLD, font=_font(BOLD_FONT, 90))

    draw.text((pad, 560), "Aaj Ka Sabse Achha Bhav", fill=ACCENT_GREEN, font=_font(BOLD_FONT, 40))
    draw.text((width - pad - 340, height - 80), "TaazaBhav.com", fill=ACCENT_GREEN, font=_font(BOLD_FONT, 40))

    return img