"""The accessibility menu every page carries (through PAGE in reports/pulse.py): dark mode, text size,
highlighted links and a dyslexia-friendly font, kept in the viewer's browser (localStorage). No server
state, standard library only.

Text size scales the root font size, so `scalable()` turns the pages' px font sizes into rem as the shell
renders them: identical at 100%, and every page follows without its own CSS changing. SVG chart text
keeps px, because it is drawn in the chart's own units. Dark mode swaps the palette tokens from
reports/pulse.py and fixes the few rules that hard-code white; print always uses the light palette.
"""
import re


def scalable(css):
    """px font sizes become rem (16px = 1rem) outside SVG rules, so the text-size setting reaches them."""
    def rule(m):
        if re.search(r"\bsvg\b|\.pie\b", m[1]):
            return m[0]
        body = re.sub(r"(font-size:\s*|font:\s*)(\d+(?:\.\d+)?)px",
                      lambda d: f"{d[1]}{float(d[2]) / 16:g}rem", m[2])
        return f"{m[1]}{{{body}}}"
    return re.sub(r"([^{}]*)\{([^{}]*)\}", rule, css)


CSS = """
/* ---- Accessibility menu (reports/a11y.py) ---- */
html { font-size:calc(100% * var(--a11y-font-scale, 1)); }
@media print { html { font-size:100%; } .a11y-menu { display:none !important; } }

/* Dark mode: the palette's tokens, then the rules that hard-code white or a light tint. Screen only. */
@media screen {
  body.dark-mode { --primary:#8ab8ec; --ink:#ecebeb; --bg:#141518; --card:#1e2024; --down:#ff7d90;
    --muted:#aeaaab; --line:#3b3e44; --nodata:#26292e; --shadow:0 1px 2px rgba(0,0,0,.5);
    --lift:0 10px 26px rgba(0,0,0,.5); color-scheme:dark; }
  /* A fill under white text turns light in dark mode, so its text turns dark. */
  body.dark-mode :is(.btn:not(.quiet), .pill.ok, .pill.missing, .pill.stale, .pill.unknown, .chg.up, .chg.down,
    .chip[aria-pressed="true"], .pick[aria-pressed="true"], .info:hover, .info:focus-visible, .hub-card .band) {
    color:var(--bg); }
  body.dark-mode .btn:not(.quiet):hover { background:#b3d1f3; }
  body.dark-mode .btn.quiet:hover { background:#24364b; }
  body.dark-mode .topbar { background:#0054A4; } /* the brand bar keeps its blue under white text */
  body.dark-mode .datalabel { color:#231F20; }
  body.dark-mode .hub-card { border-color:#4a4e55; }
  body.dark-mode .hub-card .flagged { background:var(--bg); }
  body.dark-mode .card tbody > tr:hover > td:not(.nodata),
  body.dark-mode table.lib tbody tr[data-find]:hover td,
  body.dark-mode .pielegend li:hover { background-color:var(--nodata); }
  body.dark-mode .tick { border-top-color:var(--line); }
  body.dark-mode svg.line .grid { stroke:var(--line); }
  /* ShopGoodwill's chart blue is too dark on a dark card (about 2:1): a lighter tint of it. */
  body.dark-mode [stroke="#0054A4"] { stroke:#4a90d9; }
  body.dark-mode [style*="#0054A4"] { background:#4a90d9 !important; }
}

/* Highlight links: a viewer's preference, so it overrides page styles on purpose. */
body.highlight-links a, body.highlight-links button {
  text-decoration:underline !important; text-decoration-thickness:.15em !important;
  text-underline-offset:.2em !important; }
/* Two rings, ink outside and card inside, so the focus shows on any background, the blue bar included. */
body.highlight-links a:focus-visible, body.highlight-links button:focus-visible {
  outline:3px solid var(--ink) !important; outline-offset:2px !important; box-shadow:0 0 0 5px var(--card) !important; }

/* Dyslexia-friendly font. OpenDyslexic and Atkinson Hyperlegible apply only if installed; code and charts keep theirs. */
body.dyslexia-font,
body.dyslexia-font :not(code, kbd, pre, samp, svg, svg *, [aria-hidden="true"], [aria-hidden="true"] *) {
  font-family:"OpenDyslexic","Atkinson Hyperlegible","Comic Sans MS","Comic Neue","Chalkboard SE",sans-serif !important; }

/* The menu: a round button in the brand blue, bottom right, opening a card upward. */
.a11y-menu { position:fixed; right:max(16px, env(safe-area-inset-right)); bottom:max(16px, env(safe-area-inset-bottom));
  z-index:1000; }
.a11y-menu[hidden], .a11y-menu [hidden] { display:none !important; }
.a11y-trigger { display:grid; place-items:center; width:48px; height:48px; padding:0; border:0; border-radius:50%;
  background:var(--primary); color:var(--card); cursor:pointer; box-shadow:0 0 0 2px var(--card), var(--lift);
  transition:transform var(--t-hover) var(--ease-out); }
.a11y-trigger:hover { transform:translateY(-2px); }
.a11y-trigger:active { transform:scale(.96); }
.a11y-trigger:focus-visible { outline:2px solid var(--ink); outline-offset:4px; }
.a11y-trigger svg { width:28px; height:28px; fill:currentColor; }
.a11y-panel { position:absolute; right:0; bottom:calc(100% + 10px); width:min(20rem, calc(100vw - 32px));
  max-height:calc(100vh - 96px); max-height:calc(100dvh - 96px); overflow-y:auto; padding:2px 16px 14px;
  background:var(--card); color:var(--ink); border:1px solid var(--line); border-radius:var(--radius);
  box-shadow:0 8px 28px rgba(35,31,32,.22); font-size:15px; line-height:1.4;
  transform-origin:bottom right; animation:a11y-in var(--t-reveal) var(--ease-out); }
@keyframes a11y-in { from { opacity:0; transform:translateY(4px) scale(.98); } }
.a11y-head { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 0 8px;
  border-bottom:2px solid var(--primary); }
.a11y-head h2 { margin:0; font-size:13px; color:var(--primary); text-transform:uppercase; letter-spacing:.05em; }
.a11y-close { min-width:32px; }
.a11y-row { display:flex; align-items:center; justify-content:space-between; gap:12px; width:100%; min-height:48px;
  padding:6px 0; border:0; border-bottom:1px solid var(--line); background:none; color:inherit; font:inherit;
  text-align:left; cursor:pointer; }
.a11y-row:focus-visible, .a11y-menu .btn:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }
/* The switch: off is a grey ring, on is filled blue with the knob at the end. */
.a11y-track { position:relative; flex:none; width:40px; height:22px; border:2px solid var(--muted); border-radius:999px;
  background:var(--card); transition:background-color var(--t-hover) var(--ease-out), border-color var(--t-hover) var(--ease-out); }
.a11y-track::before { content:""; position:absolute; top:3px; left:3px; width:12px; height:12px; border-radius:50%;
  background:var(--muted); transition:transform var(--t-hover) var(--ease-out), background-color var(--t-hover) var(--ease-out); }
.a11y-switch[aria-checked="true"] .a11y-track { background:var(--primary); border-color:var(--primary); }
.a11y-switch[aria-checked="true"] .a11y-track::before { transform:translateX(18px); background:var(--card); }
.a11y-size { padding:10px 0 12px; border-bottom:1px solid var(--line); }
.a11y-steps { display:flex; align-items:center; gap:8px; margin-top:6px; }
.a11y-steps output { min-width:4.5ch; text-align:center; font-weight:700; font-variant-numeric:tabular-nums; }
.a11y-menu .btn[aria-disabled="true"] { opacity:.5; cursor:default; transform:none; }
.a11y-foot { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:8px; padding-top:12px;
  font-size:13px; color:var(--muted); }
.a11y-sr { position:absolute !important; width:1px; height:1px; margin:-1px; padding:0; border:0; overflow:hidden;
  clip-path:inset(50%); white-space:nowrap; }
@media (forced-colors: active) {
  .a11y-track, .a11y-track::before { forced-color-adjust:none; border-color:ButtonText; background:ButtonFace; }
  .a11y-track::before { background:ButtonText; }
  .a11y-switch[aria-checked="true"] .a11y-track { background:Highlight; border-color:Highlight; }
  .a11y-switch[aria-checked="true"] .a11y-track::before { background:HighlightText; }
}
"""


def _switch(key, label):
    return (f'<button type="button" class="a11y-row a11y-switch" role="switch" aria-checked="false" '
            f'data-a11y-toggle="{key}"><span>{label}</span><span class="a11y-track" aria-hidden="true"></span></button>')


# Hidden until the script wires it up, so a page without JavaScript shows no dead button.
MENU = f"""<div class="a11y-menu" data-a11y-menu hidden>
<button type="button" class="a11y-trigger" data-a11y-trigger aria-expanded="false" aria-controls="a11y-panel">
<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a2 2 0 1 1 0 4 2 2 0 0 1 0-4zm9 7h-6v13h-2v-6h-2v6H9V9H3V7h18v2z"/></svg>
<span class="a11y-sr">Accessibility settings</span></button>
<div class="a11y-panel" id="a11y-panel" data-a11y-panel role="dialog" aria-labelledby="a11y-title" hidden>
<div class="a11y-head"><h2 id="a11y-title">Accessibility settings</h2>
<button type="button" class="btn quiet small a11y-close" data-a11y-close><span aria-hidden="true">&times;</span><span class="a11y-sr">Close</span></button></div>
{_switch("darkMode", "Dark mode")}
<div class="a11y-size" role="group" aria-labelledby="a11y-size-label"><span id="a11y-size-label">Text size</span>
<div class="a11y-steps"><button type="button" class="btn quiet" data-a11y-font="down">Smaller</button>
<output data-a11y-font-value aria-live="polite">100%</output>
<button type="button" class="btn quiet" data-a11y-font="up">Larger</button></div></div>
{_switch("highlightLinks", "Highlight links")}
{_switch("dyslexiaFont", "Dyslexia-friendly font")}
<div class="a11y-foot"><span>Saved in this browser only</span>
<button type="button" class="btn quiet small" data-a11y-reset>Reset all</button></div>
<p class="a11y-sr" role="status" data-a11y-status></p>
</div>
</div>"""

# First thing in <body>, so saved settings apply before the first paint (no flash of the wrong theme).
SCRIPT = r"""<script>
/* Accessibility menu (reports/a11y.py). Settings live in this browser only, under "a11y-prefs". */
(() => {
  'use strict';
  const STORAGE_KEY = 'a11y-prefs';
  const FONT_STEPS = [80, 90, 100, 110, 125, 150, 175, 200]; // percent of the page's base size
  // theme null = follow the operating system (prefers-color-scheme) until the viewer picks one.
  const DEFAULTS = { theme: null, fontSize: 100, highlightLinks: false, dyslexiaFont: false };
  const systemDark = window.matchMedia('(prefers-color-scheme: dark)');
  let prefs = load();
  let syncMenu = () => {}; // replaced once the menu exists

  function load() {
    let saved = {};
    try {
      saved = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch {
      // Storage blocked (private mode, cookies off) or corrupt: defaults.
    }
    // Stored values are untrusted input: keep only what we recognise.
    return {
      theme: saved.theme === 'dark' || saved.theme === 'light' ? saved.theme : DEFAULTS.theme,
      fontSize: FONT_STEPS.includes(saved.fontSize) ? saved.fontSize : DEFAULTS.fontSize,
      highlightLinks: saved.highlightLinks === true,
      dyslexiaFont: saved.dyslexiaFont === true,
    };
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch {
      // Not saved, but the setting still applies to this page view.
    }
  }

  const isDark = () => (prefs.theme ? prefs.theme === 'dark' : systemDark.matches);

  function apply() {
    const root = document.documentElement;
    if (prefs.fontSize === 100) root.style.removeProperty('--a11y-font-scale');
    else root.style.setProperty('--a11y-font-scale', String(prefs.fontSize / 100));
    if (!document.body) return;
    document.body.classList.toggle('dark-mode', isDark());
    document.body.classList.toggle('highlight-links', prefs.highlightLinks);
    document.body.classList.toggle('dyslexia-font', prefs.dyslexiaFont);
  }

  function update() {
    apply();
    syncMenu();
  }

  function initMenu() {
    apply();
    const menu = document.querySelector('[data-a11y-menu]');
    if (!menu) return;
    const trigger = menu.querySelector('[data-a11y-trigger]');
    const panel = menu.querySelector('[data-a11y-panel]');
    const switches = menu.querySelectorAll('[data-a11y-toggle]');
    const fontDown = menu.querySelector('[data-a11y-font="down"]');
    const fontUp = menu.querySelector('[data-a11y-font="up"]');
    const fontValue = menu.querySelector('[data-a11y-font-value]');
    const status = menu.querySelector('[data-a11y-status]');

    syncMenu = () => {
      for (const sw of switches) {
        const key = sw.dataset.a11yToggle;
        sw.setAttribute('aria-checked', String(key === 'darkMode' ? isDark() : prefs[key]));
      }
      const step = FONT_STEPS.indexOf(prefs.fontSize);
      fontValue.textContent = `${prefs.fontSize}%`;
      // aria-disabled, not disabled: disabling the focused button would drop focus to <body>.
      fontDown.setAttribute('aria-disabled', String(step === 0));
      fontUp.setAttribute('aria-disabled', String(step === FONT_STEPS.length - 1));
    };

    const isOpen = () => !panel.hidden;

    function open() {
      panel.hidden = false;
      trigger.setAttribute('aria-expanded', 'true');
      panel.querySelector('[data-a11y-toggle], [data-a11y-font]')?.focus();
    }

    function close({ restoreFocus }) {
      if (!isOpen()) return;
      panel.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
      if (restoreFocus) trigger.focus();
    }

    function commit() {
      save();
      update();
    }

    function announce(message) {
      status.textContent = '';
      // Set after a tick so screen readers repeat an identical message.
      setTimeout(() => { status.textContent = message; }, 100);
    }

    function stepFont(direction) {
      const next = FONT_STEPS[FONT_STEPS.indexOf(prefs.fontSize) + direction];
      if (next === undefined) return; // already at the smallest or largest step
      prefs.fontSize = next;
      commit();
    }

    trigger.addEventListener('click', () => (isOpen() ? close({ restoreFocus: true }) : open()));
    menu.querySelector('[data-a11y-close]').addEventListener('click', () => close({ restoreFocus: true }));
    for (const sw of switches) {
      sw.addEventListener('click', () => {
        const key = sw.dataset.a11yToggle;
        if (key === 'darkMode') prefs.theme = isDark() ? 'light' : 'dark';
        else prefs[key] = !prefs[key];
        commit();
      });
    }
    fontDown.addEventListener('click', () => stepFont(-1));
    fontUp.addEventListener('click', () => stepFont(1));
    menu.querySelector('[data-a11y-reset]').addEventListener('click', () => {
      prefs = { ...DEFAULTS };
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch {
        // Nothing was stored.
      }
      update();
      announce('Settings reset to defaults.');
    });

    // Escape closes from anywhere. Focus returns to the trigger unless it is elsewhere on the page.
    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape' || !isOpen()) return;
      const focused = document.activeElement;
      close({ restoreFocus: !focused || focused === document.body || menu.contains(focused) });
    });
    // Light dismiss, like a native popover: a click outside closes without moving focus...
    document.addEventListener('click', (event) => {
      if (isOpen() && !menu.contains(event.target)) close({ restoreFocus: false });
    });
    // ...and so does tabbing out. relatedTarget is null when Safari clicks a button inside the panel.
    menu.addEventListener('focusout', (event) => {
      if (event.relatedTarget && !menu.contains(event.relatedTarget)) close({ restoreFocus: false });
    });

    syncMenu();
    menu.hidden = false;
  }

  // Another tab changed the settings, or the OS theme changed while the viewer hasn't picked one.
  window.addEventListener('storage', (event) => {
    if (event.key === STORAGE_KEY || event.key === null) {
      prefs = load();
      update();
    }
  });
  systemDark.addEventListener('change', () => {
    if (!prefs.theme) update();
  });

  apply();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initMenu);
  else initMenu();
})();
</script>"""
