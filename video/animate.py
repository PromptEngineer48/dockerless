#!/usr/bin/env python3
"""Motion-graphics renderer: script.json + narration WAVs -> final MP4.

Every scene is an animated HTML page driven by a deterministic timeline:
Python bakes tween keyframes (sized to that scene's narration length) into
the page, then steps time frame-by-frame with `seek(ms)`, screenshots each
frame with Chromium, and pipes them straight into ffmpeg. No CSS animations,
no realtime capture — every frame is exact, so audio never drifts.

Usage:
    python animate.py                      # full video -> output/dockerless_video.mp4
    python animate.py --stills            # one mid-scene PNG per scene (fast QA)
    python animate.py --only 06_auc       # render a single scene segment
    python animate.py --fps 30 --crf 18
Scenes without output/audio/<id>.wav get a silent track timed to reading speed.
"""
import argparse
import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORDS_PER_SECOND = 2.6

# ---------------------------------------------------------------- palette --
INK = "#ffffff"
INK2 = "#c3c2b7"
MUTED = "#898781"
BLUE = "#3987e5"
AQUA = "#199e70"
SURFACE = "#1a1a19"
PAGE = "#0d0d0d"
BORDER = "rgba(255,255,255,0.10)"

CSS = f"""
* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:1920px; height:1080px; overflow:hidden; }}
body {{ background:{PAGE}; color:{INK};
  font-family: system-ui,-apple-system,"Segoe UI","DejaVu Sans",sans-serif; }}
#card {{ position:absolute; inset:40px; background:{SURFACE}; border-radius:24px;
  border:1px solid {BORDER}; overflow:hidden; }}
.orb {{ position:absolute; border-radius:50%; filter:blur(2px); pointer-events:none; }}
#grid {{ position:absolute; inset:-200px; opacity:.35;
  background-image:linear-gradient(rgba(255,255,255,0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px);
  background-size:120px 120px; }}
#content {{ position:absolute; inset:0; padding:70px 110px; }}
.kicker {{ color:{BLUE}; font-size:28px; font-weight:700; letter-spacing:.18em;
  text-transform:uppercase; }}
.head {{ font-size:66px; font-weight:800; letter-spacing:-0.01em; margin-top:22px; }}
.underline {{ height:8px; width:280px; border-radius:4px; margin-top:18px;
  background:linear-gradient(90deg,{BLUE},{AQUA}); transform-origin:left; }}
#progress {{ position:absolute; left:0; bottom:0; height:10px; width:0%;
  background:linear-gradient(90deg,{BLUE},{AQUA}); }}
.tag {{ position:absolute; top:44px; right:60px; font-size:26px; color:{MUTED};
  border:1px solid {BORDER}; border-radius:999px; padding:12px 28px;
  background:rgba(255,255,255,0.03); }}
/* title scene */
.bigwrap {{ position:absolute; left:110px; right:110px; top:300px; }}
.big {{ font-size:170px; font-weight:800; letter-spacing:-0.02em; display:flex; }}
.big span {{ display:inline-block; }}
.sub {{ font-size:50px; color:{INK2}; margin-top:34px; font-weight:400; }}
.chip {{ display:inline-block; margin-top:52px; font-size:30px; color:{INK};
  background:rgba(57,135,229,0.16); border:1px solid rgba(57,135,229,0.55);
  border-radius:999px; padding:16px 36px; }}
/* bullets */
.bullets {{ margin-top:56px; display:flex; flex-direction:column; gap:40px;
  max-width:1560px; }}
.bl {{ display:flex; align-items:flex-start; gap:30px; font-size:44px;
  line-height:1.3; color:{INK2}; }}
.bl .sq {{ flex:none; width:24px; height:24px; border-radius:7px; background:{BLUE};
  margin-top:12px; }}
.bl:nth-child(even) .sq {{ background:{AQUA}; }}
/* pipeline */
.pipe {{ margin-top:44px; position:relative; }}
#pline {{ position:absolute; left:29px; top:30px; bottom:30px; width:6px;
  border-radius:3px; background:linear-gradient(180deg,{BLUE},{AQUA});
  transform-origin:top; }}
#pdot {{ position:absolute; left:17px; width:30px; height:30px; border-radius:50%;
  background:#fff; box-shadow:0 0 26px 8px rgba(57,135,229,0.9); }}
.step {{ display:flex; align-items:center; gap:30px; margin-bottom:20px;
  position:relative; }}
.step .n {{ width:64px; height:64px; border-radius:50%; flex:none; background:{BLUE};
  display:flex; align-items:center; justify-content:center; font-size:32px;
  font-weight:800; z-index:2; box-shadow:0 0 0 8px {SURFACE}; }}
.step .box {{ background:{PAGE}; border:1px solid {BORDER}; border-radius:16px;
  padding:18px 36px; flex:1; }}
.step .lab {{ font-size:36px; font-weight:700; }}
.step .det {{ font-size:29px; color:{MUTED}; margin-top:4px; }}
/* charts */
.chart {{ margin-top:60px; display:flex; flex-direction:column; gap:36px; }}
.crow {{ display:flex; align-items:center; gap:38px; }}
.crow .lab {{ width:470px; flex:none; text-align:right; font-size:36px; color:{INK2}; }}
.crow.hl .lab {{ color:{INK}; font-weight:700; }}
.crow .track {{ flex:1; max-width:980px; height:52px; position:relative;
  background:rgba(255,255,255,0.04); border-radius:0 8px 8px 0; }}
.crow .bar {{ height:100%; width:0%; border-radius:0 8px 8px 0; background:{MUTED};
  border-left:3px solid #383835; }}
.crow.hl .bar {{ background:{BLUE}; box-shadow:0 0 30px rgba(57,135,229,0.55); }}
.crow .val {{ position:absolute; left:0%; top:50%; transform:translate(20px,-50%);
  font-size:37px; color:{INK2}; font-variant-numeric:tabular-nums; }}
.crow.hl .val {{ color:{INK}; font-weight:800; }}
.badge {{ position:absolute; font-size:34px; font-weight:800; color:#fff;
  background:linear-gradient(90deg,{BLUE},{AQUA}); border-radius:14px;
  padding:18px 34px; box-shadow:0 14px 40px rgba(0,0,0,0.45); }}
.legend {{ display:flex; gap:52px; margin-top:44px; font-size:33px; color:{INK2}; }}
.legend .it {{ display:flex; align-items:center; gap:16px; }}
.legend .cp {{ width:28px; height:28px; border-radius:8px; }}
.grp {{ margin-top:34px; }}
.grp .glab {{ font-size:34px; font-weight:700; }}
.grp .crow {{ margin-top:10px; }}
.grp .track {{ height:42px; max-width:1180px; }}
.grp .val {{ font-size:31px; }}
.delta {{ display:inline-block; margin-left:26px; font-size:29px; font-weight:800;
  color:#0ca30c; }}
.note {{ margin-top:46px; color:{MUTED}; font-size:31px; }}
/* outro buttons */
.btnrow {{ display:flex; gap:44px; margin-top:70px; }}
.btn {{ font-size:44px; font-weight:800; padding:30px 66px; border-radius:18px; }}
.btn.like {{ background:{BLUE}; }}
.btn.sub2 {{ background:#cc0000; }}
.btn.bell {{ background:rgba(255,255,255,0.08); border:1px solid {BORDER}; }}
"""

ENGINE_JS = """
const EASE = {
  linear: p => p,
  outCubic: p => 1 - Math.pow(1 - p, 3),
  inOut: p => p < .5 ? 2*p*p : 1 - Math.pow(-2*p + 2, 2)/2,
  outBack: p => { const c = 1.70158; return 1 + (c+1)*Math.pow(p-1,3) + c*Math.pow(p-1,2); },
};
let TL = null;
function initTL(data) { TL = data; }
function seek(ms) {
  const t = ms / 1000;
  const tf = {};
  for (const tw of TL.tweens) {
    let p = tw.t1 > tw.t0 ? (t - tw.t0) / (tw.t1 - tw.t0) : 1;
    p = Math.max(0, Math.min(1, p));
    p = EASE[tw.ease || 'outCubic'](p);
    const v = tw.from + (tw.to - tw.from) * p;
    const el = document.querySelector(tw.sel);
    if (!el) continue;
    if (['x','y','scale','rot','sx','sy'].includes(tw.p)) {
      (tf[tw.sel] = tf[tw.sel] || {})[tw.p] = v;
    } else if (tw.p === 'opacity') el.style.opacity = v;
    else if (tw.p === 'w') el.style.width = v + '%';
    else if (tw.p === 'left') el.style.left = v + '%';
    else if (tw.p === 'count') el.textContent = v.toFixed(tw.dec || 0);
    else if (tw.p === 'blur') el.style.filter = `blur(${v}px)`;
  }
  for (const sel in tf) {
    const el = document.querySelector(sel); if (!el) continue;
    const s = tf[sel];
    el.style.transform =
      `translate(${s.x||0}px,${s.y||0}px) rotate(${s.rot||0}deg)` +
      ` scale(${s.scale==null?1:s.scale})` +
      (s.sx!=null ? ` scaleX(${s.sx})` : '') + (s.sy!=null ? ` scaleY(${s.sy})` : '');
  }
  for (const lp of TL.loops) {
    const el = document.querySelector(lp.sel); if (!el) continue;
    if (lp.fn === 'float') {
      const dx = Math.sin(t*lp.sp + lp.ph) * lp.amp;
      const dy = Math.cos(t*lp.sp*0.8 + lp.ph) * lp.amp * 0.7;
      el.style.transform = `translate(${dx}px,${dy}px)`;
    } else if (lp.fn === 'rise') {
      const cyc = (t*lp.sp + lp.ph) % 1;
      el.style.transform = `translateY(${(1-cyc)*-1000}px)`;
      el.style.opacity = cyc < .08 ? cyc/.08 : (1-cyc) * lp.op;
    } else if (lp.fn === 'pulse') {
      const s = 1 + Math.sin(t*lp.sp + lp.ph) * lp.amp;
      el.style.transform = `scale(${s})`;
    } else if (lp.fn === 'travel') {
      if (t < lp.from) { el.style.opacity = 0; continue; }
      el.style.opacity = 1;
      const cyc = ((t-lp.from)*lp.sp) % 1;
      el.style.top = (lp.a + (lp.b-lp.a)*EASE.inOut(cyc)) + 'px';
    } else if (lp.fn === 'drift') {
      el.style.backgroundPosition = `${t*lp.sp}px ${t*lp.sp*0.6}px`;
    } else if (lp.fn === 'shine') {
      const cyc = (t*lp.sp + lp.ph) % 1;
      el.style.left = (cyc*260 - 80) + '%';
    }
  }
}
"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------ timeline DSL --
class Timeline:
    def __init__(self):
        self.tweens, self.loops = [], []

    def tw(self, sel, p, from_, to, t0, t1, ease="outCubic", **kw):
        self.tweens.append(dict(sel=sel, p=p, **{"from": from_}, to=to,
                                t0=round(t0, 3), t1=round(t1, 3), ease=ease, **kw))

    def loop(self, sel, fn, **kw):
        self.loops.append(dict(sel=sel, fn=fn, **kw))

    def enter(self, sel, t0, dur=0.55, dy=46, ease="outCubic"):
        """fade + slide-up entrance"""
        self.tw(sel, "opacity", 0, 1, t0, t0 + dur, ease)
        self.tw(sel, "y", dy, 0, t0, t0 + dur, ease)

    def pop(self, sel, t0, dur=0.5):
        self.tw(sel, "opacity", 0, 1, t0, t0 + dur * 0.5)
        self.tw(sel, "scale", 0.2, 1, t0, t0 + dur, "outBack")


def chrome(tl, dur, orbs=3):
    """Background + header elements every scene shares."""
    html = ['<div id="grid"></div>']
    palette = [(BLUE, 0.10), (AQUA, 0.09), (BLUE, 0.07)]
    pos = [("-260px", "-260px", 780), ("60%", "70%", 640), ("70%", "-180px", 520)]
    for i in range(orbs):
        c, a = palette[i % 3]
        x, y, s = pos[i % 3]
        html.append(
            f'<div class="orb" id="orb{i}" style="left:{x};top:{y};width:{s}px;'
            f'height:{s}px;background:radial-gradient(circle,{c}{"" if a else ""},'
            f'transparent 70%);background:radial-gradient(circle,'
            f'rgba(57,135,229,{a}) 0%,transparent 70%);"></div>')
        tl.loop(f"#orb{i}", "float", amp=40 + 14 * i, sp=0.35 + 0.1 * i, ph=i * 2.1)
    html.append('<div class="tag" id="tag">arXiv 2606.28436</div>')
    html.append('<div id="progress"></div>')
    tl.loop("#grid", "drift", sp=8)
    tl.tw("#progress", "w", 0, 100, 0, dur, "linear")
    tl.tw("#tag", "opacity", 0, 1, 0.3, 0.9)
    return "\n".join(html)


def header(tl, title, kicker="AI Paper Breakdown"):
    tl.enter("#kick", 0.1, 0.5, dy=-30)
    tl.enter("#head", 0.22, 0.6)
    tl.tw("#ul", "sx", 0, 1, 0.55, 1.15)
    return (f'<div class="kicker" id="kick">{esc(kicker)}</div>'
            f'<div class="head" id="head">{esc(title)}</div>'
            f'<div class="underline" id="ul"></div>')


# --------------------------------------------------------------- layouts ---
def build_title(sc, dur, tl):
    size = 170 if len(sc["title"]) <= 14 else 110
    letters = (f'<div class="big" style="font-size:{size}px">' +
               "".join(f'<span id="L{i}">{esc(ch) if ch != " " else "&nbsp;"}</span>'
                       for i, ch in enumerate(sc["title"])) + "</div>")
    for i in range(len(sc["title"])):
        t0 = 0.35 + i * 0.055
        tl.pop(f"#L{i}", t0, 0.6)
        tl.tw(f"#L{i}", "rot", -14, 0, t0, t0 + 0.6, "outBack")
    tl.enter("#sub", 0.5 + len(sc["title"]) * 0.055, 0.7)
    tl.pop("#chip", min(2.6, dur * 0.35), 0.6)
    tl.enter("#kick", 0.1, 0.5, dy=-30)
    # rising particles
    parts = []
    for i in range(16):
        x = 60 + (i * 117) % 1760
        s = 8 + (i * 7) % 14
        c = BLUE if i % 2 else AQUA
        parts.append(f'<div class="orb" id="pt{i}" style="left:{x}px;top:1060px;'
                     f'width:{s}px;height:{s}px;background:{c};opacity:0"></div>')
        tl.loop(f"#pt{i}", "rise", sp=1 / (7 + i % 5), ph=i * 0.37, op=0.55)
    return f"""{''.join(parts)}
    <div class="bigwrap">
      <div class="kicker" id="kick" style="font-size:34px">AI Paper Breakdown</div>
      {letters}
      <div class="sub" id="sub">{esc(sc.get('subtitle', ''))}</div><br>
      <div class="chip" id="chip">{esc(sc.get('footer', ''))}</div>
    </div>"""


def build_bullets(sc, dur, tl):
    n = len(sc["bullets"])
    stag = min(1.15, dur * 0.55 / n)
    items = []
    for i, b in enumerate(sc["bullets"]):
        t0 = 1.0 + i * stag
        items.append(f'<div class="bl" id="bl{i}"><div class="sq" id="sq{i}"></div>'
                     f'<div>{esc(b)}</div></div>')
        tl.tw(f"#bl{i}", "opacity", 0, 1, t0, t0 + 0.45)
        tl.tw(f"#bl{i}", "x", -90, 0, t0, t0 + 0.55)
        tl.tw(f"#sq{i}", "rot", 135, 0, t0, t0 + 0.7, "outBack")
        tl.tw(f"#sq{i}", "scale", 0, 1, t0, t0 + 0.6, "outBack")
    return header(tl, sc["title"]) + f'<div class="bullets">{"".join(items)}</div>'


def build_pipeline(sc, dur, tl):
    n = len(sc["steps"])
    stag = min(0.95, dur * 0.5 / n)
    steps = []
    for i, st in enumerate(sc["steps"]):
        t0 = 0.9 + i * stag
        steps.append(f"""
        <div class="step" id="st{i}">
          <div class="n" id="sn{i}">{i + 1}</div>
          <div class="box"><div class="lab">{esc(st['label'])}</div>
          <div class="det">{esc(st['detail'])}</div></div>
        </div>""")
        tl.tw(f"#st{i}", "opacity", 0, 1, t0, t0 + 0.45)
        tl.tw(f"#st{i}", "x", 110, 0, t0, t0 + 0.6)
        tl.pop(f"#sn{i}", t0 + 0.15, 0.55)
    tl.tw("#pline", "sy", 0, 1, 0.9, 0.9 + n * stag)
    tl.loop("#pdot", "travel", **{"from": 0.9 + n * stag},
            sp=1 / 3.2, a=30, b=560)
    return (header(tl, sc["title"]) +
            f'<div class="pipe"><div id="pline"></div><div id="pdot"></div>'
            f'{"".join(steps)}</div>')


def build_chart_bars(sc, dur, tl):
    mx = sc.get("max", 100)
    rows = []
    for i, it in enumerate(sc["items"]):
        pct = it["value"] / mx * 100
        t0 = 1.0 + i * 0.5
        hl = " hl" if it.get("highlight") else ""
        rows.append(f"""
        <div class="crow{hl}" id="cr{i}">
          <div class="lab">{esc(it['label'])}</div>
          <div class="track">
            <div class="bar" id="bar{i}"></div>
            <div class="val" id="val{i}">0</div>
          </div>
        </div>""")
        tl.tw(f"#cr{i}", "opacity", 0, 1, t0 - 0.25, t0 + 0.2)
        tl.tw(f"#bar{i}", "w", 0, pct, t0, t0 + 1.0)
        tl.tw(f"#val{i}", "left", 0, pct, t0, t0 + 1.0)
        tl.tw(f"#val{i}", "count", 0, it["value"], t0, t0 + 1.0, dec=1)
        if it.get("highlight"):
            tl.loop(f"#bar{i}", "pulse", sp=2.2, ph=0, amp=0.012)
    t_badge = min(dur * 0.62, dur - 2.5)
    tl.pop("#badge", t_badge, 0.7)
    badge = (f'<div class="badge" id="badge" style="right:130px;top:150px">'
             f'+14.3 AUC vs best open-source verifier</div>')
    note = f'<div class="note" id="note">{esc(sc.get("note", ""))}</div>'
    tl.tw("#note", "opacity", 0, 1, t_badge + 0.5, t_badge + 1.0)
    return (header(tl, sc["title"]) + f'<div class="chart">{"".join(rows)}</div>'
            + note + badge)


def build_chart_groups(sc, dur, tl):
    mx = sc.get("max", 100)
    colors = {"series1": BLUE, "series2": AQUA}
    chips = []
    for i, s in enumerate(sc["series"]):
        chips.append(f'<div class="it" id="lg{i}"><div class="cp" style="background:'
                     f'{colors[s["color"]]}"></div>{esc(s["name"])}</div>')
        tl.pop(f"#lg{i}", 0.7 + i * 0.2, 0.5)
    groups = []
    deltas = [g["values"][1] - g["values"][0] for g in sc["groups"]]
    for gi, g in enumerate(sc["groups"]):
        t0 = 1.2 + gi * min(1.15, dur * 0.42 / len(sc["groups"]))
        bars = []
        for si, v in enumerate(g["values"]):
            pct = v / mx * 100
            c = colors[sc["series"][si]["color"]]
            bid = f"g{gi}b{si}"
            bars.append(f"""
            <div class="crow">
              <div class="track">
                <div class="bar" id="{bid}" style="background:{c}"></div>
                <div class="val" id="{bid}v">0</div>
              </div>
            </div>""")
            tb = t0 + 0.25 + si * 0.18
            tl.tw(f"#{bid}", "w", 0, pct, tb, tb + 0.9)
            tl.tw(f"#{bid}v", "left", 0, pct, tb, tb + 0.9)
            tl.tw(f"#{bid}v", "count", 0, v, tb, tb + 0.9, dec=1)
        groups.append(f"""
        <div class="grp" id="grp{gi}">
          <div class="glab">{esc(g['label'])}<span class="delta" id="dl{gi}">
          +{deltas[gi]:.1f}</span></div>{''.join(bars)}
        </div>""")
        tl.tw(f"#grp{gi}", "opacity", 0, 1, t0 - 0.2, t0 + 0.25)
        tl.tw(f"#grp{gi}", "x", -70, 0, t0 - 0.2, t0 + 0.35)
        tl.pop(f"#dl{gi}", t0 + 1.35, 0.5)
    note = f'<div class="note" id="note">{esc(sc.get("note", ""))}</div>'
    t_note = min(dur * 0.7, dur - 2.0)
    tl.tw("#note", "opacity", 0, 1, t_note, t_note + 0.5)
    return (header(tl, sc["title"]) + f'<div class="legend">{"".join(chips)}</div>'
            + "".join(groups) + note)


def build_outro(sc, dur, tl):
    html = build_title(sc, dur, tl)
    btns = ['<div class="btnrow">']
    for i, (cls, txt) in enumerate([("like", "LIKE"), ("sub2", "SUBSCRIBE"),
                                    ("bell", "🔔" if False else "BELL ON")]):
        btns.append(f'<div class="btn {cls}" id="btn{i}">{txt}</div>')
        tl.pop(f"#btn{i}", dur * 0.38 + i * 0.35, 0.65)
        tl.loop(f"#btn{i}", "pulse", sp=2.0, ph=i * 1.1, amp=0.02)
    btns.append("</div>")
    return html.replace('<div class="chip"', "".join(btns) + '<div class="chip"')


LAYOUTS = {
    "title": build_title,
    "bullets": build_bullets,
    "pipeline": build_pipeline,
    "chart_bars": build_chart_bars,
    "chart_groups": build_chart_groups,
}


def build_scene_html(sc, dur):
    tl = Timeline()
    body_chrome_tl = Timeline()  # chrome first so content draws above orbs
    bg = chrome(body_chrome_tl, dur)
    builder = build_outro if sc["id"] == "09_outro" else LAYOUTS[sc["layout"]]
    content = builder(sc, dur, tl)
    tl.tweens = body_chrome_tl.tweens + tl.tweens
    tl.loops = body_chrome_tl.loops + tl.loops
    data = json.dumps({"tweens": tl.tweens, "loops": tl.loops})
    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>{CSS}</style></head><body>
<div id="card">{bg}<div id="content">{content}</div></div>
<script>{ENGINE_JS}
initTL({data}); seek(0);</script></body></html>"""


# ---------------------------------------------------------------- render ---
def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def wav_duration(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def scene_duration(sc, audio_dir, tail):
    wav = audio_dir / f"{sc['id']}.wav"
    if wav.exists():
        return wav_duration(wav) + tail, wav
    return max(4.0, len(sc["narration"].split()) / WORDS_PER_SECOND) + tail, None


def launch_chromium(p):
    try:
        return p.chromium.launch()
    except Exception:
        for cand in ("/opt/pw-browsers/chromium", "/usr/bin/chromium"):
            if Path(cand).exists():
                return p.chromium.launch(executable_path=cand)
        raise


def render_scene(page, ffmpeg, sc, dur, wav, seg, fps, crf, tail):
    html = build_scene_html(sc, dur)
    tmp = seg.with_suffix(".html")
    tmp.write_text(html)
    page.goto(tmp.as_uri())
    nframes = int(dur * fps)
    audio_in = (["-i", str(wav)] if wav else
                ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"])
    cmd = [ffmpeg, "-y",
           "-f", "image2pipe", "-framerate", str(fps), "-i", "pipe:0",
           *audio_in,
           "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
           "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           *( ["-af", f"apad=pad_dur={tail}"] if wav else [] ),
           "-t", f"{dur:.3f}", str(seg)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for f in range(nframes):
        page.evaluate(f"seek({f * 1000 / fps:.2f})")
        proc.stdin.write(page.screenshot(type="jpeg", quality=92))
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {sc['id']}")
    return nframes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=str(HERE / "script.json"))
    ap.add_argument("--audio", default=str(HERE / "output" / "audio"))
    ap.add_argument("--out", default=str(HERE / "output" / "dockerless_video.mp4"))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=19)
    ap.add_argument("--tail", type=float, default=0.6)
    ap.add_argument("--only", default=None)
    ap.add_argument("--stills", action="store_true",
                    help="render one mid-scene PNG per scene instead of video")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    cfg = json.loads(Path(args.script).read_text())
    scenes = cfg["scenes"]
    if args.only:
        scenes = [s for s in scenes if s["id"] == args.only]
    audio_dir = Path(args.audio)
    seg_dir = HERE / "output" / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()

    with sync_playwright() as p:
        browser = launch_chromium(p)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        segs = []
        for sc in scenes:
            dur, wav = scene_duration(sc, audio_dir, args.tail)
            if args.stills:
                html = build_scene_html(sc, dur)
                tmp = seg_dir / f"{sc['id']}.html"
                tmp.write_text(html)
                page.goto(tmp.as_uri())
                page.evaluate(f"seek({dur * 600:.0f})")  # 60% in
                out = seg_dir / f"{sc['id']}_still.png"
                page.screenshot(path=str(out))
                print(f"[{sc['id']}] still -> {out}")
                continue
            seg = seg_dir / f"{sc['id']}.mp4"
            n = render_scene(page, ffmpeg, sc, dur, wav, seg, args.fps,
                             args.crf, args.tail)
            print(f"[{sc['id']}] {dur:.1f}s / {n} frames"
                  f"{' (SILENT)' if not wav else ''}")
            segs.append(seg)
        browser.close()

    if args.stills or args.only:
        return
    concat = seg_dir / "list.txt"
    concat.write_text("".join(f"file '{s.resolve()}'\n" for s in segs))
    out = Path(args.out)
    subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-c", "copy", str(out)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
