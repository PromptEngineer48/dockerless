#!/usr/bin/env python3
"""Assemble slides + narration into the final MP4 with ffmpeg.

For every scene: takes output/slides/<id>.png and, if present,
output/audio/<id>.wav (from tts_qwen3.py). Scenes without audio get a silent
track sized by an estimated reading time, so you can preview the cut before
generating the voice-over.

Usage:
    python assemble.py [--out output/dockerless_video.mp4] [--tail 0.6]
"""
import argparse
import json
import shutil
import subprocess
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORDS_PER_SECOND = 2.6  # used only for silent-preview scene durations


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise SystemExit("ffmpeg not found. install it, or: pip install imageio-ffmpeg")


def wav_duration(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=str(HERE / "script.json"))
    ap.add_argument("--slides", default=str(HERE / "output" / "slides"))
    ap.add_argument("--audio", default=str(HERE / "output" / "audio"))
    ap.add_argument("--out", default=str(HERE / "output" / "dockerless_video.mp4"))
    ap.add_argument("--tail", type=float, default=0.6,
                    help="seconds of pause appended after each scene's audio")
    args = ap.parse_args()

    ffmpeg = find_ffmpeg()
    cfg = json.loads(Path(args.script).read_text())
    fps = cfg["video"].get("fps", 30)

    seg_dir = HERE / "output" / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)

    segments = []
    silent = 0
    for sc in cfg["scenes"]:
        png = Path(args.slides) / f"{sc['id']}.png"
        if not png.exists():
            raise SystemExit(f"missing slide {png} — run render_slides.py first")
        wav = Path(args.audio) / f"{sc['id']}.wav"
        seg = seg_dir / f"{sc['id']}.mp4"

        if wav.exists():
            dur = wav_duration(wav) + args.tail
            cmd = [ffmpeg, "-y", "-loop", "1", "-framerate", str(fps),
                   "-i", str(png), "-i", str(wav),
                   "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                   "-af", f"apad=pad_dur={args.tail}",
                   "-t", f"{dur:.2f}", str(seg)]
        else:
            silent += 1
            dur = max(3.5, len(sc["narration"].split()) / WORDS_PER_SECOND) + args.tail
            cmd = [ffmpeg, "-y", "-loop", "1", "-framerate", str(fps),
                   "-i", str(png),
                   "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                   "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "128k",
                   "-t", f"{dur:.2f}", str(seg)]
        print(f"[{sc['id']}] {dur:.1f}s {'(SILENT preview)' if not wav.exists() else ''}")
        run(cmd)
        segments.append(seg)

    concat_list = seg_dir / "list.txt"
    concat_list.write_text("".join(f"file '{s.resolve()}'\n" for s in segments))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c", "copy", str(out)])

    total = sum(wav_duration(Path(args.audio) / f"{s['id']}.wav") + args.tail
                if (Path(args.audio) / f"{s['id']}.wav").exists()
                else max(3.5, len(s["narration"].split()) / WORDS_PER_SECOND) + args.tail
                for s in cfg["scenes"])
    print(f"\nwrote {out} (~{total:.0f}s, {len(segments)} scenes)")
    if silent:
        print(f"note: {silent} scene(s) have NO voice-over yet — "
              f"run tts_qwen3.py with your reference voice, then re-run assemble.py")


if __name__ == "__main__":
    main()
