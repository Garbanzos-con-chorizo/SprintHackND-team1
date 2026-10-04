"""Check a deck content file and its rendered slides against .claude/skills/slides.

Returns a list of (level, slide_id, message); level is ERROR or WARN.
"""
import json
import os
import re

WORD_BUDGET = {"quotes": 120, "table": 90, "ledger": 60}  # default 40 (speaker-led)
TEXT_RE = re.compile(r"<[^>]+>")


def visible_words(slide_html):
    body = re.sub(r"<aside>.*?</aside>", "", slide_html, flags=re.S)
    body = re.sub(r'<p style="position:absolute[^>]*>.*?</p>', "", body, flags=re.S)  # footer
    return len(TEXT_RE.sub(" ", body).split())


def wrap_lines(text, size, width=1500, char=0.48):
    """Greedy estimate of how a title wraps (average bold glyph ~0.48, measured on IBM Plex Sans 700 x font size)."""
    per_line, lines, cur = int(width / (size * char)), [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > per_line:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + [cur]


def lint(content_path, out_dir):
    deck = json.load(open(content_path, encoding="utf-8"))
    issues = []
    prev = None
    for s in deck["slides"]:
        sid, lay = s["id"], s["layout"]
        path = os.path.join(out_dir, "project", "slides", sid + ".html")
        h = open(path, encoding="utf-8").read()
        for px in re.findall(r"font-size:(\d+)px", h):
            if int(px) < 24:
                issues.append(("ERROR", sid, f"font-size {px}px < 24px floor"))
        if "box-shadow" in h or "gradient" in h:
            issues.append(("ERROR", sid, "shadow/gradient: Swiss rule is hairlines and whitespace"))
        heroes = len(re.findall(r"font-size:(?:9[6-9]|[1-9]\d\d)px[^>]*>[^<]*\d", h))
        if heroes > 1:
            issues.append(("ERROR", sid, f"{heroes} hero numbers; one per slide (split it)"))
        if lay == prev and lay != "statement":
            issues.append(("ERROR", sid, f"same layout '{lay}' as the previous slide"))
        prev = lay
        words, budget = visible_words(h), WORD_BUDGET.get(lay, 40)
        if words > budget:
            issues.append(("WARN", sid, f"{words} words on slide > {budget} (glance test)"))
        title = s.get("title", "")
        if lay != "statement" and (len(title.split()) < 4 or title.endswith(":")):
            issues.append(("WARN", sid, "title reads like a label; write the claim as a sentence"))
        lines = wrap_lines(title, 96 if lay == "statement" else 64)
        if len(lines) > 1 and len(lines[-1].split()) == 1:
            issues.append(("WARN", sid, f"title widow: '{lines[-1]}' alone on the last line; rephrase"))
        if len(lines) > (3 if lay == "statement" else 2):
            issues.append(("WARN", sid, f"title runs {len(lines)} lines; cut it"))
        if re.search(r"[\w]'[\w]|\"", re.sub(r"<[^>]+>", "", h.split("<aside>")[0])):
            issues.append(("WARN", sid, "straight quote/apostrophe on the slide; use typographic ones"))
        if re.search(r"\[[^\]]+\]", h.split("<aside>")[0]):
            issues.append(("WARN", sid, "placeholder [..] left on the slide"))
        if not s.get("notes"):
            issues.append(("WARN", sid, "no speaker notes"))
    return issues
