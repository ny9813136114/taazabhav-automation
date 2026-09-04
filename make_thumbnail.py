from render_card import render_thumbnail


def generate_thumbnail(commodity, state, records, date_str, out_path="thumb.jpg"):
    img = render_thumbnail(commodity, state, records, date_str)
    img.save(out_path, "JPEG", quality=95)
    return out_path