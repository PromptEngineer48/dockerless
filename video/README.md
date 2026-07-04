# Dockerless paper video — cloned-voice pipeline

Makes an explainer video about the paper **"Dockerless: Environment-Free Program
Verifier for Coding Agents"** ([arXiv 2606.28436](https://arxiv.org/abs/2606.28436)),
narrated in **your own cloned voice** via the open-source
[Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) (Apache-2.0).

## Pipeline

```
script.json ──► render_slides.py ──► output/slides/*.png ─┐
                                                          ├─► assemble.py ──► output/dockerless_video.mp4
voice/ref.wav ─► tts_qwen3.py ─────► output/audio/*.wav ──┘
```

Everything is driven by `script.json` — edit the `narration` text there to make
it sound like *you*, then regenerate.

## 1. Install

```bash
pip install -r requirements.txt
python -m playwright install chromium   # skip if Chromium is already available
```

## 2. Provide your voice (the cloning part)

Qwen3-TTS clones a voice from a short reference clip:

- `voice/ref.wav` — **5–15 seconds** of you speaking, clean audio, no music.
- `voice/ref.txt` — the **exact transcript** of what you say in the clip.

## 3. Generate

```bash
python render_slides.py     # slides -> output/slides/*.png
python tts_qwen3.py         # narration in your cloned voice -> output/audio/*.wav
python assemble.py          # final video -> output/dockerless_video.mp4
```

`assemble.py` also works **before** the TTS step — scenes without audio get a
silent track timed to reading speed, so you can preview the cut.

## Notes

- **GPU strongly recommended** for TTS. The 1.7B clone model runs on CPU too,
  but expect roughly 3–5× slower than realtime.
- Alternative: Alibaba Cloud's **DashScope API** hosts qwen3-tts with voice
  enrollment if you'd rather not run the model locally — `tts_qwen3.py` is the
  local, free, open-source path.
- Regenerate a single scene after editing its narration:
  `python tts_qwen3.py --only 06_auc && python assemble.py`
