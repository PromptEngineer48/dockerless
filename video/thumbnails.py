#!/usr/bin/env python3
"""Render the thumbnail options from PRODUCTION.md as 1280x720 PNGs.

Usage: python thumbnails.py   -> output/thumbs/thumb_0X.png
Left third is intentionally kept clear for a face cutout.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent

BASE_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
html,body { width:1280px; height:720px; overflow:hidden; }
body { background:#0d0d0d; color:#fff; position:relative;
  font-family: system-ui,-apple-system,"Segoe UI","DejaVu Sans",sans-serif; }
.glow { position:absolute; border-radius:50%; }
.g1 { left:-200px; top:-200px; width:640px; height:640px;
  background:radial-gradient(circle, rgba(57,135,229,0.35), transparent 70%); }
.g2 { right:-160px; bottom:-220px; width:560px; height:560px;
  background:radial-gradient(circle, rgba(25,158,112,0.30), transparent 70%); }
.grid { position:absolute; inset:0; opacity:.5;
  background-image:linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
  background-size:90px 90px; }
.face { position:absolute; left:36px; bottom:24px; width:360px; color:#52514e;
  font-size:22px; border:3px dashed #383835; border-radius:18px; height:420px;
  display:flex; align-items:center; justify-content:center; text-align:center; }
.brand { position:absolute; top:28px; right:36px; font-size:26px; font-weight:800;
  letter-spacing:.12em; color:#3987e5; }
"""

FACE = '<div class="face">YOUR FACE<br>HERE</div><div class="brand">AI PAPER BREAKDOWN</div>'
BG = '<div class="glow g1"></div><div class="glow g2"></div><div class="grid"></div>'

THUMBS = {
    "thumb_01_docker_is_dead": BG + FACE + """
    <style>
      .whale { position:absolute; right:120px; top:70px; font-size:230px;
        filter:drop-shadow(0 20px 50px rgba(57,135,229,0.45)); }
      .cross { position:absolute; right:96px; top:56px; width:300px; height:300px; }
      .cross::before, .cross::after { content:""; position:absolute; left:50%; top:50%;
        width:340px; height:34px; background:#e34948; border-radius:17px;
        box-shadow:0 8px 30px rgba(0,0,0,0.6); }
      .cross::before { transform:translate(-50%,-50%) rotate(45deg); }
      .cross::after { transform:translate(-50%,-50%) rotate(-45deg); }
      .t1 { position:absolute; left:440px; bottom:150px; font-size:120px;
        font-weight:900; letter-spacing:-0.02em; line-height:.95;
        text-shadow:0 12px 40px rgba(0,0,0,.8); }
      .t1 em { font-style:normal; color:#e34948; }
      .t2 { position:absolute; left:444px; bottom:70px; font-size:40px;
        color:#c3c2b7; font-weight:700; }
    </style>
    <div class="whale">🐳</div><div class="cross"></div>
    <div class="t1">DOCKER<br>IS <em>DEAD?</em></div>
    <div class="t2">…for AI agent training</div>""",

    "thumb_02_beats_gpt": BG + FACE + """
    <style>
      .num { position:absolute; left:430px; top:60px; font-size:210px; font-weight:900;
        background:linear-gradient(90deg,#3987e5,#19c98f);
        -webkit-background-clip:text; background-clip:text; color:transparent;
        letter-spacing:-0.03em; }
      .auc { position:absolute; left:1010px; top:150px; font-size:60px; font-weight:800;
        color:#c3c2b7; }
      .beats { position:absolute; left:436px; top:300px; font-size:74px; font-weight:900; }
      .beats em { font-style:normal; color:#e34948; }
      .bars { position:absolute; left:440px; bottom:60px; display:flex; gap:40px;
        align-items:flex-end; height:240px; }
      .bar { width:150px; border-radius:12px 12px 0 0; position:relative;
        display:flex; justify-content:center; }
      .bar span { position:absolute; top:-52px; font-size:34px; font-weight:800; }
      .bl { height:100%; background:#3987e5; box-shadow:0 0 50px rgba(57,135,229,.6); }
      .gr { height:72%; background:#52514e; }
      .lab { position:absolute; bottom:14px; font-size:30px; font-weight:700; }
    </style>
    <div class="num">81.0</div><div class="auc">AUC</div>
    <div class="beats">BEATS <em>GPT-5.4</em></div>
    <div class="bars">
      <div class="bar bl"><span>81.0</span><div class="lab">OURS</div></div>
      <div class="bar gr"><span>75.9</span><div class="lab">GPT-5.4</div></div>
    </div>""",

    "thumb_03_no_docker": BG + FACE + """
    <style>
      .rows { position:absolute; left:440px; top:80px; display:flex;
        flex-direction:column; gap:44px; }
      .r { display:flex; align-items:center; gap:34px; font-size:80px; font-weight:900;
        letter-spacing:-0.02em; text-shadow:0 12px 40px rgba(0,0,0,.8);
        white-space:nowrap; }
      .r .ck { width:84px; height:84px; border-radius:22px; background:#0ca30c;
        display:flex; align-items:center; justify-content:center; font-size:56px;
        flex:none; box-shadow:0 10px 34px rgba(12,163,12,.4); }
      .r.red .ck { background:#e34948; box-shadow:0 10px 34px rgba(227,73,72,.4); }
      .r em { font-style:normal; color:#19c98f; }
    </style>
    <div class="rows">
      <div class="r red"><div class="ck">✕</div><div>NO DOCKER</div></div>
      <div class="r red"><div class="ck">✕</div><div>NO TESTS</div></div>
      <div class="r"><div class="ck">✓</div><div><em>62%</em> SWE-BENCH</div></div>
    </div>""",
}


def main():
    from playwright.sync_api import sync_playwright
    out = HERE / "output" / "thumbs"
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        for name, body in THUMBS.items():
            f = out / f"{name}.html"
            f.write_text(f"<!doctype html><html><head><meta charset='utf-8'>"
                         f"<style>{BASE_CSS}</style></head><body>{body}</body></html>")
            page.goto(f.as_uri())
            page.screenshot(path=str(out / f"{name}.png"))
            print(f"-> {out / (name + '.png')}")
        browser.close()


if __name__ == "__main__":
    main()
