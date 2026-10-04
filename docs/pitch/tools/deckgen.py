"""Render a deck content file (JSON) into the Slides artifact's files.

Output: <out>/project/deck.json and <out>/project/slides/<id>.html, ready to
publish to a Slides artifact with root=<out> (and to bundle offline with
export_html.py). Design system: .claude/skills/slides/reference/github-skills-deep-dive.md
- serif = voice (titles), sans = substance (body), mono = metadata (chrome, labels)
- two surfaces (paper / navy), one accent used only on rules, markers and *emphasis*
- chrome bar on every slide, flat + hairline, no shadows, no gradients, system fonts only
Schema: docs/pitch/tools/README.md.
"""
import html
import json
import os
import re
from datetime import datetime, timezone

SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "Consolas, Menlo, 'Courier New', monospace"

SURFACES = {
    "light": {"bg": "#F7F5F0", "ink": "#1A2030", "body": "#3E4452", "muted": "#5F6673",
              "line": "#CFCAC0", "accent": "#0054A4", "warn": "#9A4A00"},
    "dark": {"bg": "#0B2545", "ink": "#EEF0F3", "body": "#C9D2DE", "muted": "#9FB0C7",
             "line": "#2A4670", "accent": "#8FB8E8", "warn": "#F2B36B"},
    "accent": {"bg": "#0054A4", "ink": "#FFFFFF", "body": "#E3ECF7", "muted": "#C9DAEE",
               "line": "#3B7BC2", "accent": "#FFFFFF", "warn": "#FFFFFF"},
}
TOP = 176  # content starts under the chrome bar


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
        self.c = SURFACES["light"]

    # -- type ladder ----------------------------------------------------
    def emph(self, s):
        """*phrase* in a title -> italic in the accent color (the one signature move)."""
        return re.sub(r"\*(.+?)\*", lambda m: f'<i><span style="color:{self.c["accent"]}">{m.group(1)}</span></i>', esc(s))

    def title(self, s, size=72, width=1500):
        return (f'<h2 style="font-family:{SERIF};font-size:{size}px;font-weight:400;line-height:1.12;'
                f'color:{self.c["ink"]};width:{width}px">{self.emph(s)}</h2>')

    def label(self, s, color=None):
        return f'<p style="font-family:{MONO};font-size:24px;color:{color or self.c["accent"]}">{esc(s)}</p>' if s else ""

    def p(self, s, size=32, color=None, extra=""):
        return (f'<p style="font-family:{SANS};font-size:{size}px;line-height:1.45;'
                f'color:{color or self.c["body"]}{extra}">{typo(s)}</p>')

    def body(self, inner):
        """Fill the space under the title and center the content in it (no gap, no crowding)."""
        return f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:32px">{inner}</div>'

    def marker(self, color=None):
        return f'<div style="width:14px;height:14px;background:{color or self.c["accent"]};flex:none"></div>'

    def chrome(self, i, n):
        c = self.c
        left = self.deck.get("chrome", "")
        return (f'<p style="position:absolute;left:128px;top:64px;width:1200px;font-family:{MONO};font-size:24px;color:{c["muted"]}">{esc(left)}</p>'
                f'<p style="position:absolute;right:128px;top:64px;width:300px;text-align:right;font-family:{MONO};font-size:24px;color:{c["muted"]}">{i:02d} / {n:02d}</p>'
                f'<hr style="position:absolute;left:128px;top:112px;width:1664px;border-top:1px solid {c["line"]}">')

    # -- layouts --------------------------------------------------------
    def statement(self, s):
        sub = self.p(s["sub"], 40, self.c["body"]) if s.get("sub") else ""
        return (self.label(s.get("label")) + self.title(s["title"], 120, 1600) + sub,
                "justify-content:center;gap:48px")

    def quotes(self, s):
        c = self.c
        cols = "".join(
            f'<div style="flex:1;display:flex;flex-direction:column;gap:20px;border-top:1px solid {c["line"]};padding:28px 0 0 0">'
            + self.label(q["label"]) +
            f'<p style="font-family:{SERIF};font-size:32px;line-height:1.45;color:{c["ink"]}">“{typo(q["text"])}”</p></div>'
            for q in s["quotes"])
        attr = self.label(s.get("attribution"), c["muted"])
        return (self.title(s["title"]) + self.body(f'<div style="display:flex;gap:64px">{cols}</div>' + attr),
                "gap:48px")

    def system(self, s):
        """Inputs -> the program -> outputs, drawn with hairlines (a diagram, not bullets)."""
        c = self.c

        def column(head, items):
            rows = "".join(f'<div style="display:flex;gap:20px;align-items:center;border-top:1px solid {c["line"]};padding:20px 0 20px 0">'
                           + self.marker() + self.p(x, 32, c["ink"]) + "</div>" for x in items)
            return (f'<div style="flex:1;display:flex;flex-direction:column;gap:8px">{self.label(head)}'
                    f'<div style="display:flex;flex-direction:column">{rows}</div></div>')

        core = s["core"]
        mid = (f'<div style="width:440px;flex:none;display:flex;flex-direction:column;gap:16px;border:2px solid {c["accent"]};padding:40px">'
               f'{self.label(core.get("label", ""))}<h3 style="font-family:{SERIF};font-size:48px;font-weight:400;color:{c["ink"]}">{esc(core["head"])}</h3>'
               + "".join(self.p(x, 28) for x in core.get("lines", [])) + "</div>")
        arrow = f'<p style="font-family:{SANS};font-size:56px;color:{c["accent"]}">→</p>'
        return (self.title(s["title"]) +
                self.body(f'<div style="display:flex;gap:40px;align-items:center">{column(s["in_label"], s["inputs"])}{arrow}{mid}{arrow}{column(s["out_label"], s["outputs"])}</div>'),
                "gap:48px")

    def timeline(self, s):
        """Linear steps: square node on a 1 px axis, label under it."""
        c = self.c
        steps, last = [], len(s["steps"]) - 1
        for k, st in enumerate(s["steps"]):
            node = c["warn"] if st.get("flag") else c["accent"]
            axis = c["line"] if k < last else c["bg"]
            steps.append(
                f'<div style="flex:1;display:flex;flex-direction:column;gap:28px">'
                f'<div style="display:flex;align-items:center"><div style="width:20px;height:20px;background:{node};flex:none"></div>'
                f'<div style="flex:1;height:1px;background:{axis}"></div></div>'
                f'<h3 style="font-family:{SERIF};font-size:40px;font-weight:400;color:{c["ink"]};width:340px">{esc(st["head"])}</h3>'
                + (self.p(st["text"], 28, extra=";width:340px") if st.get("text") else "") + "</div>")
        return (self.title(s["title"]) + self.body(f'<div style="display:flex">{"".join(steps)}</div>'),
                "gap:48px")

    def duo(self, s):
        """Two halves split by one vertical hairline."""
        c = self.c

        def half(side):
            mark = (lambda: self.marker()) if side.get("marked") else \
                (lambda: f'<div style="width:14px;height:14px;border:2px solid {c["muted"]};flex:none"></div>')
            rows = "".join(f'<div style="display:flex;gap:20px;align-items:center;border-top:1px solid {c["line"]};padding:18px 0 18px 0">'
                           + mark() + self.p(x, 32, c["ink"]) + "</div>" for x in side["items"])
            return (f'<div style="flex:1;display:flex;flex-direction:column;gap:12px">{self.label(side["label"], c.get(side.get("color", "accent")))}'
                    f'<div style="display:flex;flex-direction:column">{rows}</div></div>')

        return (self.title(s["title"]) +
                self.body(f'<div style="display:flex;gap:72px">{half(s["left"])}<div style="width:1px;background:{c["line"]};flex:none"></div>{half(s["right"])}</div>'),
                "gap:48px")

    def points(self, s):
        c = self.c
        rows = "".join(f'<div style="display:flex;gap:32px;align-items:center;border-top:1px solid {c["line"]};padding:30px 0 30px 0">'
                       + self.marker() + f'<p style="font-family:{SERIF};font-size:44px;line-height:1.25;color:{c["ink"]}">{typo(x)}</p></div>'
                       for x in s["points"])
        return (self.title(s["title"]) + self.body(f'<div style="display:flex;flex-direction:column">{rows}</div>'),
                "gap:48px")

    def closing(self, s):
        """Left half in the accent color with the ask; right half the plain next steps."""
        a, l = SURFACES["accent"], SURFACES["light"]
        left = (f'<div style="display:flex;flex-direction:column;justify-content:center;gap:40px;background:{a["bg"]};padding:{TOP}px 96px 128px 128px">'
                f'<p style="font-family:{MONO};font-size:24px;color:{a["muted"]}">{esc(s.get("label", ""))}</p>'
                f'<h2 style="font-family:{SERIF};font-size:88px;font-weight:400;line-height:1.1;color:{a["ink"]}">{esc(s["title"])}</h2></div>')
        rows = "".join(f'<div style="display:flex;gap:24px;align-items:center;border-top:1px solid {l["line"]};padding:24px 0 24px 0">'
                       f'<div style="width:14px;height:14px;background:{l["accent"]};flex:none"></div>'
                       f'<p style="font-family:{SANS};font-size:34px;line-height:1.35;color:{l["ink"]}">{typo(x)}</p></div>' for x in s["then"])
        right = (f'<div style="display:flex;flex-direction:column;justify-content:center;gap:12px;background:{l["bg"]};padding:{TOP}px 128px 128px 96px">'
                 f'<p style="font-family:{MONO};font-size:24px;color:{l["accent"]}">{esc(s.get("then_label", ""))}</p>{rows}</div>')
        return left + right, "display:grid;grid-template-columns:1fr 1fr;padding:0"

    # -- slide ----------------------------------------------------------
    def slide(self, s, i, n):
        self.c = SURFACES[s.get("surface", "light")]
        inner, layout = getattr(self, s["layout"])(s)
        if "display:grid" in layout:  # full-bleed split layout: its own padding, no chrome across two surfaces
            box, chrome = layout, ""
        else:
            box, chrome = f"display:flex;flex-direction:column;padding:{TOP}px 128px 120px;{layout}", self.chrome(i, n)
        return (f'<section id="{s["id"]}" data-transition="fade" style="background:{self.c["bg"]};color:{self.c["ink"]};'
                f'font-family:{SANS};{box}">\n{inner}\n{chrome}\n'
                f'<aside>{esc(s.get("notes", ""))}</aside>\n</section>\n')


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
             "faces": {}, "designSystems": []}
    with open(os.path.join(proj, "deck.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1)
    return [s["id"] for s in slides]
