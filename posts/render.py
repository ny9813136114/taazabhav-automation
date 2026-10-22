# -*- coding: utf-8 -*-
"""Renders one tool post (content/tool_posts.json) to 1080x1350 PNG slides.

Plain HTML + the repo's own fonts, screenshotted by Playwright's Chromium, so
Hindi text is shaped correctly (Pillow cannot join Devanagari conjuncts).
Brand colours from the TaazaBhav identity: green #0F6B3E, dark #0B4A2C,
gold #E09A12 (accent only), cream #FBF6E8."""
import base64
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
W, H = 1080, 1350



def _font(name):
    # Inlined: a page set with set_content() may not load file:// fonts.
    return "data:font/ttf;base64," + base64.b64encode((FONTS / name).read_bytes()).decode()


CSS = f"""
@font-face {{ font-family: Baloo; src: url('{_font("Baloo2-Bold.ttf")}'); }}
@font-face {{ font-family: Noto; src: url('{_font("NotoSansDevanagari-Regular.ttf")}'); }}
@font-face {{ font-family: Noto; font-weight: 700; src: url('{_font("NotoSansDevanagari-Bold.ttf")}'); }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ width: {W}px; height: {H}px; font-family: Noto, sans-serif; color: #0B4A2C; background: #FBF6E8; }}
.s {{ width: {W}px; height: {H}px; padding: 90px 80px 150px; position: relative; display: flex; flex-direction: column; justify-content: center; }}
.dark {{ background: #0F6B3E; color: #FBF6E8; }}
.label {{ font-size: 52px; font-weight: 700; color: #E09A12; margin-bottom: 26px; }}
.big {{ font-family: Baloo; font-size: 124px; line-height: 1.12; }}
.big.num {{ font-size: 190px; }}
.sub {{ font-size: 52px; margin-top: 34px; opacity: .9; line-height: 1.35; }}
h2 {{ font-family: Baloo; font-size: 80px; margin-bottom: 40px; line-height: 1.15; }}
table {{ width: 100%; border-collapse: collapse; font-size: 54px; }}
td {{ padding: 30px 8px; border-bottom: 3px solid #0F6B3E22; vertical-align: top; }}
td.v {{ text-align: right; font-weight: 700; white-space: nowrap; padding-left: 24px; }}
tr.t td {{ border-bottom: 0; border-top: 6px solid #0F6B3E; font-weight: 700; font-size: 62px; color: #0F6B3E; }}
.note {{ font-size: 36px; margin-top: 30px; opacity: .75; }}
ul {{ list-style: none; font-size: 52px; line-height: 1.38; }}
li {{ padding: 20px 0 20px 72px; position: relative; }}
li:before {{ content: '✓'; position: absolute; left: 0; top: 26px; width: 52px; height: 52px; border-radius: 50%;
  background: #0F6B3E; color: #FBF6E8; font-size: 34px; text-align: center; line-height: 52px; }}
.url {{ display: inline-block; margin-top: 46px; background: #FBF6E8; color: #0F6B3E; font-weight: 700; font-size: 58px;
  padding: 24px 40px; border-radius: 22px; }}
.foot {{ position: absolute; left: 80px; right: 80px; bottom: 54px; display: flex; justify-content: space-between;
  font-size: 38px; font-weight: 700; opacity: .85; }}
.leaf {{ color: #E09A12; }}
.s.tr {{ padding-bottom: 190px; }}
.trust {{ position: absolute; left: 80px; right: 80px; bottom: 104px; font-size: 28px; opacity: .7; line-height: 1.3; }}
.claim {{ font-size: 72px; line-height: 1.3; background: #fff; border-left: 14px solid #E09A12; padding: 40px 44px; border-radius: 18px; }}
.stamp {{ display: inline-block; margin-top: 56px; font-family: Baloo; font-size: 120px; padding: 10px 56px; border-radius: 24px;
  border: 10px solid currentColor; transform: rotate(-4deg); }}
.stamp.false {{ color: #B3261E; }} .stamp.half {{ color: #B26A00; }} .stamp.true {{ color: #0F6B3E; }}
.q {{ font-family: Baloo; font-size: 96px; line-height: 1.15; }}
.opt {{ font-size: 60px; font-weight: 700; margin-top: 26px; background: #FBF6E8; color: #0B4A2C; padding: 20px 36px; border-radius: 20px; }}
"""


def _e(s):
    return html.escape(str(s))


CTA_SUB = "लिंक बायो में · सेव करें, शेयर करें"
# Link in the first comment (COMMENTS_LIVE): the same slide goes to FB and IG.
CTA_SUB_COMMENT = "लिंक: FB पर पहला कमेंट, IG पर बायो · सेव करें, शेयर करें"


def _slide(s, i, n, trust="", comment=False):
    k = s["kind"]
    dark = k in ("hook", "cta", "quiz")
    body = ""
    if k in ("hook", "answer"):
        big = _e(s["big"])
        cls = "big num" if k == "answer" and len(str(s["big"])) <= 10 else "big"
        body = f"<div class=label>{_e(s['label'])}</div><div class='{cls}'>{big}</div><div class=sub>{_e(s.get('sub', ''))}</div>"
    elif k == "table":
        rows = "".join(f"<tr><td>{_e(a)}</td><td class=v>{_e(b)}</td></tr>" for a, b in s["rows"])
        if s.get("total"):
            rows += f"<tr class=t><td>{_e(s['total'][0])}</td><td class=v>{_e(s['total'][1])}</td></tr>"
        note = f"<div class=note>* {_e(s['note'])}</div>" if s.get("note") else ""
        body = f"<h2>{_e(s['title'])}</h2><table>{rows}</table>{note}"
    elif k == "list":
        body = f"<h2>{_e(s['title'])}</h2><ul>{''.join(f'<li>{_e(x)}</li>' for x in s['items'])}</ul>"
    elif k == "claim":
        body = (f"<div class=label>{_e(s.get('label', 'सच या झूठ?'))}</div><div class=claim>“{_e(s['claim'])}”</div>"
                f"<div><span class='stamp {_e(s.get('tone', 'false'))}'>{_e(s['verdict'])}</span></div>")
    elif k == "quiz":
        opts = "".join(f"<div class=opt>{_e(o)}</div>" for o in s["options"])
        body = f"<div class=label>{_e(s.get('label', 'हिसाब चैलेंज'))}</div><div class=q>{_e(s['q'])}</div>{opts}<div class=sub>{_e(s.get('sub', ''))}</div>"
    elif k == "cta":
        # A format's question for the comments (PR 3) replaces the slide's words.
        label, big = (s["ask"] if comment and s.get("ask") else (s.get("label", "पूरा हिसाब अपने आंकड़ों से"), s["big"]))
        body = (f"<div class=label>{_e(label)}</div><div class=big>{_e(big)}</div>"
                f"<div><span class=url>{_e(s['url'])}</span></div><div class=sub>{CTA_SUB_COMMENT if comment else CTA_SUB}</div>")
    else:
        raise ValueError(f"unknown slide kind {k}")
    foot = f"<div class=foot><span>ताज़ा<span class=leaf>भाव</span> · taazabhav.com</span><span>{i}/{n}{' →' if i < n else ''}</span></div>"
    # Source + date-checked line on every content slide (Parachar trust line).
    tl = f"<div class=trust>{_e(trust)}</div>" if trust and k != "cta" else ""
    return f"<div class='s{' dark' if dark else ''}{' tr' if tl else ''}'><div class=c>{body}</div>{tl}{foot}</div>"


# A slide with more text than fits is scaled down instead of running into
# the footer.
FIT_JS = """() => {
  const s = document.querySelector('.s'), c = document.querySelector('.c');
  const cs = getComputedStyle(s), room = s.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
  for (let i = 0; i < 4 && c.scrollHeight * (parseFloat(c.style.zoom) || 1) > room; i++)
    c.style.zoom = String((parseFloat(c.style.zoom) || 1) * room / (c.scrollHeight * (parseFloat(c.style.zoom) || 1)) * 0.98);
}"""


def render(post, out_dir):
    """-> list of PNG paths, one per slide."""
    from playwright.sync_api import sync_playwright
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = post["slides"]
    import meta_publish as mp
    comment = bool(post.get("comment_mode") or mp.comments_live())
    paths = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for i, s in enumerate(slides, 1):
            pg.set_content(f"<!doctype html><meta charset=utf-8><style>{CSS}</style>{_slide(s, i, len(slides), post.get('trust', ''), comment)}")
            pg.evaluate("document.fonts.ready")
            pg.evaluate(FIT_JS)
            path = out_dir / f"{post['id']}-{i}.png"
            pg.screenshot(path=str(path), full_page=False)
            paths.append(path)
        b.close()
    return paths
