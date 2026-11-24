#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 INTENSE FINANCE, LLC / SLOPCORE TV
# Portable dry-run for assemble_mv.py. Generates synthetic clips and, if needed,
# a short tone plus a 120 BPM beat grid — no hardcoded machine paths.
"""
Usage:
  python3 test_assemble_mv.py
  python3 test_assemble_mv.py --out-dir ./dryrun
  python3 test_assemble_mv.py --audio master.wav --beat-grid beat-grid.json --out-dir ./dryrun
"""
import argparse, json, math, os, struct, subprocess, sys, wave

HERE = os.path.dirname(os.path.abspath(__file__))

def ff(*a):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True)

def write_tone(path, seconds=16.0, sr=48000):
    n = int(round(seconds * sr))
    with wave.open(path, "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            t = i / sr
            # quiet 120 BPM click + low tone, 16-bit stereo, peak well below full scale
            click = 0.18 if (i % int(sr * 0.5) < int(sr * 0.01)) else 0.0
            s = 0.12 * math.sin(2 * math.pi * 110 * t) + click
            v = max(-32767, min(32767, int(s * 32767)))
            frames += struct.pack("<hh", v, v)
        w.writeframes(bytes(frames))

def write_grid(path, duration=16.0, bpm=120):
    bar = 4 * (60.0 / bpm)
    bars = int(round(duration / bar))
    json.dump({
        "title": "dry-run",
        "video_title": "Fun, Fun, Fun",
        "bpm": bpm,
        "time_signature": "4/4",
        "beat_sec": 60.0 / bpm,
        "bar_sec": bar,
        "bars": bars,
        "duration_sec": duration,
    }, open(path, "w"), indent=1)

def probe(f):
    return json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", f],
        capture_output=True, text=True, check=True).stdout)

def atoms(f):
    order = []
    with open(f, "rb") as h:
        while True:
            hd = h.read(8)
            if len(hd) < 8:
                break
            sz, typ = struct.unpack(">I4s", hd)
            order.append(typ.decode("ascii", "replace"))
            if sz == 1:
                sz = struct.unpack(">Q", h.read(8))[0]
                h.seek(sz - 16, 1)
            else:
                h.seek(max(sz, 8) - 8, 1)
    return order

def main():
    ap = argparse.ArgumentParser(description="Portable dry-run for grobie-mv / assemble_mv.py")
    ap.add_argument("--out-dir", default=os.path.join(os.getcwd(), "grobie-mv-dryrun"))
    ap.add_argument("--audio")
    ap.add_argument("--beat-grid")
    ap.add_argument("--duration", type=float, default=16.0)
    a = ap.parse_args()
    out_dir = os.path.abspath(a.out_dir)
    clips = os.path.join(out_dir, "clips")
    os.makedirs(clips, exist_ok=True)

    audio = a.audio
    gridp = a.beat_grid
    if audio is None or gridp is None:
        audio = os.path.join(out_dir, "dryrun-tone.wav")
        gridp = os.path.join(out_dir, "dryrun-beat-grid.json")
        write_tone(audio, a.duration)
        write_grid(gridp, a.duration)
    audio = os.path.abspath(audio)
    gridp = os.path.abspath(gridp)

    ff("-f", "lavfi", "-i", "testsrc2=s=1280x720:r=24:d=6", "-c:v", "libx264", "-pix_fmt", "yuv420p", os.path.join(clips, "clipA.mp4"))
    ff("-f", "lavfi", "-i", "mandelbrot=s=1280x720:r=24", "-t", "2.5", "-c:v", "libx264", "-pix_fmt", "yuv420p", os.path.join(clips, "clipB.mp4"))
    ff("-f", "lavfi", "-i", "gradients=s=1280x720:r=24:speed=0.03:d=1.5", "-c:v", "libx264", "-pix_fmt", "yuv420p", os.path.join(clips, "clipC.mp4"))
    ff("-f", "lavfi", "-i", "cellauto=s=1280x720:r=24:rule=110", "-t", "5",
       "-vf", "format=yuv420p,colorchannelmixer=.2:.5:.3:0:.3:.6:.1:0:.2:.4:.6", "-c:v", "libx264",
       os.path.join(clips, "clipD.mp4"))
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (1920, 1080), (13, 21, 32)); d = ImageDraw.Draw(im)
    for i in range(0, 1920, 60):
        d.line([(i, 0), (i + 400, 1080)], fill=(30 + i // 30, 90, 140), width=3)
    d.ellipse([760, 340, 1160, 740], outline=(240, 190, 80), width=12)
    im.save(os.path.join(clips, "still.png"))

    shots = {
        "title": "Fun, Fun, Fun", "artist": "Grobie (A Grok AI bot)", "album": "SLOPCORE TV",
        "clips_dir": "clips",
        "title_card": {"text": "GROBIE — Fun, Fun, Fun", "subtitle": "WARP978", "start_sec": 0.4, "end_sec": 3.9},
        "end_card": {"text": "GROBIE · MAIN TEAMMATE · A Grok AI bot", "subtitle": "SLOPCORE TV", "glyph": "☯"},
        "shots": [
            {"id": "t01", "file": "clipA.mp4", "start_bar": 1, "end_bar": 2, "fit": "trim", "in_offset": 0.5, "transition": "cut", "grade": "default"},
            {"id": "t02", "file": "still.png", "start_bar": 3, "end_bar": 4, "fit": "ken_burns", "transition": "crossfade", "transition_dur": 0.5,
             "grade": "default", "ken_burns": {"zoom_from": 1.0, "zoom_to": 1.15, "pan": "right"}},
            {"id": "t03", "file": "clipB.mp4", "start_bar": 5, "end_bar": 6, "fit": "stretch", "transition": "flash", "transition_dur": 0.35,
             "grade": "default", "overlay_text": "HOLD", "overlay_style": "hit", "overlay_color": "#ECF4FA", "overlay_dur": 1.4},
            {"id": "t04", "file": "clipC.mp4", "start_sec": 12.0, "end_sec": 16.0, "fit": "loop", "transition": "cut", "grade": "shadow_fault"},
        ],
    }
    sl = os.path.join(out_dir, "dryrun-shot-list.json")
    json.dump(shots, open(sl, "w"), indent=1, ensure_ascii=False)
    out1 = os.path.join(out_dir, "dryrun-test-16s.mp4")
    subprocess.run([sys.executable, os.path.join(HERE, "assemble_mv.py"),
                    "--shot-list", sl, "--audio", audio, "--beat-grid", gridp,
                    "--output", out1, "--audio-start", "0", "--duration", "16"], check=True)

    # Second run uses only the first 8 s of the same sources so a generated 16 s tone is enough.
    shots2 = dict(shots, title_card=None, end_card=None, flashes=[{"time_sec": 6.0, "dur": 0.4}], shots=[
        {"id": "d01", "file": "clipD.mp4", "start_sec": 0.0, "end_sec": 4.0, "fit": "trim", "grade": "storm"},
        {"id": "d02", "file": "clipA.mp4", "start_sec": 4.0, "end_sec": 8.0, "fit": "trim", "transition": "flash", "grade": "gold_blaze",
         "overlay_text": "WARP978", "overlay_style": "hit"},
    ])
    sl2 = os.path.join(out_dir, "dryrun-shot-list-1080p.json")
    json.dump(shots2, open(sl2, "w"), indent=1, ensure_ascii=False)
    out2 = os.path.join(out_dir, "dryrun-test-1080p.mp4")
    subprocess.run([sys.executable, os.path.join(HERE, "assemble_mv.py"),
                    "--shot-list", sl2, "--audio", audio, "--beat-grid", gridp,
                    "--output", out2, "--audio-start", "0", "--duration", "8",
                    "--resolution", "1080p", "--fps", "30"], check=True)

    ok = True
    report = {}
    for f, W, H, fps, dur in ((out1, 1280, 720, "24/1", 16.0), (out2, 1920, 1080, "30/1", 8.0)):
        p = probe(f)
        v = [s for s in p["streams"] if s["codec_type"] == "video"][0]
        astream = [s for s in p["streams"] if s["codec_type"] == "audio"][0]
        at = atoms(f)
        fs = int(v["nb_frames"])
        r = {
            "video": f"{v['codec_name']} {v.get('profile')} L{v.get('level')} {v['width']}x{v['height']} {v['pix_fmt']} {v['r_frame_rate']} frames={fs}",
            "audio": f"{astream['codec_name']} {astream['sample_rate']}Hz ch={astream['channels']} {int(astream.get('bit_rate', 0)) // 1000}k",
            "duration": p["format"]["duration"],
            "atoms": at,
            "faststart": at.index("moov") < at.index("mdat"),
            "title": p["format"].get("tags", {}).get("title"),
        }
        checks = [
            v["codec_name"] == "h264", v.get("profile") == "High",
            v["width"] == W, v["height"] == H, v["pix_fmt"] == "yuv420p",
            v["r_frame_rate"] == fps, astream["codec_name"] == "aac",
            astream["sample_rate"] == "48000", astream["channels"] == 2,
            abs(float(p["format"]["duration"]) - dur) < 0.05,
            fs == round(dur * eval(fps)), r["faststart"], r["title"] == "Fun, Fun, Fun",
        ]
        r["pass"] = all(checks)
        ok &= r["pass"]
        report[os.path.basename(f)] = r
    print(json.dumps(report, indent=1))
    print("DRY-RUN", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
