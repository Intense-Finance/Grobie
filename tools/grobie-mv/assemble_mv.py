#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# assemble_mv.py - grobie-mv beat-locked music-video assembly & mastering tool.
# Copyright (c) 2026 INTENSE FINANCE, LLC / SLOPCORE TV. Released under the MIT License.
# Needs: ffmpeg/ffprobe (LGPL/GPL build), Python 3.9+, Pillow (MIT-CMU), fontTools (MIT, optional).
"""
Assemble a 16:9 music video from a JSON shot list + a mastered audio file + beat-grid.json.

  assemble_mv.py --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output out.mp4
                 [--resolution 720p|1080p] [--fps 24|30] [--no-grade] [--no-title-cards]
                 [--audio-start SEC] [--duration SEC] [--crf 18] [--title "Fun, Fun, Fun"] [--keep-temp]

Shot list schema (JSON):
{
  "title": "Fun, Fun, Fun",                     # MP4 title metadata + default title-card text
  "artist": "Grobie (A Grok AI bot)", "album": "SLOPCORE TV",
  "output": "video.mp4",                        # used when --output is omitted (relative to the shot list)
  "clips_dir": "clips",                         # base dir for relative shot files (relative to the shot list)
  "title_card": {"text": "GROBIE — Fun, Fun, Fun", "subtitle": "WARP978", "start_sec": 0.5, "end_sec": 6.0},
  "flashes": [{"time_sec": 210.0, "dur": 0.45}],   # optional global white jump flashes (any time, not only at cuts)
  "end_card":   {"text": "GROBIE · MAIN TEAMMATE · A Grok AI bot", "subtitle": "SLOPCORE TV", "glyph": "☯",
                 "start_sec": 222.0, "end_sec": 224.0},          # default = last 2.0 s of the output window
  "shots": [ { "id": "s01", "file": "s01.mp4",
               "start_bar": 1, "end_bar": 4,                     # inclusive bars from beat-grid; or start_sec/end_sec
               "fit": "trim|stretch|loop|ken_burns", "in_offset": 0.0,
               "transition": "cut|crossfade|flash|dip_black", "transition_dur": 0.35,   # transition INTO this shot
               "grade": "default|shadow_fault|gold_blaze|storm|none",
               "overlay_text": "WARP978", "overlay_style": "hit|title|lower", "overlay_start": 0.0, "overlay_dur": 1.6,
               "ken_burns": {"zoom_from": 1.0, "zoom_to": 1.12, "pan": "center|left|right|up|down"} } ]
}
Every shot boundary is snapped to the frame grid (round(sec*fps)), so the picture never drifts from the audio.
"""
import argparse, json, math, os, shutil, struct, subprocess, sys, tempfile

GRADES = {
    # dark steel #0D1520 blacks, cool cyan shadows, warm amber highlights
    "default": "curves=r='0/0.051 0.5/0.49 1/1':g='0/0.082 0.5/0.5 1/1':b='0/0.125 0.5/0.52 1/0.98',"
               "colorbalance=rs=-0.04:bs=0.06:rh=0.06:gh=0.02:bh=-0.05,eq=contrast=1.06:saturation=1.05,vignette=angle=PI/5",
    "shadow_fault": "eq=brightness=-0.04:contrast=1.12:saturation=0.42,"
                    "curves=r='0/0.04 1/0.9':g='0/0.07 1/0.95':b='0/0.12 1/1',colorbalance=bs=0.10:bm=0.05:rh=-0.02,vignette=angle=PI/4",
    "gold_blaze": "curves=r='0/0.05 0.5/0.55 1/1':g='0/0.07 0.5/0.51 1/0.97':b='0/0.1 0.5/0.44 1/0.88',"
                  "colorbalance=rm=0.05:bm=-0.05:rh=0.10:gh=0.05:bh=-0.08,eq=contrast=1.08:saturation=1.2,vignette=angle=PI/5",
    "storm": "eq=brightness=-0.03:contrast=1.25:saturation=0.7,curves=b='0/0.12 1/1':g='0/0.07 1/1',"
             "colorbalance=bs=0.08:bm=0.04:bh=0.03,unsharp=5:5:0.6,vignette=angle=PI/4",
    "none": "",
}
FONT_DIRS = ["/usr/share/fonts/truetype/sand-box/google", "/usr/share/fonts/truetype", "/usr/share/fonts", os.path.expanduser("~/.fonts")]
RES = {"720p": (1280, 720), "1080p": (1920, 1080)}
VEXT = (".mp4", ".mov", ".webm", ".mkv", ".m4v"); IEXT = (".jpg", ".jpeg", ".png", ".webp")

def run(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.stderr.write(r.stderr[-3000:]); raise SystemExit("ffmpeg failed: " + " ".join(cmd[:8]) + " ...")
    return r
def probe_dur(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return 0.0

def find_font(names):
    for d in FONT_DIRS:
        for root, _, files in os.walk(d):
            for n in names:
                if n in files: return os.path.join(root, n)
    return None

def has_glyph(path, ch):
    try:
        from fontTools.ttLib import TTFont
        return ord(ch) in TTFont(path, lazy=True, fontNumber=0).getBestCmap()
    except Exception: return True

def render_card(text, sub, style, W, H, out, glyph=None, color=None):
    """Transparent PNG card with tracked type, soft drop shadow and glyph fallback."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    s = W / 1280.0
    bold = find_font(["Rajdhani-Bold.ttf", "Inter-Bold.ttf", "DejaVuSans-Bold.ttf"])
    med = find_font(["Rajdhani-SemiBold.ttf", "Rajdhani-Medium.ttf", "DejaVuSans.ttf"])
    fb = find_font(["DejaVuSans-Bold.ttf", "DejaVuSans.ttf"])
    sizes = {"title": (int(84 * s), int(30 * s), 0.06), "hit": (int(170 * s), int(34 * s), 0.04), "end": (int(46 * s), int(64 * s), 0.12),
             "lower": (int(40 * s), int(24 * s), 0.05)}
    big, small, track = sizes.get(style, sizes["title"])
    col = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) if color else ({"hit": (240, 190, 80)}.get(style, (236, 244, 250)))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if style == "end":  # dark steel backdrop band
        band = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
        for y in range(H):
            a = int(205 * max(0.0, 1 - abs(y - H * 0.5) / (H * 0.42)) ** 0.6); bd.line([(0, y), (W, y)], fill=(13, 21, 32, a))
        img = Image.alpha_composite(img, band); d = ImageDraw.Draw(img)
    def line_img(txt, size, fontpath, trk, fill):
        f = ImageFont.truetype(fontpath, size); ff = ImageFont.truetype(fb, size) if fb else f
        chars = [(ch, f if has_glyph(fontpath, ch) else ff) for ch in txt]
        widths = [fo.getlength(ch) for ch, fo in chars]; tw = sum(widths) + trk * size * max(0, len(chars) - 1)
        asc, desc = f.getmetrics(); li = Image.new("RGBA", (int(tw) + 8, asc + desc + 8), (0, 0, 0, 0)); ld = ImageDraw.Draw(li); x = 4
        for (ch, fo), w in zip(chars, widths): ld.text((x, 4), ch, font=fo, fill=fill); x += w + trk * size
        # Auto-scale any over-wide hit/title line to stay inside 1160px at 1280-wide
        # (and the equivalent margin at other resolutions).
        max_w = int(round(1160 * s))
        if li.width > max_w:
            new_h = max(1, int(round(li.height * (max_w / li.width))))
            li = li.resize((max_w, new_h), Image.Resampling.LANCZOS)
        return li
    lines = []
    if style == "end":
        lines.append(line_img(text, big, med, track * 0.5, col + (255,)))
        if glyph: lines.append(line_img(glyph, int(big * 1.3), fb or med, 0, (240, 190, 80, 255)))
        if sub: lines.append(line_img(sub, small, bold, track, (96, 220, 236, 255)))
    else:
        lines.append(line_img(text, big, bold, track, col + (255,)))
        if sub: lines.append(line_img(sub, small, med, 0.25, (96, 220, 236, 235)))
    gap = int(14 * s); th = sum(l.height for l in lines) + gap * (len(lines) - 1)
    y = {"lower": int(H * 0.80) - th // 2}.get(style, (H - th) // 2)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for l in lines: layer.alpha_composite(l, ((W - l.width) // 2, y)); y += l.height + gap
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(layer.getchannel("A").point(lambda v: int(v * 0.75)))
    sh = sh.filter(ImageFilter.GaussianBlur(int(6 * s) + 1)); img.alpha_composite(sh, (int(3 * s), int(4 * s)))
    if style in ("title", "hit"):
        glow = layer.filter(ImageFilter.GaussianBlur(int(10 * s) + 1)); glow.putalpha(glow.getchannel("A").point(lambda v: int(v * 0.35)))
        img.alpha_composite(glow)
    img.alpha_composite(layer)
    if style == "title":  # thin cyan rule under the title
        d = ImageDraw.Draw(img); cy = (H + th) // 2 + int(18 * s); d.line([(W // 2 - int(160 * s), cy), (W // 2 + int(160 * s), cy)], fill=(96, 220, 236, 200), width=max(1, int(2 * s)))
    img.save(out)

def resolve_shots(sl, grid, base):
    bar = float(grid.get("bar_sec", 2.0)); shots = []
    for i, s in enumerate(sl["shots"]):
        if "start_sec" in s: a = float(s["start_sec"])
        elif "start_bar" in s: a = (float(s["start_bar"]) - 1) * bar
        else: raise SystemExit("shot %s needs start_bar or start_sec" % s.get("id", i))
        if "end_sec" in s: b = float(s["end_sec"])
        elif "end_bar" in s: b = float(s["end_bar"]) * bar
        else: b = None
        f = s.get("file")
        if f and not os.path.isabs(f): f = os.path.join(base, f)
        shots.append(dict(s, _a=a, _b=b, _file=f, id=s.get("id", "s%02d" % (i + 1))))
    shots.sort(key=lambda s: s["_a"])
    for i, s in enumerate(shots):
        if s["_b"] is None: s["_b"] = shots[i + 1]["_a"] if i + 1 < len(shots) else float(grid["duration_sec"])
    return shots

def kb_expr(kb, frames, W, H):
    z0, z1 = float(kb.get("zoom_from", 1.0)), float(kb.get("zoom_to", 1.12)); n = max(1, frames - 1)
    z = "(%f+(%f)*on/%d)" % (z0, z1 - z0, n)
    pan = kb.get("pan", "center"); p = "on/%d" % n
    x = {"left": "(iw-iw/zoom)*(1-%s)" % p, "right": "(iw-iw/zoom)*%s" % p}.get(pan, "(iw-iw/zoom)/2")
    y = {"up": "(ih-ih/zoom)*(1-%s)" % p, "down": "(ih-ih/zoom)*%s" % p}.get(pan, "(ih-ih/zoom)/2")
    return "zoompan=z='%s':x='%s':y='%s':d=%d:s=%dx%d:fps=%s" % (z, x, y, frames, W, H, "{fps}")

def render_shot(s, frames, pre_extra, W, H, fps, grade_on, tmp, idx):
    """Render one shot to an intermediate (exact frame count). pre_extra: extra tail frames for an outgoing crossfade."""
    total = frames + pre_extra; dur = total / fps; out = os.path.join(tmp, "seg%03d.mp4" % idx)
    f = s["_file"]; fit = s.get("fit", "trim"); off = float(s.get("in_offset", 0.0))
    norm = "scale=%d:%d:force_original_aspect_ratio=increase:flags=lanczos,crop=%d:%d,setsar=1" % (W, H, W, H)
    g = GRADES.get(s.get("grade", "default"), GRADES["default"]) if grade_on else ""
    tr, td = s.get("transition", "cut"), float(s.get("transition_dur", 0.35))
    fx = []
    if tr == "flash": fx.append("fade=t=in:st=0:d=%.3f:color=white" % max(td, 0.12))
    if tr == "dip_black": fx.append("fade=t=in:st=0:d=%.3f" % (td / 2))
    if s.get("_dip_out"): fx.append("fade=t=out:st=%.3f:d=%.3f" % (frames / fps - s["_dip_out"] / 2, s["_dip_out"] / 2))
    post = ",".join([x for x in ([g] + fx) if x])
    cmd = ["ffmpeg", "-hide_banner", "-y", "-loglevel", "error"]
    if f is None or not os.path.exists(f):
        if f: sys.stderr.write("warning: missing %s for shot %s, using dark steel slate\n" % (f, s["id"]))
        cmd += ["-f", "lavfi", "-i", "color=c=0x0D1520:s=%dx%d:r=%s:d=%.4f" % (W, H, fps, dur + 1)]; vf = "fps=%s" % fps
    elif f.lower().endswith(IEXT) or fit == "ken_burns" and not f.lower().endswith(VEXT):
        kb = s.get("ken_burns", {})
        cmd += ["-loop", "1", "-framerate", str(fps), "-i", f]
        vf = "scale=%d:%d:force_original_aspect_ratio=increase:flags=lanczos,crop=%d:%d,setsar=1,%s" % (W * 4, H * 4, W * 4, H * 4, kb_expr(kb, total, W, H).replace("{fps}", str(fps)))
    else:
        src = probe_dur(f); avail = max(0.04, src - off)
        if fit == "loop": cmd += ["-stream_loop", "-1"]
        cmd += ["-ss", "%.3f" % off, "-i", f]
        if fit == "stretch": vf = "setpts=%.6f*(PTS-STARTPTS),fps=%s,%s" % (dur / avail, fps, norm)
        else: vf = "setpts=PTS-STARTPTS,fps=%s,%s,tpad=stop_mode=clone:stop_duration=%.3f" % (fps, norm, dur + 1)
        if fit == "ken_burns":  # slow push on moving footage
            vf += ",scale=%d:%d,%s" % (W * 2, H * 2, kb_expr(s.get("ken_burns", {}), total, W, H).replace("{fps}", str(fps)).replace(":d=%d" % total, ":d=1"))
    vf = vf + ",format=yuv420p" + ("," + post if post else "") + ",format=yuv420p"
    cmd += ["-an", "-vf", vf, "-frames:v", str(total), "-r", str(fps), "-fps_mode", "cfr", "-c:v", "libx264", "-preset", "veryfast", "-crf", "10",
            "-pix_fmt", "yuv420p", "-video_track_timescale", str(int(fps)), out]
    run(cmd); return out

def main():
    ap = argparse.ArgumentParser(description="grobie-mv: beat-locked music-video assembly & mastering", formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--shot-list", required=True); ap.add_argument("--audio", required=True); ap.add_argument("--beat-grid", required=True)
    ap.add_argument("--output"); ap.add_argument("--resolution", choices=list(RES), default="720p"); ap.add_argument("--fps", type=int, choices=[24, 25, 30], default=24)
    ap.add_argument("--grade", dest="grade", action="store_true", default=True); ap.add_argument("--no-grade", dest="grade", action="store_false")
    ap.add_argument("--title-cards", dest="cards", action="store_true", default=True); ap.add_argument("--no-title-cards", dest="cards", action="store_false")
    ap.add_argument("--audio-start", type=float, default=0.0); ap.add_argument("--duration", type=float)
    ap.add_argument("--crf", type=int, default=18); ap.add_argument("--title"); ap.add_argument("--artist"); ap.add_argument("--album")
    ap.add_argument("--keep-temp", action="store_true")
    a = ap.parse_args()
    for t in ("ffmpeg", "ffprobe"):
        if not shutil.which(t): raise SystemExit("%s not found on PATH" % t)
    sl = json.load(open(a.shot_list)); grid = json.load(open(a.beat_grid)); slbase = os.path.dirname(os.path.abspath(a.shot_list))
    base = os.path.join(slbase, sl.get("clips_dir", "")) if sl.get("clips_dir") else slbase
    out = a.output or (os.path.join(slbase, sl["output"]) if sl.get("output") else None)
    if not out: raise SystemExit("give --output or an 'output' field in the shot list")
    title = a.title or sl.get("title", "Fun, Fun, Fun"); artist = a.artist or sl.get("artist", "Grobie (A Grok AI bot)"); album = a.album or sl.get("album", "SLOPCORE TV")
    W, H = RES[a.resolution]; fps = a.fps
    adur = probe_dur(a.audio); full = float(grid.get("duration_sec", adur))
    T0 = a.audio_start; D = a.duration if a.duration else min(full, adur) - T0
    if D <= 0: raise SystemExit("empty output window")
    F = int(round(D * fps)); D = F / fps
    shots = [s for s in resolve_shots(sl, grid, base) if s["_b"] > T0 + 1e-6 and s["_a"] < T0 + D - 1e-6]
    if not shots: raise SystemExit("no shots inside the output window")
    # frame-snap every boundary inside the window
    for s in shots:
        s["_fa"] = max(0, int(round((s["_a"] - T0) * fps))); s["_fb"] = min(F, int(round((s["_b"] - T0) * fps)))
    shots[0]["_fa"] = 0; shots[-1]["_fb"] = F
    for i in range(1, len(shots)): shots[i]["_fa"] = shots[i - 1]["_fb"]
    shots = [s for s in shots if s["_fb"] > s["_fa"]]
    for i, s in enumerate(shots):
        if i == 0 and s.get("transition") in ("crossfade",): s["transition"] = "cut"
        nxt = shots[i + 1] if i + 1 < len(shots) else None
        s["_xf_out"] = int(round(float(nxt.get("transition_dur", 0.35)) * fps)) if nxt and nxt.get("transition") == "crossfade" else 0
        s["_dip_out"] = float(nxt.get("transition_dur", 0.35)) if nxt and nxt.get("transition") == "dip_black" else 0
    tmp = tempfile.mkdtemp(prefix="grobie-mv-")
    try:
        segs = []
        for i, s in enumerate(shots):
            fr = s["_fb"] - s["_fa"]
            segs.append(render_shot(s, fr, s["_xf_out"], W, H, fps, a.grade, tmp, i))
            print("shot %-6s %7.3f-%7.3f s  %4d fr  fit=%-9s tr=%-9s grade=%s" % (s["id"], s["_fa"] / fps + T0, s["_fb"] / fps + T0, fr, s.get("fit", "trim"),
                  s.get("transition", "cut"), s.get("grade", "default") if a.grade else "off"), flush=True)
        # cards & overlays
        cards = []
        if a.cards:
            tc = sl.get("title_card", {"text": "GROBIE — %s" % title})
            if tc:
                cards.append(("title", tc.get("text", "GROBIE — %s" % title), tc.get("subtitle"), None, tc.get("color"),
                              float(tc.get("start_sec", T0 + 0.5)), float(tc.get("end_sec", T0 + min(5.5, D * 0.35)))))
            ec = sl.get("end_card", {"text": "GROBIE · MAIN TEAMMATE · A Grok AI bot", "subtitle": "SLOPCORE TV", "glyph": "☯"})
            if ec:
                ea, eb = float(ec.get("start_sec", T0 + D - 2.0)), float(ec.get("end_sec", T0 + D))
                if ea >= T0 + D - 0.2 or ea < T0: ea, eb = T0 + D - 2.0, T0 + D  # previews: show the end card in the last 2 s
                cards.append(("end", ec.get("text"), ec.get("subtitle", "SLOPCORE TV"), ec.get("glyph", "☯"), ec.get("color"), ea, eb))
        for s in shots:
            if s.get("overlay_text"):
                st = s["_fa"] / fps + T0 + float(s.get("overlay_start", 0.0))
                cards.append((s.get("overlay_style", "hit"), s["overlay_text"], s.get("overlay_sub"), None, s.get("overlay_color"),
                              st, st + float(s.get("overlay_dur", min(1.6, (s["_fb"] - s["_fa"]) / fps)))))
        inputs = []; fc = []
        for p in segs: inputs += ["-i", p]
        n = len(segs)
        # FFmpeg 7.1 xfade requires matching timebases AND a real constant
        # frame rate. Pre-filters like fps=/setpts= zero the frame rate (1/0)
        # and break xfade. Join the CFR intermediates raw, then settb=1/fps
        # after every join so the next xfade sees a matching timebase.
        prev = "[0:v]"; acc_len = (shots[0]["_fb"] - shots[0]["_fa"]) / fps
        for i in range(1, n):
            s = shots[i]; lab = "[v%d]" % i
            if s.get("transition") == "crossfade" and shots[i - 1]["_xf_out"]:
                fc.append("%s[%d:v]xfade=transition=fade:duration=%.4f:offset=%.4f,settb=1/%d%s" % (prev, i, shots[i - 1]["_xf_out"] / fps, s["_fa"] / fps, fps, lab))
            else:
                fc.append("%s[%d:v]concat=n=2:v=1:a=0,settb=1/%d%s" % (prev, i, fps, lab))
            prev = lab
        ci = n
        for k, (style, text, sub, glyph, color, ca, cb) in enumerate(cards):
            ca, cb = max(ca, T0), min(cb, T0 + D)
            if cb - ca < 0.1: continue
            png = os.path.join(tmp, "card%02d.png" % k); render_card(text, sub, style, W, H, png, glyph=glyph, color=color)
            d = cb - ca; fi = 0.08 if style == "hit" else 0.45; fo = 0.35 if style == "hit" else 0.5
            if style == "end" and abs(cb - (T0 + D)) < 1e-3: fo = 0.0001
            inputs += ["-loop", "1", "-framerate", str(fps), "-t", "%.4f" % d, "-i", png]
            fc.append("[%d:v]format=rgba,fade=t=in:st=0:d=%.3f:alpha=1,fade=t=out:st=%.3f:d=%.3f:alpha=1,setpts=PTS-STARTPTS+%.4f/TB[c%d]"
                      % (ci, fi, max(0, d - fo), fo, ca - T0, k))
            fc.append("%s[c%d]overlay=0:0:eof_action=pass:enable='between(t,%.4f,%.4f)'[o%d]" % (prev, k, ca - T0, cb - T0, k)); prev = "[o%d]" % k; ci += 1
        for k, fl in enumerate(sl.get("flashes", [])):  # global white jump flashes, e.g. {"time_sec": 210.0, "dur": 0.45}
            ft, fd = float(fl["time_sec"]), float(fl.get("dur", 0.45))
            if not (T0 <= ft < T0 + D): continue
            fd = min(fd, T0 + D - ft)
            inputs += ["-f", "lavfi", "-i", "color=c=%s:s=%dx%d:r=%d:d=%.4f" % (fl.get("color", "white"), W, H, fps, fd)]
            fc.append("[%d:v]format=rgba,fade=t=out:st=0:d=%.4f:alpha=1,setpts=PTS-STARTPTS+%.4f/TB[f%d]" % (ci, fd, ft - T0, k))
            fc.append("%s[f%d]overlay=0:0:eof_action=pass:enable='between(t,%.4f,%.4f)'[fo%d]" % (prev, k, ft - T0, ft - T0 + fd, k)); prev = "[fo%d]" % k; ci += 1
        fc.append("%sformat=yuv420p,setsar=1[vout]" % prev)
        inputs += ["-ss", "%.4f" % T0, "-t", "%.4f" % D, "-i", a.audio]
        fade_out = 0.0 if abs(T0 + D - full) < 0.05 else min(0.4, D * 0.05)
        af = "[%d:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:%.4f,asetpts=PTS-STARTPTS%s,apad=whole_dur=%.4f[aout]" % (
            ci, D, (",afade=t=out:st=%.4f:d=%.4f" % (D - fade_out, fade_out)) if fade_out else "", D)
        fc.append(af)
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        level = "4.1" if fps <= 30 else "4.2"
        cmd = ["ffmpeg", "-hide_banner", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
               "-frames:v", str(F), "-r", str(fps), "-c:v", "libx264", "-profile:v", "high", "-level", level, "-pix_fmt", "yuv420p",
               "-crf", str(a.crf), "-preset", "medium", "-g", str(fps * 2), "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
               "-t", "%.4f" % D, "-movflags", "+faststart", "-metadata", "title=%s" % title, "-metadata", "artist=%s" % artist,
               "-metadata", "album=%s" % album, "-metadata", "comment=INTENSE FINANCE, LLC / SLOPCORE TV", out]
        run(cmd)
        print("wrote %s  (%.3f s, %dx%d @ %d fps, %d frames)" % (out, D, W, H, fps, F))
    finally:
        if a.keep_temp: print("temp kept:", tmp)
        else: shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__": main()
