#!/usr/bin/env python3
"""Render the scenes in script.json to 1920x1080 slide PNGs.

Slides are plain HTML/CSS screenshotted with Playwright + Chromium.
Outputs: output/slides/<scene_id>.png (and the .html next to it for tweaking).

Usage:
    python render_slides.py [--script script.json] [--out output/slides]
"""
import argparse
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Dark-mode palette (validated categorical slots + chart chrome)
CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --surface: #1a1a19;
  --page: #0d0d0d;
  --ink: #ffffff;
  --ink-2: #c3c2b7;
  --muted: #898781;
  --grid: #2c2c2a;
  --baseline: #383835;
  --series-1: #3987e5;  /* blue  */
  --series-2: #199e70;  /* aqua  */
  --border: rgba(255,255,255,0.10);
}
html, body { width: 1920px; height: 1080px; }
body {
  background: var(--page);
  color: var(--ink);
  font-family: system-ui, -apple-system, "Segoe UI", "DejaVu Sans", sans-serif;
  display: flex;
}
.slide {
  background: var(--surface);
  margin: 40px; border-radius: 24px; border: 1px solid var(--border);
  flex: 1; padding: 70px 110px; display: flex; flex-direction: column;
  position: relative; overflow: hidden;
}
.slide::before {  /* subtle accent glow, top-right */
  content: ""; position: absolute; top: -300px; right: -300px;
  width: 700px; height: 700px; border-radius: 50%;
  background: radial-gradient(circle, rgba(57,135,229,0.12), transparent 70%);
}
.kicker { color: var(--series-1); font-size: 30px; font-weight: 700;
  letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 28px; }
h1.big { font-size: 150px; font-weight: 800; letter-spacing: -0.02em; }
h2.sub { font-size: 52px; font-weight: 400; color: var(--ink-2); margin-top: 30px; }
h1.head { font-size: 68px; font-weight: 800; letter-spacing: -0.01em; margin-bottom: 48px; }
.footer { position: absolute; bottom: 60px; left: 110px; right: 110px;
  color: var(--muted); font-size: 30px; }
ul.bullets { list-style: none; display: flex; flex-direction: column; gap: 42px;
  font-size: 46px; line-height: 1.35; color: var(--ink-2); max-width: 1550px; }
ul.bullets li { padding-left: 58px; position: relative; }
ul.bullets li::before { content: ""; position: absolute; left: 0; top: 0.52em;
  width: 22px; height: 22px; border-radius: 6px; background: var(--series-1);
  transform: translateY(-50%); }
.center { justify-content: center; }
/* pipeline layout */
.pipe { display: flex; flex-direction: column; gap: 22px; margin-top: 4px; }
.pipe .step { display: flex; align-items: center; gap: 32px; }
.pipe .n { width: 60px; height: 60px; border-radius: 50%; flex: none;
  background: var(--series-1); color: #fff; display: flex; align-items: center;
  justify-content: center; font-size: 32px; font-weight: 800; }
.pipe .box { background: var(--page); border: 1px solid var(--border);
  border-radius: 16px; padding: 18px 36px; flex: 1; }
.pipe .label { font-size: 36px; font-weight: 700; }
.pipe .detail { font-size: 30px; color: var(--muted); margin-top: 4px; }
/* charts */
.chart { display: flex; flex-direction: column; gap: 34px; margin-top: 20px; }
.row { display: flex; align-items: center; gap: 40px; }
.row .lab { width: 480px; flex: none; text-align: right; font-size: 38px;
  color: var(--ink-2); }
.row .track { flex: 1; height: 54px; position: relative; }
.row .bar { height: 100%; border-radius: 0 8px 8px 0; background: var(--muted);
  border-left: 3px solid var(--baseline); }
.row.hl .bar { background: var(--series-1); }
.row.hl .lab { color: var(--ink); font-weight: 700; }
.row .val { font-size: 38px; font-variant-numeric: tabular-nums; color: var(--ink-2);
  position: absolute; left: 100%; top: 50%; transform: translate(20px, -50%); }
.row.hl .val { color: var(--ink); font-weight: 700; }
.note { margin-top: 44px; color: var(--muted); font-size: 32px; }
.legend { display: flex; gap: 56px; margin-bottom: 36px; font-size: 34px;
  color: var(--ink-2); }
.legend .item { display: flex; align-items: center; gap: 18px; }
.legend .chip { width: 28px; height: 28px; border-radius: 8px; }
.group { margin-bottom: 30px; }
.group .glab { font-size: 34px; font-weight: 700; margin-bottom: 12px; }
.group .row { margin-bottom: 8px; }
.group .track { height: 40px; }
.group .val { font-size: 32px; }
.s1 { background: var(--series-1); }
.s2 { background: var(--series-2); }
.row .bar.s1 { background: var(--series-1); }
.row .bar.s2 { background: var(--series-2); }
"""


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def slide_title(sc):
    return f"""
    <div class="slide center">
      <div class="kicker">AI Paper Breakdown</div>
      <h1 class="big">{esc(sc['title'])}</h1>
      <h2 class="sub">{esc(sc.get('subtitle', ''))}</h2>
      <div class="footer">{esc(sc.get('footer', ''))}</div>
    </div>"""


def slide_bullets(sc):
    lis = "\n".join(f"<li>{esc(b)}</li>" for b in sc["bullets"])
    return f"""
    <div class="slide">
      <h1 class="head">{esc(sc['title'])}</h1>
      <ul class="bullets">{lis}</ul>
    </div>"""


def slide_pipeline(sc):
    parts = []
    for i, st in enumerate(sc["steps"]):
        parts.append(f"""
        <div class="step">
          <div class="n">{i + 1}</div>
          <div class="box"><div class="label">{esc(st['label'])}</div>
          <div class="detail">{esc(st['detail'])}</div></div>
        </div>""")
    return f"""
    <div class="slide">
      <h1 class="head">{esc(sc['title'])}</h1>
      <div class="pipe">{''.join(parts)}</div>
    </div>"""


def slide_chart_bars(sc):
    mx = sc.get("max", 100)
    rows = []
    for it in sc["items"]:
        pct = it["value"] / mx * 100
        hl = " hl" if it.get("highlight") else ""
        rows.append(f"""
        <div class="row{hl}">
          <div class="lab">{esc(it['label'])}</div>
          <div class="track" style="max-width:1000px">
            <div class="bar" style="width:{pct:.1f}%"></div>
            <div class="val" style="left:{pct:.1f}%">{it['value']}</div>
          </div>
        </div>""")
    note = f'<div class="note">{esc(sc["note"])}</div>' if sc.get("note") else ""
    return f"""
    <div class="slide">
      <h1 class="head">{esc(sc['title'])}</h1>
      <div class="chart">{''.join(rows)}</div>
      {note}
    </div>"""


def slide_chart_groups(sc):
    mx = sc.get("max", 100)
    chips = "".join(
        f'<div class="item"><div class="chip {"s1" if s["color"] == "series1" else "s2"}">'
        f'</div>{esc(s["name"])}</div>' for s in sc["series"])
    groups = []
    for g in sc["groups"]:
        bars = []
        for si, v in enumerate(g["values"]):
            cls = "s1" if sc["series"][si]["color"] == "series1" else "s2"
            pct = v / mx * 100
            bars.append(f"""
            <div class="row">
              <div class="lab" style="width:0"></div>
              <div class="track" style="max-width:1250px">
                <div class="bar {cls}" style="width:{pct:.1f}%"></div>
                <div class="val" style="left:{pct:.1f}%">{v}</div>
              </div>
            </div>""")
        groups.append(f'<div class="group"><div class="glab">{esc(g["label"])}</div>'
                      f'{"".join(bars)}</div>')
    note = f'<div class="note">{esc(sc["note"])}</div>' if sc.get("note") else ""
    return f"""
    <div class="slide">
      <h1 class="head">{esc(sc['title'])}</h1>
      <div class="legend">{chips}</div>
      {''.join(groups)}
      {note}
    </div>"""


LAYOUTS = {
    "title": slide_title,
    "bullets": slide_bullets,
    "pipeline": slide_pipeline,
    "chart_bars": slide_chart_bars,
    "chart_groups": slide_chart_groups,
}


def build_html(sc):
    body = LAYOUTS[sc["layout"]](sc)
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"


def launch_chromium(p):
    """Launch the pre-installed Chromium, falling back to an explicit path."""
    try:
        return p.chromium.launch()
    except Exception:
        for cand in (os.environ.get("CHROMIUM_PATH"), "/opt/pw-browsers/chromium",
                     "/usr/bin/chromium", "/usr/bin/chromium-browser"):
            if cand and Path(cand).exists():
                return p.chromium.launch(executable_path=cand)
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=str(HERE / "script.json"))
    ap.add_argument("--out", default=str(HERE / "output" / "slides"))
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    cfg = json.loads(Path(args.script).read_text())
    w, h = cfg["video"]["resolution"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = launch_chromium(p)
        page = browser.new_page(viewport={"width": w, "height": h})
        for sc in cfg["scenes"]:
            html_path = out / f"{sc['id']}.html"
            html_path.write_text(build_html(sc))
            page.goto(html_path.as_uri())
            png = out / f"{sc['id']}.png"
            page.screenshot(path=str(png))
            print(f"rendered {png}")
        browser.close()


if __name__ == "__main__":
    main()
