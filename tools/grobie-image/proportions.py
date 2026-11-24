# Copyright (c) 2026 INTENSE FINANCE, LLC
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. See LICENSE-GPLv3.txt in this tools package, or
# https://grobie.slopcore.army/tools/LICENSE-GPLv3.txt
#
"""Body-proportion check: is Grobie drawn tall and slim (canon), or big-headed and short-legged?
ViTPose-base (usyd-community/vitpose-base-simple, Apache-2.0) finds 17 COCO body keypoints inside
Grobie's person box (OWLv2); SAM masks his silhouette for the crown of the head and the soles of the feet.
  heads_tall  = standing height / head height
  leg_ratio   = (hip line -> soles) / standing height
Head height is estimated from the face keypoints (drawing convention: the eye line is ~1/2 and the nose
~2/3 of the way down from crown to chin): mean of 2*(eye - crown) and 1.5*(nose - crown).
Thresholds come from the Proprietor-approved master (grobie-proportions-master-v1.jpg); see README."""
import os, json, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
CAL = os.path.join(HERE, "calib", "proportions-calibration.json")
MID = "usyd-community/vitpose-base-simple"
_pose = None
def pose():
    global _pose
    if _pose is None:
        from transformers import VitPoseForPoseEstimation, AutoProcessor
        _pose = (AutoProcessor.from_pretrained(MID), VitPoseForPoseEstimation.from_pretrained(MID).eval())
    return _pose
NAMES = ["nose", "l_eye", "r_eye", "l_ear", "r_ear", "l_shoulder", "r_shoulder", "l_elbow", "r_elbow", "l_wrist", "r_wrist",
         "l_hip", "r_hip", "l_knee", "r_knee", "l_ankle", "r_ankle"]
SKEL = [(0, 1), (0, 2), (1, 3), (2, 4), (5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
DEFAULT_TH = {"heads_warn": 6.0, "heads_fail": 5.2, "leg_warn": 0.42, "leg_fail": 0.36, "legs_in_heads_warn": 2.6, "legs_in_heads_fail": 2.2}
def thresholds():
    if os.path.exists(CAL): return json.load(open(CAL))["thresholds"], True
    return DEFAULT_TH, False
def find_grobie(im):
    """Person box and head box for Grobie (the brightest glass head)."""
    import torch
    import aim as A
    P, M = A.owl(); q = ["a photo of a person", "a photo of a head", "a photo of a robot"]
    inp = P(text=[q], images=im, return_tensors="pt")
    with torch.no_grad(): out = M(**inp)
    W, H = im.size
    r = P.post_process_grounded_object_detection(out, threshold=0.05, target_sizes=torch.tensor([[max(W, H)] * 2]))[0]
    dets = []
    for s, l, b in zip(r["scores"].tolist(), r["labels"].tolist(), r["boxes"].tolist()):
        b = [max(0, b[0]), max(0, b[1]), min(W, b[2]), min(H, b[3])]
        if b[2] - b[0] > 8 and b[3] - b[1] > 8: dets.append({"kind": ["person", "head", "person"][l], "score": s, "box": b})
    gray = np.asarray(im.convert("L"), np.float32) / 255
    heads = []
    for d in A.nms([d for d in dets if d["kind"] == "head"], 0.3):
        x0, y0, x1, y1 = map(int, d["box"])
        if d["score"] >= 0.10: heads.append({**d, "lum": float(gray[y0:y1, x0:x1].mean())})
    persons = A.nms([d for d in dets if d["kind"] == "person" and d["score"] >= 0.08], 0.5)
    if not persons: return None, None
    def contains(p, h):
        cx, cy = (h["box"][0] + h["box"][2]) / 2, (h["box"][1] + h["box"][3]) / 2
        return p["box"][0] <= cx <= p["box"][2] and p["box"][1] - 0.05 * H <= cy <= p["box"][3]
    head = max(heads, key=lambda h: h["score"] * h["lum"]) if heads else None
    cand = [p for p in persons if head is None or contains(p, head)] or persons
    area = lambda b: (b[2] - b[0]) * (b[3] - b[1])
    person = max(cand, key=lambda p: p["score"] * area(p["box"]) ** 0.5)
    return person, head
def keypoints(im, box):
    import torch
    P, M = pose(); x0, y0, x1, y1 = box; b = [[x0, y0, x1 - x0, y1 - y0]]
    inp = P(im, boxes=[b], return_tensors="pt")
    with torch.no_grad(): o = M(**inp)
    r = P.post_process_pose_estimation(o, boxes=[b])[0][0]
    return np.array(r["keypoints"].tolist()), np.array(r["scores"].tolist())
def run(path, debug_out=None):
    import aim as A
    t0 = time.time(); im = Image.open(path).convert("RGB"); W, H = im.size
    res = {"file": path, "size": f"{W}x{H}", "model": MID + " (Apache-2.0)"}
    th, calibrated = thresholds(); res["thresholds"] = th; res["calibrated"] = calibrated
    person, head = find_grobie(im)
    if person is None:
        res.update(verdict="N/A", reason="proportions not measured: no figure found", notes=["no figure found"], full_figure=False); return res
    pb = person["box"]; m = 0.03
    box = [max(0, pb[0] - m * (pb[2] - pb[0])), max(0, pb[1] - m * (pb[3] - pb[1])), min(W, pb[2] + m * (pb[2] - pb[0])), min(H, pb[3] + m * (pb[3] - pb[1]))]
    kp, ks = keypoints(im, box)
    sm = A.masks(im, [box])[0]
    # ---- sanity checks: does the pose model actually land on a robot? ----
    problems = []
    low = [NAMES[i] for i in range(17) if ks[i] < 0.5]
    if low: problems.append("low-confidence keypoints: " + ", ".join(low))
    y = lambda *ii: float(np.mean([kp[i, 1] for i in ii]))
    eye_y, nose_y, sh_y, hip_y, knee_y, ank_y = y(1, 2), y(0), y(5, 6), y(11, 12), y(13, 14), y(15, 16)
    if not (eye_y < sh_y < hip_y < knee_y < ank_y): problems.append("keypoints out of top-to-bottom order (eyes, shoulders, hips, knees, ankles)")
    if head is not None:
        hb = head["box"]
        if not (hb[0] <= kp[0, 0] <= hb[2] and hb[1] <= kp[0, 1] <= hb[3]): problems.append("nose keypoint is outside the detected head")
    def on_mask(pt, r):
        x, yy = int(round(pt[0])), int(round(pt[1])); x0, x1 = max(0, x - r), min(W, x + r + 1); y0, y1 = max(0, yy - r), min(H, yy + r + 1)
        return bool(sm[y0:y1, x0:x1].any())
    off = [NAMES[i] for i in (0, 5, 6, 11, 12, 13, 14, 15, 16) if not on_mask(kp[i], max(4, int(0.015 * H)))]
    if off: problems.append("keypoints off the silhouette: " + ", ".join(off))
    if kp[5, 0] < kp[6, 0] and kp[3, 0] < kp[4, 0]:
        problems.append("left/right keypoints are mirrored (back view?): face keypoints are guesses; head size uses the crown and the eye/nose lines only")
    # ---- crown and soles from the SAM silhouette ----
    hx0 = int(min(kp[3, 0], kp[4, 0])); hx1 = int(max(kp[3, 0], kp[4, 0])) + 1
    if head is not None: hx0, hx1 = int(max(hx0, head["box"][0])) - 2, int(min(max(hx1, hx0 + 4), head["box"][2])) + 2
    rows = np.where(sm[:, max(0, hx0):min(W, hx1)].any(1))[0]
    crown = float(rows.min()) if len(rows) else float(box[1])
    if head is not None and abs(crown - head["box"][1]) > 0.04 * H:
        # the glass head can drop out of the SAM silhouette (or the silhouette can bleed into the backdrop): use the head box
        problems.append(f"crown from silhouette ({crown:.0f}) and head box top ({head['box'][1]:.0f}) disagree; used the head box")
        crown = float(head["box"][1])
    soles = []
    for a in (15, 16):
        ax, ay = kp[a]; r = int(0.05 * H); cols = sm[int(ay):, max(0, int(ax - r)):min(W, int(ax + r))]
        rr = np.where(cols.any(1))[0]
        # lowest row of the run that is connected to the ankle (stop at the first empty row)
        last = 0
        for v in rr:
            if v - last > 3: break
            last = v
        soles.append(ay + last)
    floor = float(max(soles))
    cut = floor >= H - 3 or crown <= 2
    height = floor - crown
    head_eye = 2.0 * (eye_y - crown); head_nose = 1.5 * (nose_y - crown); head_h = (head_eye + head_nose) / 2
    heads_tall = height / head_h if head_h > 0 else 0
    leg = floor - hip_y; leg_ratio = leg / height if height > 0 else 0; legs_heads = leg / head_h if head_h > 0 else 0
    res.update(person_box=[round(v) for v in box], person_score=round(person["score"], 3),
               head_box=[round(v) for v in head["box"]] if head else None,
               crown_y=round(crown), soles_y=round(floor), height_px=round(height), head_px=round(head_h),
               head_px_by_eye=round(head_eye), head_px_by_nose=round(head_nose), hip_y=round(hip_y),
               heads_tall=round(heads_tall, 2), leg_ratio=round(leg_ratio, 3), legs_in_heads=round(legs_heads, 2),
               keypoints={NAMES[i]: [round(kp[i, 0]), round(kp[i, 1]), round(float(ks[i]), 2)] for i in range(17)},
               keypoint_problems=problems, figure_cut_off=bool(cut))
    # ---- is this a full standing figure? (close-ups, knee crops and back views can't be measured) ----
    na = []
    if cut: na.append("figure touches the top or bottom frame edge (head or feet cut off)")
    if max(ks[15], ks[16]) < 0.5: na.append("no confident ankle keypoint (feet hidden or out of frame)")
    if min(ks[0], ks[1], ks[2]) < 0.5: na.append("no confident face keypoints (back view or face hidden)")
    if not (crown < eye_y < sh_y < hip_y < knee_y < ank_y): na.append("body keypoints out of order (not standing upright, or crown below the eyes)")
    if len(off) >= 3: na.append(f"{len(off)} keypoints land off the silhouette (pose or mask not reliable, e.g. a back view)")
    if height < 0.45 * H: na.append(f"figure is only {100 * height / H:.0f}% of the image height (too small to measure)")
    res["full_figure"] = not na
    if na:
        res.update(verdict="N/A", reason="proportions not measured: " + "; ".join(na), notes=na)
        if debug_out: res["debug_image"] = draw(im, sm, kp, ks, res, debug_out)
        res["seconds"] = round(time.time() - t0, 1); return res
    notes, verdict = [], "PASS"
    rank = {"PASS": 0, "WARN": 1, "FAIL": 2}
    def bump(v, msg):
        nonlocal verdict; notes.append(msg); verdict = v if rank[v] > rank[verdict] else verdict
    for val, k, name in ((heads_tall, "heads", "heads tall"), (leg_ratio, "leg", "leg length / height"), (legs_heads, "legs_in_heads", "leg length in heads")):
        if val < th[k + "_fail"]: bump("FAIL", f"{name} {val:.2f} under the FAIL line {th[k + '_fail']} (big head / short legs)")
        elif val < th[k + "_warn"]: bump("WARN", f"{name} {val:.2f} under the WARN line {th[k + '_warn']}")
    if problems: notes.append("pose check (info): " + "; ".join(problems))
    res.update(verdict=verdict, reason="; ".join(notes) if notes else f"{heads_tall:.2f} heads tall, legs {leg_ratio:.2f} of height ({legs_heads:.2f} heads): canon proportions",
               notes=notes)
    if debug_out: res["debug_image"] = draw(im, sm, kp, ks, res, debug_out)
    res["seconds"] = round(time.time() - t0, 1)
    return res
def draw(im, sm, kp, ks, res, out):
    a = np.asarray(im).astype(np.float32).copy(); a[sm] = a[sm] * 0.7 + np.array([60, 200, 255]) * 0.3
    img = Image.fromarray(a.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(img); W, H = img.size
    try: f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(14, H // 55))
    except Exception: f = ImageFont.load_default()
    for i, j in SKEL: d.line([tuple(kp[i]), tuple(kp[j])], fill=(255, 230, 60), width=max(2, H // 300))
    for i in range(17):
        x, y = kp[i]; r = max(4, H // 180); c = (60, 255, 120) if ks[i] >= 0.5 else (255, 60, 60)
        d.ellipse([x - r, y - r, x + r, y + r], fill=c, outline=(0, 0, 0))
    crown, floor, hh, hip = res["crown_y"], res["soles_y"], res["head_px"], res["hip_y"]
    x0, x1 = res["person_box"][0], res["person_box"][2]; rx = max(10, x0 - 40)
    d.line([(x0, crown), (x1, crown)], fill=(255, 255, 255), width=2); d.line([(x0, floor), (x1, floor)], fill=(255, 255, 255), width=2)
    d.line([(x0, hip), (x1, hip)], fill=(255, 120, 255), width=2)
    k = 0
    while hh > 5 and k < 15 and crown + k * hh <= floor + 1:  # head-height ladder
        yy = crown + k * hh; d.line([(rx - 12, yy), (rx + 12, yy)], fill=(255, 255, 255), width=3)
        if k: d.text((rx + 16, yy - hh / 2 - 8), str(k), fill=(255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0))
        k += 1
    d.line([(rx, crown), (rx, floor)], fill=(255, 255, 255), width=3)
    lines = [f"PROPORTIONS {res['verdict']}: {res['heads_tall']} heads tall, legs {res['leg_ratio']} of height ({res['legs_in_heads']} heads)"] + res["notes"]
    if res["verdict"] == "N/A": lines = ["PROPORTIONS N/A (not measured; numbers below are not valid)"] + res["notes"]
    for n, t in enumerate(lines):
        d.text((10, 10 + n * (f.size + 6)), t[:110], fill=(255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0))
    img.save(out, quality=90); return out
