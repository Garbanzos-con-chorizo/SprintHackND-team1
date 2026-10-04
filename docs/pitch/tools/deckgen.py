"""Render a deck content file (JSON) into the Slides artifact's files.

Output: <out>/project/deck.json and <out>/project/slides/<id>.html, ready to
publish to a Slides artifact with root=<out>. Layouts and themes follow
.claude/skills/slides (Swiss grid: hairlines, one anchor color, no shadows).
Schema: docs/pitch/tools/README.md.
"""
import html
import json
import os
import re
from datetime import datetime, timezone

THEMES = {
    "swiss": {"ink": "#231F20", "paper": "#FFFFFF", "alt": "#F4F4F2", "anchor": "#0054A4",
              "warn": "#B25000", "body": "#4A4647", "muted": "#5C5859", "line": "#D3D2D2",
              "head": "IBM Plex Sans", "text": "IBM Plex Sans",
              "faces": {"ibm-plex-sans": ("IBM Plex Sans", "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&display=swap")}},
    "keynote": {"ink": "#F5F5F7", "paper": "#111113", "alt": "#1C1C1E", "anchor": "#2997FF",
                "warn": "#FF9F0A", "body": "#C7C7CC", "muted": "#98989D", "line": "#3A3A3C",
                "head": "DM Sans", "text": "DM Sans",
                "faces": {"dm-sans": ("DM Sans", "https://fonts.googleapis.com/css2?family=DM+Sans:wght@400..700&display=swap")}},
    "ledger": {"ink": "#1B1B1B", "paper": "#FAF8F3", "alt": "#F1EEE6", "anchor": "#0B5D3B",
               "warn": "#A4361B", "body": "#45423C", "muted": "#5E5A52", "line": "#CFC9BB",
               "head": "Source Serif 4", "text": "IBM Plex Sans",
               "faces": {"source-serif-4": ("Source Serif 4", "https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&display=swap"),
                         "ibm-plex-sans": ("IBM Plex Sans", "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&display=swap")}},
}

PAD = "padding:128px 128px 160px"
NUM = "font-variant-numeric:tabular-nums"


def typo(s):
    """Typographic polish: curly apostrophes and quotes, en dash in number ranges, true minus."""
    s = re.sub(r"(\w)'(\w)", r"\1’\2", str(s))
    s = re.sub(r"(^|[\s(])'", r"\1‘", s).replace("'", "’")
    if "<" not in s:
        s = re.sub(r'(^|[\s(])"', r"\1“", s).replace('"', "”")
    s = re.sub(r"(\d)-(\d)", r"\1–\2", s)
    return re.sub(r"(^|\s)-(\$?\d)", r"\1−\2", s)


def esc(s):
    return typo(html.escape(str(s), quote=False))


class Renderer:
    def __init__(self, deck):
        self.deck = deck
        self.t = THEMES[deck.get("theme", "swiss")]
        t = self.t
        self.ff_head = f"font-family:'{t['head']}', Georgia, serif" if t["head"] != t["text"] else f"font-family:'{t['head']}', Arial, sans-serif"
        self.ff_text = f"font-family:'{t['text']}', Arial, sans-serif"

    # -- pieces ---------------------------------------------------------
    def eyebrow(self, s, color=None):
        return (f'<p style="font-size:24px;font-weight:600;letter-spacing:3px;text-transform:uppercase;'
                f'color:{color or self.t["anchor"]}">{esc(s)}</p>') if s else ""

    def title(self, s, size=64, color=None):
        return (f'<h2 style="{self.ff_head};font-size:{size}px;font-weight:700;line-height:1.1;'
                f'letter-spacing:-1px;color:{color or self.t["ink"]};width:1500px">{esc(s)}</h2>')

    def head(self, s):
        return self.eyebrow(s.get("eyebrow")) + self.title(s["title"])

    def body(self, inner):
        """Body fills the space under the title and centers in it, so no half-empty slide."""
        return f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:32px">{inner}</div>'

    def footer(self, i, n, color=None):
        text = f'{i} / {n} · {self.deck.get("footer", "")}'.rstrip(" ·")
        return (f'<p style="position:absolute;left:128px;bottom:64px;width:1664px;font-size:24px;'
                f'color:{color or self.t["muted"]}">{esc(text)}</p>')

    def p(self, s, size=32, color=None, extra=""):
        return f'<p style="font-size:{size}px;line-height:1.4;color:{color or self.t["body"]}{extra}">{s}</p>'

    # -- layouts --------------------------------------------------------
    def statement(self, s):
        inner = self.eyebrow(s.get("eyebrow")) + self.title(s["title"], 96) + (self.p(esc(s["sub"]), 40) if s.get("sub") else "")
        return inner, "display:flex;flex-direction:column;justify-content:center;gap:48px"

    def quotes(self, s):
        t = self.t
        cols = "".join(
            f'<div style="flex:1;display:flex;flex-direction:column;gap:16px;border-top:4px solid {t["anchor"]};padding:24px 0 0 0">'
            f'<p style="font-size:24px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:{t["anchor"]}">{esc(q["label"])}</p>'
            f'<p style="{self.ff_head};font-size:30px;line-height:1.4;color:{t["ink"]}">“{typo(q["text"])}”</p></div>'
            for q in s["quotes"])
        attr = self.p(esc(s.get("attribution", "")), 24, t["muted"])
        return self.head(s) + self.body(f'<div style="display:flex;gap:56px">{cols}</div>' + attr), \
            "display:flex;flex-direction:column;gap:48px"

    def hero(self, s):
        t = self.t
        color = t["warn"] if s.get("tone") == "warn" else t["anchor"]
        num = (f'<p style="{self.ff_head};font-size:240px;font-weight:700;line-height:1;letter-spacing:-6px;{NUM};'
               f'color:{color}">{esc(s["number"])}</p>')
        cap = self.p(typo(s.get("caption", "")), 40, t["ink"], ";width:1400px")
        return self.head(s) + self.body(num + cap), "display:flex;flex-direction:column;gap:48px"

    def ledger(self, s):
        t = self.t
        rows = []
        for r in s["rows"]:
            c = t["warn"] if r.get("warn") else t["ink"]
            rows.append(
                f'<div style="display:flex;gap:32px;align-items:center;border-top:2px solid {t["line"]};padding:24px 0 24px 0">'
                f'<div style="flex:1;display:flex;flex-direction:column;gap:8px">'
                f'<p style="font-size:24px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:{c}">{esc(r.get("status", ""))}</p>'
                f'<p style="font-size:36px;line-height:1.3;color:{t["ink"]}">{typo(r["label"])}</p></div>'
                f'<p style="width:420px;text-align:right;{self.ff_head};font-size:64px;font-weight:700;{NUM};color:{c}">{esc(r["amount"])}</p></div>')
        rows.append(f'<hr style="border-top:2px solid {t["line"]};width:1664px">')
        return self.head(s) + self.body(f'<div style="display:flex;flex-direction:column">{"".join(rows)}</div>'), \
            "display:flex;flex-direction:column;gap:48px"

    def columns(self, s):
        t = self.t
        cols = "".join(
            f'<div style="flex:1;display:flex;flex-direction:column;gap:16px;border-top:4px solid {t["ink"]};padding:24px 0 0 0">'
            f'<p style="font-size:24px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:{t["anchor"]}">{esc(c.get("label", ""))}</p>'
            f'<h3 style="{self.ff_head};font-size:44px;font-weight:700;color:{t["ink"]}">{esc(c["head"])}</h3>'
            + self.p(typo(c["text"]), 36) + "</div>" for c in s["cols"])
        return self.head(s) + self.body(f'<div style="display:flex;gap:56px">{cols}</div>'), \
            "display:flex;flex-direction:column;gap:48px"

    def table(self, s):
        t = self.t
        w = s.get("widths", [40, 60])
        head = "".join(f'<th style="width:{w[i]}%">{esc(h)}</th>' for i, h in enumerate(s["head"]))
        body = "".join("<tr>" + "".join(f"<td>{typo(c)}</td>" for c in r) + "</tr>" for r in s["rows"])
        tbl = (f'<table style="font-size:28px;color:{t["ink"]};padding:16px 20px">'
               f'<tr style="background:{t["alt"]}">{head}</tr>{body}</table>')
        return self.head(s) + self.body(tbl), "display:flex;flex-direction:column;gap:48px"

    # -- slide ----------------------------------------------------------
    def slide(self, s, i, n):
        t = self.t
        inv = s.get("invert", False)
        if inv:  # statement on the anchor color, light text
            saved = dict(t)
            t.update(ink=saved["paper"], body=saved["paper"], muted=saved["paper"], anchor=saved["paper"])
        inner, layout = getattr(self, s["layout"])(s)
        bg = saved["anchor"] if inv else (t["alt"] if s.get("alt") else t["paper"])
        out = (f'<section id="{s["id"]}" data-transition="fade" style="background:{bg};color:{t["ink"]};'
               f'{self.ff_text};{PAD};{layout}">\n{inner}\n{self.footer(i, n)}\n'
               f'<aside>{esc(s.get("notes", ""))}</aside>\n</section>\n')
        if inv:
            t.update(saved)
        return out


def build(content_path, out_dir):
    deck = json.load(open(content_path, encoding="utf-8"))
    r = Renderer(deck)
    proj = os.path.join(out_dir, "project")
    os.makedirs(os.path.join(proj, "slides"), exist_ok=True)
    slides = deck["slides"]
    for i, s in enumerate(slides, 1):
        with open(os.path.join(proj, "slides", s["id"] + ".html"), "w", encoding="utf-8") as f:
            f.write(r.slide(s, i, len(slides)))
    index = {"v": 4, "createdOnFiles": {"v": 1, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
             "lists": "css", "title": deck["title"], "order": [s["id"] for s in slides],
             "sections": {f"s{k}": {"description": sec["description"], "start": sec["start"]}
                          for k, sec in enumerate(deck.get("sections") or [{"description": deck["title"], "start": slides[0]["id"]}], 1)},
             "faces": {k: {"family": fam, "href": href} for k, (fam, href) in r.t["faces"].items()},
             "designSystems": []}
    with open(os.path.join(proj, "deck.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1)
    return [s["id"] for s in slides]
