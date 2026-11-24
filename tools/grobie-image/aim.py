# Copyright (c) 2026 INTENSE FINANCE, LLC
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. See LICENSE-GPLv3.txt in this tools package, or
# https://grobie.slopcore.army/tools/LICENSE-GPLv3.txt
#
"""Aim / contact check: do Grobie's hands actually touch and grip the named object?
OWLv2 (open-vocabulary detection) finds the object and hands; SAM (box-prompted) masks them;
geometry measures gap, overlap, how much of the hand hugs the object, and how closed the hand is."""
import os, json, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
_owl = _sam = None
def owl():
    global _owl
    if _owl is None:
        import torch
        from transformers import Owlv2Processor, Owlv2ForObjectDetection
        mid = "google/owlv2-base-patch16-ensemble"
        _owl = (Owlv2Processor.from_pretrained(mid), Owlv2ForObjectDetection.from_pretrained(mid).eval())
    return _owl
def sam():
    global _sam
    if _sam is None:
        from transformers import SamModel, SamProcessor
        mid = "facebook/sam-vit-base"
        _sam = (SamProcessor.from_pretrained(mid), SamModel.from_pretrained(mid).eval())
    return _sam
HAND_Q = ["a photo of a hand", "a photo of a transparent glass hand", "a photo of a robot hand gripping"]
OCC_Q = ["a photo of a person", "a photo of a coat sleeve", "a photo of an arm"]  # things in front of / around the object that are not the object
def detect(im, obj):
    import torch
    P, M = owl(); q = [f"a photo of an {obj}" if obj[:1].lower() in "aeiou" else f"a photo of a {obj}"] + HAND_Q + OCC_Q
    inp = P(text=[q], images=im, return_tensors="pt")
    with torch.no_grad(): out = M(**inp)
    S = max(im.size)
    r = P.post_process_grounded_object_detection(out, threshold=0.05, target_sizes=torch.tensor([[S, S]]))[0]
    W, H = im.size; dets = []
    for s, l, b in zip(r["scores"].tolist(), r["labels"].tolist(), r["boxes"].tolist()):
        b = [max(0, b[0]), max(0, b[1]), min(W, b[2]), min(H, b[3])]
        if b[2] - b[0] > 4 and b[3] - b[1] > 4: dets.append({"kind": "object" if l == 0 else ("hand" if l <= len(HAND_Q) else "occluder"), "score": s, "box": b})
    return dets
def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x2 - x1) * max(0, y2 - y1); u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / u if u else 0
def nms(ds, t=0.4):
    keep = []
    for d in sorted(ds, key=lambda d: -d["score"]):
        if all(iou(d["box"], k["box"]) < t for k in keep): keep.append(d)
    return keep
_emb = {}
def masks(im, boxes):
    import torch
    P, M = sam(); out = []
    # one image embedding per image, reused for every box prompt. Keyed by the image object itself (plus a content
    # digest): the old id(im) key could be reused by a NEW image after the old one was freed, giving stale masks.
    import hashlib
    key = (im.size, hashlib.md5(im.tobytes()).hexdigest())
    if _emb.get("key") != key:
        _emb.clear(); base = P(im, return_tensors="pt")
        with torch.no_grad(): _emb["emb"] = M.get_image_embeddings(base["pixel_values"])
        _emb["key"] = key
    for b in boxes:
        inp = P(im, input_boxes=[[b]], return_tensors="pt"); inp.pop("pixel_values", None)
        with torch.no_grad(): o = M(image_embeddings=_emb["emb"], input_boxes=inp["input_boxes"], multimask_output=True)
        ms = P.image_processor.post_process_masks(o.pred_masks, inp["original_sizes"], inp["reshaped_input_sizes"])[0][0].numpy()
        sc = o.iou_scores[0, 0].numpy(); m = ms[int(sc.argmax())]
        x0, y0, x1, y1 = map(int, b); clip = np.zeros_like(m); clip[y0:y1, x0:x1] = True
        out.append(m & clip)
    return out
def tile_masks(im, box, main):
    """Long objects (anchor shank + ring) often come back from SAM with a part missing (v4: the ring and the shank
    above the fists). Prompt SAM again with 3 overlapping half-length tiles along the box's long axis and keep each
    tile mask that touches or overlaps the main mask and is not bigger than it (so it can't swallow the background)."""
    from scipy.ndimage import binary_dilation
    x0, y0, x1, y1 = box; tall = (y1 - y0) >= (x1 - x0); L = (y1 - y0) if tall else (x1 - x0)
    tiles = []
    for k in range(3):
        a = (y0 if tall else x0) + k * L / 4; b = a + L / 2
        tiles.append([x0, a, x1, b] if tall else [a, y0, b, y1])
    near = binary_dilation(main, iterations=3); add = np.zeros_like(main); kept = []
    for t, m in zip(tiles, masks(im, tiles)):
        if m.sum() < 30: continue
        if (m & near).sum() >= 20 and m.sum() <= 1.2 * max(1, main.sum()):
            add |= m; kept.append([round(v) for v in t])
    return add, kept
def local_axis(om, hm, hsize):
    """Unit direction and a centre point of the object near this hand (PCA of object pixels in a window round the hand)."""
    ys, xs = np.nonzero(hm); cy, cx = ys.mean(), xs.mean(); R = 1.6 * hsize
    H, W = om.shape; y0, y1, x0, x1 = int(max(0, cy - R)), int(min(H, cy + R)), int(max(0, cx - R)), int(min(W, cx + R))
    oy, ox = np.nonzero(om[y0:y1, x0:x1])
    if len(oy) < 50: return None, None
    pts = np.stack([ox + x0, oy + y0], 1).astype(np.float64); mu = pts.mean(0)
    w, v = np.linalg.eigh(np.cov((pts - mu).T)); d = v[:, int(w.argmax())]
    return d / np.linalg.norm(d), mu
def spans_object(om, hm, others, hsize):
    """Occlusion-aware grip (Grobie's rule): a closed hand counts as GRIP when the object mask continues on BOTH sides
    of the hand along the object's axis. Another hand stacked on the shank may sit in between (two fists on one shank).
    Returns (both_sides, detail)."""
    d, mu = local_axis(om, hm, hsize)
    if d is None: return False, "no object pixels near the hand", None
    H, W = om.shape; n = np.array([-d[1], d[0]])
    ys, xs = np.nonzero(hm); P = np.stack([xs, ys], 1) - mu; t = P @ d; sN = P @ n
    tmin, tmax = np.percentile(t, 1), np.percentile(t, 99)
    half = 0.25 * hsize; reach = 0.45 * hsize; step = 2.0
    s_vals = np.arange(-half, half + 1, 3.0)
    def at(tt, mask):
        q = mu + tt * d + s_vals[:, None] * n; x = q[:, 0].round().astype(int); y = q[:, 1].round().astype(int)
        ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
        return bool(mask[y[ok], x[ok]].any()) if ok.any() else False
    res = {}; widths = []
    oy, ox = np.nonzero(om); OP = np.stack([ox, oy], 1) - mu; ot = OP @ d; os_ = OP @ n
    for side, t0, sg in (("before", tmin, -1), ("after", tmax, 1)):
        tt = t0; through = 0.0; found = False; budget = reach
        while budget > 0:
            tt += sg * step
            if at(tt, om): found = True; break
            if at(tt, hm) or at(tt, others): through += step; continue   # still inside this hand / a stacked hand
            budget -= step
        res[side] = (found, round(through))
        if found:  # the object's cross-section just beyond the hand on this side
            lo_t, hi_t = sorted((tt, tt + sg * 0.3 * hsize)); sel = (ot >= lo_t) & (ot <= hi_t) & (np.abs(os_) <= 1.2 * hsize)
            if sel.sum() > 10: widths.append((np.percentile(os_[sel], 5), np.percentile(os_[sel], 95)))
    both = res["before"][0] and res["after"][0]
    # does the hand cover the object's full width (wrapped) or only one side of it (pressed against it)?
    cover = None
    if widths:
        hl, hh = np.percentile(sN, 3), np.percentile(sN, 97)
        ws = [w for w in widths if w[1] - w[0] >= 0.15 * hsize]        # ignore slivers of mask beside the fist
        if ws: cover = round(max(float((min(hh, hi) - max(hl, lo)) / max(1.0, hi - lo)) for lo, hi in ws), 3)
        if os.environ.get("AIM_DEBUG"): print("   span dbg axis", d.round(2), "mu", mu.round(0), "widths", [tuple(round(float(x)) for x in w) for w in widths], "hand s", round(float(hl)), round(float(hh)), "t", round(float(tmin)), round(float(tmax)), res)
    return both, f"object {'continues' if res['before'][0] else 'stops'} before / {'continues' if res['after'][0] else 'stops'} after the hand along its axis; covers {cover} of its width", cover
def solidity(m):
    from skimage.morphology import convex_hull_image
    if m.sum() < 20: return 0.0
    return float(m.sum() / max(1, convex_hull_image(m).sum()))
# Per-hand grip rule. Set BEFORE looking at the v2 remake; see README for the calibration table.
GRIP = {"solidity": 0.75, "border": 0.20, "far": 0.10, "open_hand": 0.70, "cover": 0.80}
# Occlusion-aware grip (added 2026-11-23): a closed hand (solidity >= GRIP solidity) touching the object, with the
# object continuing on both sides of it along the object's axis, is a GRIP even when little of its outline borders the
# object (the fist hides the shank). Spread hands never qualify (they are MISS-open-hand). Guard: the hand must also
# cover at least GRIP["cover"] of the object's width next to it (wrapped across the shank, not pressed on one side of it:
# anchor v2's lower hand covers 0.49 and stays TOUCH; the v3/v4 fists cover 0.99-1.0).
def run(path, obj="anchor", hands=1, debug_out=None):
    from scipy.ndimage import distance_transform_edt, binary_dilation
    t0 = time.time(); im = Image.open(path).convert("RGB"); W, H = im.size; diag = (W * W + H * H) ** 0.5
    dets = detect(im, obj)
    objs = nms([d for d in dets if d["kind"] == "object"])
    hs = nms([d for d in dets if d["kind"] == "hand"], 0.3)
    res = {"file": path, "object": obj, "hands_required": hands, "size": f"{W}x{H}"}
    if not objs or objs[0]["score"] < 0.10:
        res.update(verdict="FAIL", reason=f"no '{obj}' found (best score {objs[0]['score'] if objs else 0:.2f})"); return res
    ob = objs[0]
    # object mask = union of SAM masks of the strong object boxes (big objects come in parts)
    obj_boxes = [d["box"] for d in objs if d["score"] >= max(0.10, 0.5 * ob["score"])][:4]
    om = np.zeros((H, W), bool)
    for m in masks(im, obj_boxes): om |= m
    om_main = om.copy()
    tadd, tiles_kept = tile_masks(im, ob["box"], om); om |= tadd      # fill parts SAM skipped along the long axis (v4 ring/shank)
    om_raw = om.copy()
    occ = [d for d in nms([d for d in dets if d["kind"] == "occluder"], 0.5) if d["score"] >= 0.15][:6]
    occ_mask = np.zeros((H, W), bool)
    for m in (masks(im, [d["box"] for d in occ]) if occ else []):
        if (m & om_main).sum() < 0.6 * m.sum(): occ_mask |= m   # skip an "occluder" mask that is mostly the object itself (judged on the box mask, before tiles)
    om &= ~occ_mask
    gray = np.asarray(im.convert("L"), np.float32)
    # Grobie's hands: big enough, and bright (glowing glass) compared with the scene
    cands = []
    for h in hs:
        x0, y0, x1, y1 = map(int, h["box"]); area = (x1 - x0) * (y1 - y0) / (W * H)
        if area < 0.004 or area > 0.15: continue
        lum = float(gray[y0:y1, x0:x1].mean()) / 255
        cands.append({**h, "area_pct": round(100 * area, 2), "lum": round(lum, 3)})
    scene_lum = float(gray.mean()) / 255
    cands = [c for c in cands if c["lum"] > scene_lum * 1.15] or cands
    cands = sorted(cands, key=lambda c: -(c["score"] * c["lum"]))
    picked = []
    for c in cands:
        if all(iou(c["box"], p["box"]) < 0.2 for p in picked): picked.append(c)
        if len(picked) == max(2, hands): break
    hmasks = masks(im, [p["box"] for p in picked]) if picked else []
    for hm in hmasks: om &= ~hm                                # a hand in front of the object is not the object
    dist_to_obj = distance_transform_edt(~om)
    ow = om.any(0).sum(); 
    per = []
    for p, hm in zip(picked, hmasks):
        if hm.sum() < 30: continue
        d = dist_to_obj[hm]
        gap = float(d.min())                                   # 0 = touching / overlapping in 2D
        hx = hm.any(0).sum(); hy = hm.any(1).sum(); hsize = max(hx, hy)
        r = max(3, int(0.04 * hsize)); ring = binary_dilation(hm, iterations=r) & ~hm
        overlap = float((ring & om).sum() / max(1, ring.sum()))  # share of the hand's outline that borders the object
        near = float((d <= 0.12 * hsize).mean())               # share of the hand within ~12% of its size from the object
        far = float((d > 0.35 * hsize).mean())                 # share of the hand reaching well away from the object (spread / missing fingers)
        sol = solidity(hm)
        contact = gap <= max(3, 0.004 * W)
        open_hand = sol < GRIP["open_hand"]                    # spread fingers: overlap in 2D is the hand passing in front, not a grip
        grip_outline = contact and sol >= GRIP["solidity"] and overlap >= GRIP["border"] and far <= GRIP["far"]
        others = np.zeros_like(hm)
        for q in hmasks:
            if q is not hm: others |= q
        span, span_detail, cover = spans_object(om, hm, others, hsize) if contact and sol >= GRIP["solidity"] else (False, "not a closed hand touching the object", None)
        # reaching-away measured against object + the other (stacked) hands: a fist stacked on a fist is still on the shank
        far_occ = float((distance_transform_edt(~(om | others))[hm] > 0.35 * hsize).mean())
        grip_occluded = contact and sol >= GRIP["solidity"] and span and not open_hand and cover is not None and cover >= GRIP["cover"]
        grip = grip_outline or grip_occluded
        per.append({"box": [round(x) for x in p["box"]], "det_score": round(p["score"], 3), "gap_px": round(gap, 1),
                    "gap_pct_width": round(100 * gap / W, 2), "border_share": round(overlap, 3), "near_share": round(near, 3),
                    "far_share": round(far, 3), "solidity": round(sol, 3), "contact": bool(contact), "grip": bool(grip),
                    "grip_rule": "outline" if grip_outline else ("occlusion: object on both sides" if grip_occluded else None),
                    "spans_object": bool(span), "span_detail": span_detail, "far_share_with_stacked_hands": round(far_occ, 3), "width_cover": cover,
                    "state": "GRIP" if grip else ("MISS-open-hand" if contact and open_hand else ("TOUCH" if contact else "MISS")),
                    "_mask": hm})
    rank = {"GRIP": 0, "TOUCH": 1, "MISS-open-hand": 2, "MISS": 3}
    per = sorted(per, key=lambda x: (rank[x["state"]], x["gap_px"]))
    n_contact = sum(p["state"] in ("GRIP", "TOUCH") for p in per); n_grip = sum(p["state"] == "GRIP" for p in per)
    if len(per) < hands: verdict, reason = "FAIL", f"found {len(per)} Grobie hand(s), need {hands}"
    elif n_contact < hands: verdict, reason = "FAIL", f"{n_contact} of {hands} required hand(s) touch the {obj} with a closed hand (" + ", ".join(p["state"] for p in per) + ")"
    elif n_grip < hands: verdict, reason = "WARN", f"{n_contact} hand(s) touch the {obj} but only {n_grip} look like a wrapped grip (open/spread fingers or reaching past it)"
    else: verdict, reason = "PASS", f"{n_grip} hand(s) touch and grip the {obj}"
    res.update(verdict=verdict, reason=reason, object_score=round(ob["score"], 3), hands_found=len(per), sam_tiles_added=tiles_kept,
               hands_in_contact=n_contact, hands_gripping=n_grip,
               hands=[{k: v for k, v in p.items() if not k.startswith("_")} for p in per])
    if debug_out: res["debug_image"] = draw(im, om, obj_boxes, per, picked, res, debug_out)
    res["seconds"] = round(time.time() - t0, 1)
    return res
_vlm = None
def vlm_vote(path, obj):
    """Optional second opinion from SmolVLM-500M-Instruct (Apache-2.0). Advisory only: it does not change the verdict."""
    global _vlm
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    if _vlm is None:
        mid = "HuggingFaceTB/SmolVLM-500M-Instruct"
        _vlm = (AutoProcessor.from_pretrained(mid), AutoModelForImageTextToText.from_pretrained(mid, torch_dtype=torch.float32).eval())
    P, M = _vlm; im = Image.open(path).convert("RGB")
    msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": f"Are the character's hands gripping the {obj}? Answer yes or no."}]}]
    t = P.apply_chat_template(msgs, add_generation_prompt=True); inp = P(text=t, images=[im], return_tensors="pt")
    with torch.no_grad(): o = M.generate(**inp, max_new_tokens=4, do_sample=False)
    return P.batch_decode(o[:, inp["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()
def draw(im, om, obj_boxes, per, picked, res, out):
    a = np.asarray(im).astype(np.float32).copy()
    a[om] = a[om] * 0.5 + np.array([255, 60, 60]) * 0.5
    cols = [(60, 255, 120), (60, 200, 255), (255, 220, 60), (255, 120, 255)]
    for i, p in enumerate(per):
        a[p["_mask"]] = a[p["_mask"]] * 0.45 + np.array(cols[i % 4]) * 0.55
    img = Image.fromarray(a.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    try: f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except Exception: f = ImageFont.load_default()
    for b in obj_boxes: d.rectangle(b, outline=(255, 60, 60), width=3)
    for i, p in enumerate(per):
        b = p["box"]; d.rectangle(b, outline=cols[i % 4], width=3)
        lab = f"hand{i+1} gap {p['gap_px']}px border {p['border_share']} far {p['far_share']} sol {p['solidity']} {p['state']}" + (" (both sides, covers %s)" % p.get("width_cover") if (p.get("grip_rule") or "").startswith("occlusion") else "")
        tw = d.textlength(lab, font=f); x = min(b[0] + 4, img.width - tw - 6)
        d.text((max(4, x), b[1] + 4), lab, fill=(255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((10, 10), f"AIM {res['verdict']}: {res['reason']}", fill=(255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0))
    img.save(out); return out
