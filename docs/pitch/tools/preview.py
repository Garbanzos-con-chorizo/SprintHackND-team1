"""Screenshot every built slide with a headless browser, for visual QA.

Wraps each project/slides/<id>.html in a 1920x1080 page (fonts from deck.json)
and saves <out>/preview/<n>-<id>.png plus contact.html (all slides on one page).
Uses the same browser lookup as the PDF export (Edge, Chrome or Chromium).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from engine.export.pdf import find_browser  # noqa: E402

PAGE = """<!doctype html><html><head><meta charset="utf-8">{links}
<style>html,body{{margin:0;width:1920px;height:1080px;overflow:hidden}}
section{{position:relative;box-sizing:border-box;width:1920px;height:1080px;overflow:hidden}}
section *{{margin:0;box-sizing:border-box}} aside{{display:none}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #D3D2D2;text-align:left;padding:16px 20px}}
ul,ol{{padding-left:1.2em}}</style></head><body>{body}</body></html>"""


def preview(out_dir):
    browser = find_browser()
    if not browser:
        sys.exit("no Edge/Chrome/Chromium found (set PDF_BROWSER)")
    proj = os.path.join(out_dir, "project")
    index = json.load(open(os.path.join(proj, "deck.json"), encoding="utf-8"))
    links = "".join(f'<link rel="stylesheet" href="{f["href"]}">' for f in index["faces"].values() if "href" in f)
    dest = os.path.join(out_dir, "preview")
    os.makedirs(dest, exist_ok=True)
    shots = []
    for n, sid in enumerate(index["order"], 1):
        body = open(os.path.join(proj, "slides", sid + ".html"), encoding="utf-8").read()
        page = os.path.join(dest, f"{n}-{sid}.html")
        open(page, "w", encoding="utf-8").write(PAGE.format(links=links, body=body))
        png = os.path.abspath(os.path.join(dest, f"{n}-{sid}.png"))
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--window-size=1920,1080", "--virtual-time-budget=4000",
                        f"--screenshot={png}", "file:///" + os.path.abspath(page).replace("\\", "/")],
                       check=True, capture_output=True, timeout=60)
        shots.append(os.path.basename(png))
    imgs = "".join(f'<figure><img src="{s}" width="640"><figcaption>{s}</figcaption></figure>' for s in shots)
    open(os.path.join(dest, "contact.html"), "w", encoding="utf-8").write(
        f'<!doctype html><body style="display:flex;flex-wrap:wrap;gap:16px;font-family:sans-serif">{imgs}</body>')
    return [os.path.join(dest, s) for s in shots]
