#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 INTENSE FINANCE, LLC / SLOPCORE TV. Released under the MIT License.
"""Assemble the 4:12 Director's Cut v2 in a single final H.264 pass for lip-sync close-ups.

Non-close-up shots may be rendered to crf-10 intermediates (grades, fits). Lip-sync
close-up pixels are trimmed into a lossless FFV1 CFR intermediate (no scale, crop,
grade, warp, or retime) so FFmpeg 7 xfade sees a real frame rate; the only H.264
encode of those pixels is the final export. Source frame 0 of each close-up file
is its locked timeline origin (a=160, b=174, c=188).
"""
import argparse, json, os, sys, tempfile, hashlib, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble_mv as am

CU_MD5 = {
    "closeup-a-lipsync-v4-silent.mp4": "5c1f7d2ccde47e824d920994d86f7ce5",
    "closeup-b-lipsync-v4-silent.mp4": "ba840bfcd646dde61f557a67f6f2afda",
    "closeup-c-lipsync-v4-silent.mp4": "22391b4ba377408d0319e6bee6751480",
}
CU_ORIGIN = {
    "closeup-a-lipsync-v4-silent.mp4": 160.0,
    "closeup-b-lipsync-v4-silent.mp4": 174.0,
    "closeup-c-lipsync-v4-silent.mp4": 188.0,
}
AUDIO_MD5 = "f90b5cdf64a5772b67466365e22014c6"

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def is_cu(s):
    return s.get("encode") == "final-pass-only" or ("closeup" in (s.get("file") or "") and s.get("grade") == "none")

def basename(s):
    return os.path.basename(s.get("file") or s.get("_file") or "")

def render_cu_lossless(s, tmp, idx, fps):
    """Trim exact frames from the silent CU file into a lossless CFR FFV1 AVI.
    Pixels are identical to the source; this is not an H.264 encode."""
    out = os.path.join(tmp, "cu%03d.avi" % idx)
    a0 = s["_cu_start_frame"]
    n = s["_cu_nframes"]
    a1 = a0 + n
    cmd = [
        "ffmpeg", "-hide_banner", "-y", "-loglevel", "error",
        "-i", s["_file"], "-an",
        "-vf", "trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS,format=yuv420p" % (a0, a1),
        "-frames:v", str(n), "-r", str(fps), "-fps_mode", "cfr",
        "-c:v", "ffv1", "-pix_fmt", "yuv420p",
        out,
    ]
    am.run(cmd)
    return out

def main():
    ap = argparse.ArgumentParser(description="Assemble the 4:12 Director's Cut v2 (single final H.264 pass for lip-sync close-ups).")
    ap.add_argument("--shot-list", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--beat-grid", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()

    sl = json.load(open(args.shot_list))
    grid = json.load(open(args.beat_grid))
    slbase = os.path.dirname(os.path.abspath(args.shot_list))
    base = os.path.join(slbase, sl.get("clips_dir", ""))
    W, H, fps = 1280, 720, 24
    T0, D, F = 0.0, 252.0, 6048
    shots = am.resolve_shots(sl, grid, base)
    for s in shots:
        s["_fa"] = max(0, int(round((s["_a"] - T0) * fps)))
        s["_fb"] = min(F, int(round((s["_b"] - T0) * fps)))
    shots[0]["_fa"] = 0
    shots[-1]["_fb"] = F
    for i in range(1, len(shots)):
        shots[i]["_fa"] = shots[i - 1]["_fb"]
    shots = [s for s in shots if s["_fb"] > s["_fa"]]

    seen_md5 = {}
    for i, s in enumerate(shots):
        if i == 0 and s.get("transition") in ("crossfade",):
            s["transition"] = "cut"
        nxt = shots[i + 1] if i + 1 < len(shots) else None
        s["_xf_out"] = int(round(float(nxt.get("transition_dur", 0.35)) * fps)) if nxt and nxt.get("transition") == "crossfade" else 0
        s["_dip_out"] = 0
        s["_is_cu"] = is_cu(s)
        if s["_is_cu"]:
            bn = basename(s)
            if bn not in CU_MD5:
                raise SystemExit("unknown CU file %s" % bn)
            origin = CU_ORIGIN[bn]
            expected = (s["_fa"] / fps + T0) - origin
            got = float(s.get("in_offset", 0.0))
            if abs(expected - got) > 1e-6:
                raise SystemExit("CU %s in_offset %.6f != timeline-origin %.6f (fa=%d origin=%.3f)" % (s["id"], got, expected, s["_fa"], origin))
            f = s["_file"]
            if f not in seen_md5:
                h = md5(f)
                if h != CU_MD5[bn]:
                    raise SystemExit("md5 mismatch for %s: got %s want %s" % (f, h, CU_MD5[bn]))
                seen_md5[f] = h
                print("verified %s md5 %s" % (bn, h), flush=True)
            s["_cu_start_frame"] = int(round(got * fps))
            s["_cu_nframes"] = s["_fb"] - s["_fa"]
            if s["_cu_start_frame"] < 0 or s["_cu_start_frame"] + s["_cu_nframes"] > 337:
                raise SystemExit("CU %s frames %d+%d exceed 337" % (s["id"], s["_cu_start_frame"], s["_cu_nframes"]))
            if s["_xf_out"]:
                raise SystemExit("CU shot %s has outgoing crossfade; not allowed (would need extra CU frames / a filter on CU pixels)" % s["id"])

    audio_md5 = md5(args.audio)
    if audio_md5 != AUDIO_MD5:
        raise SystemExit("audio md5 mismatch: %s" % audio_md5)
    print("verified audio md5 %s" % audio_md5, flush=True)

    tmp = tempfile.mkdtemp(prefix="grobie-dc-v2-")
    print("temp", tmp, flush=True)
    ok = False
    try:
        segs = []
        for i, s in enumerate(shots):
            fr = s["_fb"] - s["_fa"]
            if s["_is_cu"]:
                segs.append(render_cu_lossless(s, tmp, i, fps))
                print("shot %-22s %7.3f-%7.3f s  %4d fr  CU lossless-trim file_fr %d-%d  grade=none" % (
                    s["id"], s["_fa"] / fps + T0, s["_fb"] / fps + T0, fr,
                    s["_cu_start_frame"], s["_cu_start_frame"] + s["_cu_nframes"]), flush=True)
            else:
                segs.append(am.render_shot(s, fr, s["_xf_out"], W, H, fps, True, tmp, i))
                print("shot %-22s %7.3f-%7.3f s  %4d fr  fit=%-9s tr=%-9s grade=%s" % (
                    s["id"], s["_fa"] / fps + T0, s["_fb"] / fps + T0, fr,
                    s.get("fit", "trim"), s.get("transition", "cut"), s.get("grade", "default")), flush=True)

        title = sl.get("title", "Fun, Fun, Fun")
        cards = []
        tc = sl.get("title_card")
        if tc:
            cards.append(("title", tc.get("text", "GROBIE — %s" % title), tc.get("subtitle"), None, tc.get("color"),
                          float(tc.get("start_sec", 0.6)), float(tc.get("end_sec", 5.8))))
        ec = sl.get("end_card")
        if ec:
            cards.append(("end", ec.get("text"), ec.get("subtitle", "SLOPCORE TV"), ec.get("glyph", "☯"), ec.get("color"),
                          float(ec.get("start_sec", 249.5)), float(ec.get("end_sec", 252.0))))
        for s in shots:
            if s.get("overlay_text"):
                st = s["_fa"] / fps + T0 + float(s.get("overlay_start", 0.0))
                cards.append((s.get("overlay_style", "hit"), s["overlay_text"], s.get("overlay_sub"), None, s.get("overlay_color"),
                              st, st + float(s.get("overlay_dur", 1.6))))

        # Join CFR intermediates raw (no pre-filter). settb after each join so
        # the next xfade sees a matching timebase. FFmpeg 7.1: fps=/setpts= on
        # an input before xfade zeros the reported rate (1/0) and breaks xfade.
        inputs = []
        for p in segs:
            inputs += ["-i", p]
        fc = []
        n = len(segs)
        prev = "[0:v]"
        for i in range(1, n):
            s = shots[i]
            lab = "[v%d]" % i
            if s.get("transition") == "crossfade" and shots[i - 1]["_xf_out"]:
                fc.append("%s[%d:v]xfade=transition=fade:duration=%.4f:offset=%.4f,settb=1/%d%s" % (
                    prev, i, shots[i - 1]["_xf_out"] / fps, s["_fa"] / fps, fps, lab))
            else:
                fc.append("%s[%d:v]concat=n=2:v=1:a=0,settb=1/%d%s" % (prev, i, fps, lab))
            prev = lab

        ci = n
        for k, (style, text, sub, glyph, color, ca, cb) in enumerate(cards):
            ca, cb = max(ca, T0), min(cb, T0 + D)
            if cb - ca < 0.1:
                continue
            png = os.path.join(tmp, "card%02d.png" % k)
            am.render_card(text, sub, style, W, H, png, glyph=glyph, color=color)
            d = cb - ca
            fi = 0.08 if style == "hit" else 0.45
            fo = 0.35 if style == "hit" else 0.5
            if style == "end" and abs(cb - (T0 + D)) < 1e-3:
                fo = 0.0001
            inputs += ["-loop", "1", "-framerate", str(fps), "-t", "%.4f" % d, "-i", png]
            fc.append("[%d:v]format=rgba,fade=t=in:st=0:d=%.3f:alpha=1,fade=t=out:st=%.3f:d=%.3f:alpha=1,setpts=PTS-STARTPTS+%.4f/TB[c%d]"
                      % (ci, fi, max(0, d - fo), fo, ca - T0, k))
            fc.append("%s[c%d]overlay=0:0:eof_action=pass:enable='between(t,%.4f,%.4f)'[o%d]" % (prev, k, ca - T0, cb - T0, k))
            prev = "[o%d]" % k
            ci += 1

        for k, fl in enumerate(sl.get("flashes", [])):
            ft, fd = float(fl["time_sec"]), float(fl.get("dur", 0.45))
            if not (T0 <= ft < T0 + D):
                continue
            fd = min(fd, T0 + D - ft)
            inputs += ["-f", "lavfi", "-i", "color=c=%s:s=%dx%d:r=%d:d=%.4f" % (fl.get("color", "white"), W, H, fps, fd)]
            fc.append("[%d:v]format=rgba,fade=t=out:st=0:d=%.4f:alpha=1,setpts=PTS-STARTPTS+%.4f/TB[f%d]" % (ci, fd, ft - T0, k))
            fc.append("%s[f%d]overlay=0:0:eof_action=pass:enable='between(t,%.4f,%.4f)'[fo%d]" % (prev, k, ft - T0, ft - T0 + fd, k))
            prev = "[fo%d]" % k
            ci += 1

        fc.append("%sformat=yuv420p,setsar=1[vout]" % prev)
        inputs += ["-ss", "0", "-t", "%.4f" % D, "-i", args.audio]
        af = "[%d:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:%.4f,asetpts=PTS-STARTPTS,apad=whole_dur=%.4f[aout]" % (ci, D, D)

        out = args.output
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        graph_path = os.path.join(tmp, "filter_complex.txt")
        with open(graph_path, "w") as gf:
            gf.write(";\n".join(fc + [af]))
        # also copy graph next to the output for debug
        dbg = os.path.splitext(os.path.abspath(out))[0] + ".filtergraph.txt"
        shutil.copy(graph_path, dbg)

        cmd = ["ffmpeg", "-hide_banner", "-y", "-loglevel", "error"] + inputs + [
            "-filter_complex_script", graph_path,
            "-map", "[vout]", "-map", "[aout]",
            "-frames:v", str(F), "-r", str(fps),
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-crf", str(args.crf), "-preset", "medium", "-g", str(fps * 2),
            "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart",
            "-metadata", "title=Fun, Fun, Fun",
            "-metadata", "artist=Grobie (A Grok AI bot)",
            "-metadata", "album=SLOPCORE TV",
            "-metadata", "comment=Fun, Fun, Fun (The Director's Cut), 4:12 v2 — INTENSE FINANCE, LLC / SLOPCORE TV",
            out,
        ]
        print("ffmpeg final pass (%d inputs, %d filter steps)..." % (sum(1 for x in inputs if x == "-i"), len(fc)), flush=True)
        am.run(cmd, quiet=True)
        print("wrote %s" % out, flush=True)
        ok = True
    finally:
        if ok and not args.keep_temp:
            shutil.rmtree(tmp, ignore_errors=True)
        elif not ok:
            print("FAILED; temp kept at %s" % tmp, flush=True)

if __name__ == "__main__":
    main()
