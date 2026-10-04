"""Charts shared by the portal and the scorecards: a pie of the parts of a whole, and a small line over time.

Plain SVG written when the page is built: no script, no dependency, and no number the page computes for
itself beyond a share of a total it was given. Every mark carries a <title>, so hovering names it; the
legend beside a pie gives each part's amount and share as text, so color is never the only label.
"""
from html import escape

# One color per marketplace on every chart, by name. Checked as a set for color-blind separation on white;
# none is the green or red the pages use for change and missing data.
COLORS = {"ShopGoodwill": "#0054A4", "Amazon": "#eb6834", "eBay": "#1baf7a", "Other": "#8a8687"}

CHART_CSS = """
.piebox { display:flex; flex-wrap:wrap; align-items:center; gap:10px 24px; }
.pie { width:168px; height:168px; flex:none; }
.pie circle:hover { opacity:.82; }
.pie text { text-anchor:middle; fill:var(--ink); }
.pie .pie-total { font-size:5px; font-weight:700; }
.pie .pie-cap { font-size:2.5px; fill:var(--muted); }
.pielegend { list-style:none; margin:0; padding:0; flex:1 1 190px; font-size:14px; }
.pielegend li { display:grid; grid-template-columns:10px 1fr auto 40px; align-items:center; gap:8px; padding:6px 0;
  border-bottom:1px solid var(--line); }
.pielegend li:last-child { border-bottom:none; }
.pielegend i { width:10px; height:10px; border-radius:2px; }
.pielegend b { font-variant-numeric:tabular-nums; }
.pielegend em { font-style:normal; color:var(--muted); text-align:right; font-variant-numeric:tabular-nums; }
svg.line { display:block; width:100%; height:auto; margin-top:6px; overflow:visible; }
svg.line .grid { stroke:#e6e6e8; stroke-width:1; }
svg.line .path { fill:none; stroke:var(--primary); stroke-width:2; stroke-linejoin:round; stroke-linecap:round; }
svg.line .dot { fill:var(--primary); stroke:var(--card); stroke-width:2; }
svg.line .dot.hollow { fill:var(--card); stroke:var(--primary); }
svg.line a:hover .dot, svg.line a:focus .dot { stroke:var(--ink); }
svg.line text { font-size:11px; fill:var(--muted); font-variant-numeric:tabular-nums; }
@media print { .pie circle, .pielegend i { -webkit-print-color-adjust:exact; print-color-adjust:exact; } }
"""

GAP = 0.8  # the gap between two parts of a pie, in percent of the circle: the card shows through


def pie(slices, center, caption):
    """A pie of the parts of a whole (drawn as a ring, the total in the middle) and its legend.

    slices: (name, color, dollars). A part with no amount is left out, never drawn as zero. Returns "" when
    there is nothing to draw. The ring starts at 12 o'clock and runs clockwise, in the order given.
    """
    slices = [(name, color, value) for name, color, value in slices if value and value > 0]
    total = sum(value for _, _, value in slices)
    if not slices or total <= 0:
        return ""
    at, rings, rows = 0.0, [], []
    for name, color, value in slices:
        share = 100 * value / total
        dash = max(share - GAP, 0.2) if len(slices) > 1 else 100
        rings.append(f'<circle cx="21" cy="21" r="15.915" fill="none" stroke="{color}" stroke-width="8" '
                     f'stroke-dasharray="{dash:.2f} {100 - dash:.2f}" stroke-dashoffset="{(125 - at) % 100:.2f}">'
                     f'<title>{escape(name)}: ${value:,.2f} ({share:.1f}%)</title></circle>')
        rows.append(f'<li><i style="background:{color}"></i><span>{escape(name)}</span><b>${value:,.0f}</b>'
                    f'<em>{share:.0f}%</em></li>')
        at += share
    said = "; ".join(f"{name} ${value:,.0f}, {100 * value / total:.0f}%" for name, _, value in slices)
    return (f'<div class="piebox"><svg class="pie" viewBox="0 0 42 42" role="img" aria-label="{escape(said)}">'
            f'{"".join(rings)}<text x="21" y="21.5" class="pie-total">{escape(center)}</text>'
            f'<text x="21" y="25.5" class="pie-cap">{escape(caption)}</text></svg>'
            f'<ul class="pielegend">{"".join(rows)}</ul></div>')


def line(points, fmt):
    """One value over time, as a small line with a dot per period.

    points: (short label, value or None, hover text, link or "", hollow) in time order; a None value breaks
    the line (no data is never drawn as zero). `fmt` turns a value into the text of the two gridlines (the
    lowest and the highest value shown). Returns "" when no point has a value.
    """
    values = [p[1] for p in points if p[1] is not None]
    if not values:
        return ""
    W, H, LEFT, RIGHT, TOP, BOTTOM = 320, 150, 10, 10, 20, 24
    low, high = min(values), max(values)
    pad = (high - low) * 0.15 or abs(high) * 0.1 or 1
    lo, hi = (max(low - pad, 0) if low >= 0 else low - pad), high + pad

    def x(i):
        return LEFT + (W - LEFT - RIGHT) * (i / (len(points) - 1) if len(points) > 1 else 0.5)

    def y(v):
        return TOP + (H - TOP - BOTTOM) * (1 - (v - lo) / (hi - lo))

    grid = "".join(f'<line class="grid" x1="{LEFT}" x2="{W - RIGHT}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                   f'<text x="{LEFT}" y="{y(v) - 4:.1f}">{escape(fmt(v))}</text>'
                   for v in ([high, low] if high != low else [high]))
    path, pen = [], "M"
    for i, p in enumerate(points):
        if p[1] is None:
            pen = "M"
            continue
        path.append(f"{pen}{x(i):.1f} {y(p[1]):.1f}")
        pen = "L"
    dots = []
    for i, (_, value, said, href, hollow) in enumerate(points):
        if value is None:
            continue
        mark = (f'<circle cx="{x(i):.1f}" cy="{y(value):.1f}" r="11" fill="transparent"><title>{escape(said)}</title></circle>'
                f'<circle class="dot{" hollow" if hollow else ""}" cx="{x(i):.1f}" cy="{y(value):.1f}" r="4"/>')
        dots.append(f'<a href="{escape(href)}">{mark}</a>' if href else mark)
    every = max(1, -(-len(points) // 6))  # at most about six labels under the line; the last one always
    shown = {i for i in range(len(points)) if i % every == 0 and len(points) - 1 - i >= every} | {len(points) - 1}
    labels = "".join(
        f'<text x="{x(i):.1f}" y="{H - 6}" text-anchor="{"start" if i == 0 and len(points) > 1 else "end" if i == len(points) - 1 and len(points) > 1 else "middle"}">'
        f'{escape(points[i][0])}</text>' for i in sorted(shown))
    return (f'<svg class="line" viewBox="0 0 {W} {H}" role="img" aria-label="{escape("; ".join(p[2] for p in points))}">'
            f'{grid}<path class="path" d="{" ".join(path)}"/>{"".join(dots)}{labels}</svg>')
