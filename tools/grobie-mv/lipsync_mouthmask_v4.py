#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# lipsync_mouthmask_v4.py - v4 of the gentle, rigid-face mouth sync for Grobie's crystal face (CPU only, no models, no weights).
# v4: head and facets are NEVER warped or stretched. Outside a local ROI every pixel is the original frame; inside it the only
# changes are the shaped mouth slit, additive amber light spill, and a pure 0-2 px rigid translate of the chin (no stretch).
# Inside the mask: a thin dark mouth slit that opens with the viseme aperture (capped, eased) plus an amber inner glow.
# The mask follows a temporally smoothed optical-flow track (position + scale only, no deformation).
"""
lipsync_mouthmask.py --clip closeup.mp4 --cues lipsync-cues-extended.json --song-start 160.0 \
    --mouth 640,421,180,55 [--ref-time 7.0] [--audio master.wav] --out out.mp4 [--silent-out out-silent.mp4]
    [--open-cap 0.10] [--track-json track.json]
--mouth  cx,cy,w,h of the closed lip seam centre / lip width / lip height on the frame at --ref-time.
--open-cap  slit height at full aperture, as a fraction of lip width (v1 crystal warp moved the jaw 0.25 x width; 0.10 = 40%).
"""
import argparse, json, math, subprocess, sys, numpy as np, cv2
# v4 width per viseme: B (EE/teeth) wider, E (AO/ER) and F (OO/UW/W) rounder + narrower
ROUND = {"B": 1.12, "C": 1.06, "D": 1.0, "E": 0.86, "F": 0.72, "G": 0.96, "H": 0.96, "A": 1.0, "X": 1.0}
TALL = {"E": 1.12, "F": 1.25}
ap = argparse.ArgumentParser(description="Rigid-face mouth-mask lip sync", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
ap.add_argument("--clip", required=True); ap.add_argument("--cues", required=True); ap.add_argument("--song-start", type=float, required=True)
ap.add_argument("--mouth", required=True); ap.add_argument("--ref-time", type=float, default=0.0); ap.add_argument("--audio")
ap.add_argument("--out", required=True); ap.add_argument("--silent-out"); ap.add_argument("--open-cap", type=float, default=0.10)
ap.add_argument("--glow", type=float, default=0.8); ap.add_argument("--dark-alpha", type=float, default=0.82); ap.add_argument("--slit-width", type=float, default=0.30)
ap.add_argument("--gamma", type=float, default=1.0, help="aperture curve (<1 lifts small vowels)"); ap.add_argument("--glow-core", type=float, default=0.55, help="glow ellipse height vs slit"); ap.add_argument("--spill", type=float, default=0.8, help="amber light spill strength"); ap.add_argument("--jaw-px", type=float, default=2.0, help="max rigid jaw translate (px)")
ap.add_argument("--smile", type=float, default=0.05, help="lip-line smile curve (fraction of width)"); ap.add_argument("--crf", type=int, default=12); ap.add_argument("--track-json")
a = ap.parse_args()
cx0, cy0, mw0, mh0 = [float(v) for v in a.mouth.split(",")]
cues = json.load(open(a.cues)); fps_c = cues["fps"]; CF = cues["frames"]
cap = cv2.VideoCapture(a.clip); fps = cap.get(cv2.CAP_PROP_FPS) or 24.0; W = int(cap.get(3)); H = int(cap.get(4))
frames = []
while True:
    ok, f = cap.read()
    if not ok: break
    frames.append(f)
n = len(frames); G = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
ri = min(n - 1, int(round(a.ref_time * fps)))

# ---------------- tracking: KLT + RANSAC similarity from the reference frame outwards, then temporal smoothing
def face_mask(shape, cx, cy, mw):
    m = np.zeros(shape, np.uint8)
    cv2.rectangle(m, (int(cx - 1.5 * mw), int(cy - 1.9 * mw)), (int(cx + 1.5 * mw), int(cy + 0.45 * mw)), 255, -1)
    cv2.ellipse(m, (int(cx), int(cy)), (int(mw * 0.6), int(mw * 0.25)), 0, 0, 360, 0, -1); return m
def propagate(order):
    cx, cy, sc = cx0, cy0, 1.0; pg = G[ri]; out = {}
    pts = cv2.goodFeaturesToTrack(pg, 400, 0.01, 6, mask=face_mask(pg.shape, cx, cy, mw0))
    for j in order:
        g = G[j]
        nx, st, _ = cv2.calcOpticalFlowPyrLK(pg, g, pts, None, winSize=(21, 21), maxLevel=3)
        bk, st2, _ = cv2.calcOpticalFlowPyrLK(g, pg, nx, None, winSize=(21, 21), maxLevel=3)
        ok = (st.ravel() == 1) & (st2.ravel() == 1) & (np.linalg.norm((bk - pts).reshape(-1, 2), axis=1) < 1.0)
        M = cv2.estimateAffinePartial2D(pts[ok], nx[ok], method=cv2.RANSAC, ransacReprojThreshold=2.0)[0] if ok.sum() >= 8 else None
        if M is not None:
            cx, cy = M[0, 0] * cx + M[0, 1] * cy + M[0, 2], M[1, 0] * cx + M[1, 1] * cy + M[1, 2]; sc *= math.hypot(M[0, 0], M[1, 0])
        out[j] = (cx, cy, sc); pg = g; pts = nx[ok].reshape(-1, 1, 2)
        if len(pts) < 120: pts = cv2.goodFeaturesToTrack(g, 400, 0.01, 6, mask=face_mask(g.shape, cx, cy, mw0 * sc))
    return out
T = np.zeros((n, 3)); T[ri] = (cx0, cy0, 1.0)
for rng in (range(ri - 1, -1, -1), range(ri + 1, n)):
    for j, v in propagate(list(rng)).items(): T[j] = v
raw = T.copy()
k = np.exp(-0.5 * (np.arange(-6, 7) / 2.5) ** 2); k /= k.sum()   # Gaussian, sigma 2.5 frames
for c in range(3):
    p = np.pad(T[:, c], 6, mode="edge"); T[:, c] = np.convolve(p, k, "valid")

# ---------------- aperture: cap, ease (2-3 frame attack/release), hard close on M/B/P
tgt = np.zeros(n); vis = []
for i in range(n):
    f = CF[min(len(CF) - 1, int(round((a.song_start + i / fps) * fps_c)))]
    v = f[2] if f[5] else "X"; vis.append(v); tgt[i] = 0.0 if v in ("A", "X") else f[3]
ape = np.zeros(n); s = 0.0
for i in range(n):
    s = s + (tgt[i] - s) * (0.5 if tgt[i] > s else 0.4)    # ~2 frame attack, ~3 frame release
    if vis[i] == "A": s = 0.0                               # bilabial closure: lips meet
    ape[i] = s if s > 0.03 else 0.0
rnd = np.array([ROUND.get(v, 1.0) for v in vis]); tal = np.array([TALL.get(v, 1.0) for v in vis])
rnd = np.convolve(np.pad(rnd, 2, mode="edge"), np.ones(5) / 5, "valid"); tal = np.convolve(np.pad(tal, 2, mode="edge"), np.ones(5) / 5, "valid")

# ---------------- render (v4: shaped slit + refracted interior + amber light spill + tiny rigid jaw cue)
cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
if a.audio: cmd += ["-ss", "%.4f" % a.song_start, "-t", "%.6f" % (n / fps), "-i", a.audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "256k"]
cmd += ["-c:v", "libx264", "-crf", str(a.crf), "-preset", "medium", "-profile:v", "high", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
enc = subprocess.Popen(cmd, stdin=subprocess.PIPE); log = []
# jaw series: smoothed + slew-limited so the rigid translate never jumps more than 0.35 px per frame (keeps lower-face wobble low)
jt = np.array([min(3.0, a.jaw_px * (ape[k] ** a.gamma if ape[k] > 0 else 0.0)) for k in range(n)])
jt = np.convolve(np.pad(jt, 3, mode="edge"), np.array([1, 2, 3, 4, 3, 2, 1]) / 16.0, "valid")
for k in range(1, n): jt[k] = jt[k - 1] + np.clip(jt[k] - jt[k - 1], -0.35, 0.35)
AMBER = np.array([60, 160, 255], np.float32); DARK = np.array([16, 10, 8], np.float32)
for i, fr in enumerate(frames):
    cx, cy, sc = T[i]; mw = mw0 * sc; o = ape[i] ** a.gamma if ape[i] > 0 else 0.0
    if o <= 0 and jt[i] <= 0.05:
        enc.stdin.write(fr.tobytes()); log.append([i, round(a.song_start + i / fps, 3), vis[i], 0.0, round(cx, 1), round(cy, 1), round(sc, 3), 0.0]); continue
    pad = int(mw * 0.95); x0, y0 = max(0, int(cx - pad)), max(0, int(cy - pad * 0.6)); x1, y1 = min(W, int(cx + pad)), min(H, int(cy + pad * 0.95))
    roi = fr[y0:y1, x0:x1].astype(np.float32); h, w = roi.shape[:2]; lx, ly = cx - x0, cy - y0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # (3) tiny rigid jaw cue: translate the region below the mouth down by <= jaw_px, through a feathered mask (no stretch)
    jaw = float(jt[i])
    if jaw > 0.05:
        sh = cv2.warpAffine(roi, np.float32([[1, 0, 0], [0, 1, jaw]]), (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        jm = (((xx - lx) / (0.62 * mw)) ** 2 + ((yy - (ly + 0.42 * mw)) / (0.52 * mw)) ** 2 <= 1).astype(np.float32) * (yy > ly + 0.03 * mw)
        jm = cv2.GaussianBlur(jm, (0, 0), 0.10 * mw)[..., None]
        roi = roi * (1 - jm) + sh * jm
    if o <= 0:
        out = fr.copy(); out[y0:y1, x0:x1] = np.clip(roi, 0, 255).astype(np.uint8)
        enc.stdin.write(out.tobytes()); log.append([i, round(a.song_start + i / fps, 3), vis[i], 0.0, round(cx, 1), round(cy, 1), round(sc, 3), round(jaw, 2)]); continue
    # (2) slit shaped to the lip line: smile curve, opening mostly downward, rounder/narrower on O/U, wider on EE
    ww = mw * a.slit_width * rnd[i]; hh = max(0.6, o * a.open_cap * mw * 0.5) * tal[i]
    u = np.linspace(-1, 1, 64); prof = (1 - u ** 2) ** (0.55 if tal[i] > 1.05 else 0.75)
    ymid = ly - a.smile * mw * (u ** 2) + jaw * 0.5; xs = lx + u * ww
    top = ymid - 0.30 * 2 * hh * prof; bot = ymid + 0.70 * 2 * hh * prof
    poly = np.concatenate([np.stack([xs, top], 1), np.stack([xs[::-1], bot[::-1]], 1)])
    slit = np.zeros((h, w), np.float32); cv2.fillPoly(slit, [np.round(poly * 8).astype(np.int32)], 1.0, cv2.LINE_AA, 3)
    slit = cv2.GaussianBlur(slit, (0, 0), max(1.0, 0.012 * mw))
    # interior: dark core + amber glow (brighter toward the centre) + faint refraction of the real facets above
    core = np.zeros((h, w), np.float32)
    cv2.ellipse(core, (int(lx * 8), int((ly + 0.25 * hh) * 8)), (int(ww * 0.75 * 8), int(max(1, hh * 0.55) * 8)), 0, 0, 360, 1.0, -1, cv2.LINE_AA, 3)
    core = cv2.GaussianBlur(core, (0, 0), max(1.5, hh * 0.45))
    refr = cv2.remap(roi, xx, (yy - np.float32(2.2 * hh + 0.06 * mw)).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    refr = cv2.GaussianBlur(refr, (0, 0), 1.0); rl = refr.mean(2, keepdims=True) / 255.0
    inner = DARK + 0.22 * refr * np.array([1.0, 0.9, 0.8], np.float32) + AMBER * (core[..., None] * min(1.0, o * 1.25) * a.glow * 0.62) * (0.75 + 0.5 * rl)
    al = (slit * a.dark_alpha)[..., None]
    comp = roi * (1 - al) + inner * al
    # (1) amber light spill: soft additive bloom on nearby facets / gold veins / lower lip + chin, falloff ~20-40 px
    sig = (10 + 9 * o) * max(0.7, sc)
    spill = cv2.GaussianBlur(np.roll(slit, int(0.06 * mw), axis=0), (0, 0), sig)
    spill = spill / (spill.max() + 1e-6) * (1 - slit * 0.9)
    lum = roi.mean(2, keepdims=True) / 255.0
    comp = comp + AMBER * (spill[..., None] * a.spill * o) * (0.35 + 0.9 * lum)
    out = fr.copy(); out[y0:y1, x0:x1] = np.clip(comp, 0, 255).astype(np.uint8)
    enc.stdin.write(out.tobytes()); log.append([i, round(a.song_start + i / fps, 3), vis[i], round(float(o), 3), round(cx, 1), round(cy, 1), round(sc, 3), round(jaw, 2)])
enc.stdin.close(); enc.wait()
if a.silent_out: subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.out, "-map", "0:v", "-c", "copy", "-an", a.silent_out], check=True)
if a.track_json:
    json.dump({"clip": a.clip, "song_start": a.song_start, "mouth_ref": [cx0, cy0, mw0, mh0], "open_cap": a.open_cap,
               "track_raw": raw.round(2).tolist(), "frames": log}, open(a.track_json, "w"))
print("wrote", a.out, "frames", n, "open frames", int((ape > 0).sum()))
