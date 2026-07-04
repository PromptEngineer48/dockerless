#!/usr/bin/env python3
"""Generate the narration for every scene in YOUR cloned voice with Qwen3-TTS.

Uses the open-source Qwen3-TTS voice-clone model
(Qwen/Qwen3-TTS-12Hz-1.7B-Base, Apache-2.0). It clones a voice from a short
reference clip — ~5-15 seconds of clean speech is enough.

Setup (GPU strongly recommended; CPU works but is ~3-5x slower than realtime):
    pip install -U qwen-tts soundfile

Provide your voice:
    video/voice/ref.wav   — 5-15 s of you speaking, clean, no music
    video/voice/ref.txt   — the EXACT transcript of ref.wav

Run:
    python tts_qwen3.py                       # all scenes -> output/audio/*.wav
    python tts_qwen3.py --only 01_title       # regenerate a single scene
    python tts_qwen3.py --device cpu          # force CPU

Outputs one WAV per scene: output/audio/<scene_id>.wav
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


def pick_device(arg):
    if arg != "auto":
        return arg
    try:
        import torch
        return "cuda:0" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=str(HERE / "script.json"))
    ap.add_argument("--ref-audio", default=str(HERE / "voice" / "ref.wav"))
    ap.add_argument("--ref-text", default=str(HERE / "voice" / "ref.txt"))
    ap.add_argument("--out", default=str(HERE / "output" / "audio"))
    ap.add_argument("--language", default="English")
    ap.add_argument("--device", default="auto", help="auto | cpu | cuda:0 ...")
    ap.add_argument("--only", default=None, help="generate a single scene id")
    args = ap.parse_args()

    ref_audio = Path(args.ref_audio)
    ref_text_path = Path(args.ref_text)
    if not ref_audio.exists() or not ref_text_path.exists():
        raise SystemExit(
            f"Missing reference voice.\n"
            f"  put a 5-15s clean clip of your voice at: {ref_audio}\n"
            f"  and its exact transcript at:            {ref_text_path}"
        )
    ref_text = ref_text_path.read_text().strip()

    cfg = json.loads(Path(args.script).read_text())
    scenes = cfg["scenes"]
    if args.only:
        scenes = [s for s in scenes if s["id"] == args.only]
        if not scenes:
            raise SystemExit(f"no scene with id {args.only}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel

    device = pick_device(args.device)
    dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
    kwargs = dict(device_map=device, dtype=dtype)
    if device.startswith("cuda"):
        # flash-attn is optional; fall back silently if not installed
        try:
            import flash_attn  # noqa: F401
            kwargs["attn_implementation"] = "flash_attention_2"
        except ImportError:
            pass

    print(f"loading {MODEL_ID} on {device} ...")
    model = Qwen3TTSModel.from_pretrained(MODEL_ID, **kwargs)

    # Build the clone prompt once, reuse for every scene.
    prompt_items = model.create_voice_clone_prompt(
        ref_audio=str(ref_audio),
        ref_text=ref_text,
        x_vector_only_mode=False,
    )

    for sc in scenes:
        text = sc["narration"]
        print(f"[{sc['id']}] {len(text)} chars ...")
        wavs, sr = model.generate_voice_clone(
            text=text,
            language=args.language,
            voice_clone_prompt=prompt_items,
        )
        wav_path = out / f"{sc['id']}.wav"
        sf.write(str(wav_path), wavs[0], sr)
        print(f"  -> {wav_path} ({len(wavs[0]) / sr:.1f}s)")

    print("done. now run: python assemble.py")


if __name__ == "__main__":
    main()
