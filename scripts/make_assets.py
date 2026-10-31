#!/usr/bin/env python3
"""Generate the favicon set and the default social card into static/. No external fonts or libraries beyond Pillow and a headless Chrome.

  python3 scripts/make_assets.py

Outputs: favicon.svg, favicon.png (32), apple-touch-icon.png (180), favicon.ico (16/32/48),
og-default.svg, og-default.png (1200x630, English), og-default-zh.png (Chinese).
The output is committed, the build only copies static/. Re-run after changing the strings og.tagline in data/i18n/ui.txt.
"""
import os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = os.path.join(ROOT, "static")
ACC, BG, FG, MUT, LINE = "#4f46e5", "#fafaf9", "#18181b", "#71717a", "#e4e4e7"
ERA = ["#a5b4fc", "#818cf8", "#4f46e5"]     # classic, deep, generative: the three era colours of the site, light to dark

def ui(key):
    for line in open(os.path.join(ROOT, "data/i18n/ui.txt"), encoding="utf-8"):
        p = [x.strip() for x in line.rstrip("\n").split(" || ")]
        if len(p) == 3 and p[0] == key: return p[1], p[2]
    sys.exit("missing ui key " + key)

# favicon: an indigo tile with three stacked layers, the shape of a multi-stage pipeline
LAYERS = [(8, 9, 16, 4, 0.55), (6, 14, 20, 4, 0.8), (4, 19, 24, 4, 1.0)]   # x, y, w, h, opacity on a 32x32 grid
def favicon_svg():
    bars = "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="1.5" fill="#fff" fill-opacity="{o}"/>' for x, y, w, h, o in LAYERS)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="{ACC}"/>{bars}</svg>\n'

def favicon_png(size):
    k = 8; S = size * k; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); u = S / 32
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=7 * u, fill=ACC)
    for x, y, w, h, o in LAYERS:
        ov = Image.new("RGBA", (S, S), (0, 0, 0, 0)); ImageDraw.Draw(ov).rounded_rectangle([x * u, y * u, (x + w) * u, (y + h) * u], radius=1.5 * u, fill=(255, 255, 255, int(255 * o)))
        im = Image.alpha_composite(im, ov)
    return im.resize((size, size), Image.LANCZOS)

def og_svg(tag, lang):
    # no web fonts: a system stack, so the PNG is rendered with whatever the box has (Inter and Noto Sans CJK here)
    fam = "Inter, 'Noto Sans CJK SC', -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
    size = 40 if lang == "en" else 42
    words = tag.split(" ") if lang == "en" else None
    if lang == "en":
        mid = len(words) // 2 + 1; lines = [" ".join(words[:mid]), " ".join(words[mid:])]
    else:
        lines = [tag.split("，")[0] + "，", tag.split("，")[1]]
    tl = "".join(f'<text x="80" y="{374 + i * 58}" font-size="{size}" fill="{MUT}">{l}</text>' for i, l in enumerate(lines))
    cards = ""
    for i, c in enumerate(ERA):   # three columns echoing the era timeline
        x = 80 + i * 360
        cards += f'<rect x="{x}" y="470" width="320" height="96" rx="14" fill="#fff" stroke="{LINE}" stroke-width="2"/><rect x="{x}" y="470" width="10" height="96" rx="5" fill="{c}"/>'
        for j, w in enumerate((200, 150)):
            cards += f'<rect x="{x + 34}" y="{494 + j * 28}" width="{w}" height="12" rx="6" fill="{c}" fill-opacity="{0.55 if j else 0.9}"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" font-family="{fam}">
<rect width="1200" height="630" fill="{BG}"/><rect x="0" y="0" width="1200" height="10" fill="{ACC}"/>
<g transform="translate(80 84) scale(2.4)"><rect width="32" height="32" rx="7" fill="{ACC}"/>{"".join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="1.5" fill="#fff" fill-opacity="{o}"/>' for x, y, w, h, o in LAYERS)}</g>
<text x="176" y="156" font-size="64" font-weight="700" fill="{FG}" letter-spacing="-1.5">Rec<tspan fill="{ACC}">Arch</tspan></text>
<text x="80" y="300" font-size="30" font-weight="600" fill="{ACC}" letter-spacing="1">RECOMMENDER &#183; SEARCH &#183; RANKING</text>
{tl}{cards}</svg>
'''

def chrome():
    for n in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        p = shutil.which(n)
        if p: return p
    sys.exit("headless Chrome or Chromium is needed to render the social card")

def render(svg, out):
    with tempfile.TemporaryDirectory() as t:
        f = os.path.join(t, "og.svg"); open(f, "w", encoding="utf-8").write(svg)
        html = os.path.join(t, "og.html"); open(html, "w").write(f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0}}img{{display:block}}</style><img src="og.svg" width="1200" height="630">')
        subprocess.run([chrome(), "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--window-size=1200,630", "--force-device-scale-factor=1",
                        "--virtual-time-budget=2000", f"--screenshot={out}", "file://" + html], check=True, capture_output=True)

if __name__ == "__main__":
    open(os.path.join(ST, "favicon.svg"), "w").write(favicon_svg())
    favicon_png(32).save(os.path.join(ST, "favicon.png")); favicon_png(180).save(os.path.join(ST, "apple-touch-icon.png"))
    favicon_png(48).save(os.path.join(ST, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    en, zh = ui("og.tagline")
    open(os.path.join(ST, "og-default.svg"), "w", encoding="utf-8").write(og_svg(en, "en"))
    render(og_svg(en, "en"), os.path.join(ST, "og-default.png")); render(og_svg(zh, "zh"), os.path.join(ST, "og-default-zh.png"))
    for n in ("favicon.svg", "favicon.png", "apple-touch-icon.png", "favicon.ico", "og-default.svg", "og-default.png", "og-default-zh.png"):
        print(n, os.path.getsize(os.path.join(ST, n)), "bytes")
