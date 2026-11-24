#!/usr/bin/env python3
# Copyright (c) 2026 INTENSE FINANCE, LLC
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. See LICENSE-GPLv3.txt in this tools package, or
# https://grobie.slopcore.army/tools/LICENSE-GPLv3.txt
#
"""grobie-image: offline helper for adding consistent Grobie images to https://grobie.slopcore.army
Subcommands: check, aim, proportions, add, prompt, cutout, calibrate, calibrate-proportions.
Nothing here uploads, publishes or sends anything."""
import argparse, datetime, hashlib, io, json, os, re, shutil, sys
import numpy as np
from PIL import Image, ImageOps
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("HF_HOME", os.path.join(HERE, "models", "hf"))
os.environ.setdefault("U2NET_HOME", os.path.join(HERE, "models", "u2net"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
def kit_dir():
    return os.environ.get("GROBIE_KIT") or os.path.join(HERE, "kit")
KIT = kit_dir()
# Canonical v2 reference set, split into the individual views each sheet contains.
REFS = [  # (file, layout cols x rows)
    ("grobie-outfit-master-v2.jpg", (1, 1)),
    ("grobie-head-turnaround-v2.jpg", (4, 1)),
    ("grobie-mouth-shapes-v3.jpg", (3, 3)),
    ("grobie-turnaround-shine-v2.jpg", (4, 1)),
    # PRIMARY (Proprietor, Nov 23 2026 5:36 AM CST: "MUCH BETTER DIMENSIONS - SAVE THIS PHOTO TO ONE OF YOUR PRIMARY IMAGES")
    ("grobie-proportions-master-v1.jpg", (1, 1)),
]
PROP_MASTER = os.path.join(KIT, "grobie-proportions-master-v1.jpg")
PROP_MASTER_MD5 = "118825eb55e1153ece7a28ff53918df4"
PALETTE = {  # from VIDEO-KIT.md section (c), sampled from the canonical art
    "navy_coat": "#13182B", "gold_trim": "#C29E7C", "glass_blue": "#34374B",
    "core_glow": "#F3DBBC", "eye_glow": "#FEF7F0",
}
CALIB = os.path.join(HERE, "calibration.json")
BG = (43, 43, 43)

# ---------- embeddings ----------
_model = None
def model():
    global _model
    if _model is None:
        import torch
        from transformers import AutoModel
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        _model = AutoModel.from_pretrained("facebook/dinov2-small").eval()
    return _model
MEAN = np.array([0.485, 0.456, 0.406], np.float32); STD = np.array([0.229, 0.224, 0.225], np.float32)
def to_tensor(im):
    im = ImageOps.pad(im.convert("RGB"), (224, 224), method=Image.BICUBIC, color=BG)
    a = (np.asarray(im, np.float32) / 255 - MEAN) / STD
    return a.transpose(2, 0, 1)
def embed(crops):
    import torch
    out = []
    with torch.no_grad():
        for i in range(0, len(crops), 32):
            x = torch.from_numpy(np.stack([to_tensor(c) for c in crops[i:i + 32]]))
            h = model()(pixel_values=x).last_hidden_state
            cls = torch.nn.functional.normalize(h[:, 0], dim=-1)
            pm = torch.nn.functional.normalize(h[:, 1:].mean(1), dim=-1)
            out.append(torch.nn.functional.normalize(cls + pm, dim=-1).numpy())
    return np.concatenate(out)
def panels(path, layout):
    im = Image.open(path).convert("RGB"); W, H = im.size; c, r = layout; out = []
    for j in range(r):
        for i in range(c):
            out.append(im.crop((i * W // c, j * H // r, (i + 1) * W // c, (j + 1) * H // r)))
    if layout == (1, 1):  # outfit / proportions master: also the head+collar and the chest
        out += [im.crop((0, 0, W, H // 3)), im.crop((0, H // 5, W, H * 3 // 5))]
    return out
def crops(im):
    im = im.convert("RGB"); W, H = im.size; m = min(W, H); out = [im]
    for s in (1.0, 0.6, 0.4):
        w = int(m * s); st = max(1, w // 2)
        for y in range(0, H - w + 1, st):
            for x in range(0, W - w + 1, st):
                out.append(im.crop((x, y, x + w, y + w)))
    return out
_refcache = None
def ref_embeddings():
    global _refcache
    if _refcache is None:
        cache = os.path.join(HERE, "models", "ref-embeddings.npz")
        sig = hashlib.md5("".join(f + str(os.path.getsize(os.path.join(KIT, f))) for f, _ in REFS).encode()).hexdigest()
        if os.path.exists(cache):
            z = np.load(cache, allow_pickle=True)
            if str(z["sig"]) == sig: _refcache = (z["E"], list(z["names"])); return _refcache
        E, names = [], []
        for f, lay in REFS:
            ps = panels(os.path.join(KIT, f), lay); E.append(embed(ps)); names += [f] * len(ps)
        E = np.concatenate(E); np.savez(cache, E=E, names=np.array(names), sig=sig); _refcache = (E, names)
    return _refcache
def stem_key(p):
    b = os.path.basename(p).lower()
    b = re.sub(r"\.(jpg|jpeg|png|webp)$", "", b); return re.sub(r"-4k$", "", b)
_refmd5 = {}
def ref_md5(f):
    if f not in _refmd5: _refmd5[f] = hashlib.md5(open(os.path.join(KIT, f), "rb").read()).hexdigest()
    return _refmd5[f]
def consistency(path_or_im, exclude_self=True, src_name=None):
    im = Image.open(path_or_im) if isinstance(path_or_im, str) else path_or_im
    E, names = ref_embeddings()
    src = src_name or (path_or_im if isinstance(path_or_im, str) else "")
    key = stem_key(src)
    # leave-one-out by name AND by content: a byte-identical copy under another name (anchor v4 = proportions master) is excluded too
    smd5 = hashlib.md5(open(src, "rb").read()).hexdigest() if src and os.path.exists(src) else None
    keep = np.array([not (exclude_self and (stem_key(n) == key or (smd5 is not None and ref_md5(n) == smd5))) for n in names])
    C = embed(crops(im)); S = C @ E[keep].T
    best = S.max(1); top = np.sort(best)[::-1][:3]
    per_ref = {}
    for n, k, col in zip(names, keep, range(len(names))):
        pass
    kn = [n for n, k in zip(names, keep) if k]
    for j, n in enumerate(kn): per_ref[n] = max(per_ref.get(n, -1), float(S[:, j].max()))
    return float(top.mean()), {k: round(v, 3) for k, v in per_ref.items()}

# ---------- palette / sharpness ----------
def hex2rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def palette(im):
    from skimage.color import rgb2lab, deltaE_ciede2000
    s = im.convert("RGB").copy(); s.thumbnail((256, 256))
    a = np.asarray(s, np.float32) / 255; lab = rgb2lab(a).reshape(-1, 3); out = {}
    near_any = np.zeros(len(lab), bool); masks = {}
    chroma = np.hypot(lab[:, 1], lab[:, 2])
    for k, h in PALETTE.items():
        ref = rgb2lab(np.array([[hex2rgb(h)]], np.float32) / 255).reshape(1, 3)
        d = deltaE_ciede2000(lab, np.repeat(ref, len(lab), 0)); m = d < 12
        if k in ("navy_coat", "glass_blue"): m &= chroma > 6   # don't count the neutral grey backdrop as navy/glass
        masks[k] = m; out[k + "_pct"] = round(100 * m.mean(), 2); near_any |= m
    out["navy_or_glass_pct"] = round(100 * (masks["navy_coat"] | masks["glass_blue"]).mean(), 2)
    out["on_palette_pct"] = round(100 * near_any.mean(), 1)
    hsv = np.asarray(s.convert("HSV"), np.float32).reshape(-1, 3) / 255
    hue, sat, val = hsv[:, 0] * 360, hsv[:, 1], hsv[:, 2]
    red = ((hue < 15) | (hue > 340)) & (sat > 0.55) & (val > 0.35)
    green = (hue > 75) & (hue < 165) & (sat > 0.45) & (val > 0.3)
    pink = (hue > 290) & (hue <= 340) & (sat > 0.45) & (val > 0.35)
    out["off_canon_red_pct"] = round(100 * red.mean(), 2)
    out["off_canon_green_pct"] = round(100 * green.mean(), 2)
    out["off_canon_pink_pct"] = round(100 * pink.mean(), 2)
    return out
def sharpness(im):
    from scipy.ndimage import laplace
    g = im.convert("L").copy(); g.thumbnail((1024, 1024))
    return float(laplace(np.asarray(g, np.float32)).var())

# ---------- check ----------
def load_calib():
    if not os.path.exists(CALIB): return None
    return json.load(open(CALIB))
def subject_on_grey(rgb):
    from rembg import remove, new_session
    cut = remove(rgb, session=new_session("u2net"))
    bg = Image.new("RGBA", cut.size, BG + (255,)); bg.alpha_composite(cut); return bg.convert("RGB")
def check(path, quiet=False, src_name=None, subject=False, proportions=False):
    im = Image.open(path); W, H = im.size; rgb = im.convert("RGB")
    scene_score, per_ref = consistency(rgb, src_name=src_name or path)
    score, subj = scene_score, None
    if subject:  # scene images: also score the cut-out subject on the canonical grey, use the better of the two
        subj, per_ref_s = consistency(subject_on_grey(rgb), src_name=src_name or path)
        if subj > score: score, per_ref = subj, per_ref_s
    pal = palette(rgb); sh = sharpness(rgb)
    cal = load_calib(); th = cal["thresholds"] if cal else {"score_pass": 0.5, "score_warn": 0.35, "navy_min": 2, "gold_min": 0.3, "sharp_min": 20, "red_max": 1.0}
    notes, verdict = [], "PASS"
    def warn(msg):
        nonlocal verdict; notes.append(msg); verdict = "WARN" if verdict == "PASS" else verdict
    if score < th["score_warn"]: notes.append(f"consistency {score:.3f} below the floor {th['score_warn']} (looks like a different character)"); verdict = "FAIL"
    elif score < th["score_pass"]: warn(f"consistency {score:.3f} below pass line {th['score_pass']}")
    navy = pal["navy_or_glass_pct"]
    if navy < th["navy_min"]: warn(f"navy/glass-blue only {navy:.1f}% (min {th['navy_min']})")
    if pal["gold_trim_pct"] < th["gold_min"]: warn(f"gold trim only {pal['gold_trim_pct']}% (min {th['gold_min']})")
    if pal["off_canon_red_pct"] > th["red_max"]: warn(f"saturated red {pal['off_canon_red_pct']}% (max {th['red_max']}): canon has no red parts; check eyes/head")
    if min(W, H) < 720: warn(f"resolution {W}x{H}: short side under 720 px")
    if max(W, H) < 800: warn("long side under 800 px: thumb would be upscaled-looking")
    if sh < th["sharp_min"]: warn(f"sharpness {sh:.1f} below {th['sharp_min']} (blurry)")
    r = {"file": path, "verdict": verdict, "size": f"{W}x{H}", "consistency": round(score, 3),
         "scene_score": round(scene_score, 3), "subject_score": None if subj is None else round(subj, 3),
         "consistency_by_ref": per_ref, "sharpness": round(sh, 1), **pal, "notes": notes,
         "thresholds": th, "calibrated": bool(cal)}
    if not quiet: print_check(r)
    if proportions:
        r["proportions"] = prop_run(path, quiet=quiet)
    return r
def print_check(r):
    print(f"{r['verdict']}  {r['file']}")
    print(f"  consistency {r['consistency']}  (pass >= {r['thresholds']['score_pass']}, floor {r['thresholds']['score_warn']})"
          + (f"  [whole image {r['scene_score']}, cut-out subject {r['subject_score']}]" if r.get("subject_score") is not None else ""))
    print("  best match per reference: " + ", ".join(f"{k.replace('grobie-','').replace('.jpg','')} {v}" for k, v in r["consistency_by_ref"].items()))
    print(f"  size {r['size']}  sharpness {r['sharpness']}")
    print(f"  palette: navy+glass {r['navy_or_glass_pct']}%  navy {r['navy_coat_pct']}%  glass-blue {r['glass_blue_pct']}%  gold {r['gold_trim_pct']}%  core-glow {r['core_glow_pct']}%  eye-glow {r['eye_glow_pct']}%  on-palette {r['on_palette_pct']}%")
    print(f"  off-canon: red {r['off_canon_red_pct']}%  green {r['off_canon_green_pct']}%  pink {r['off_canon_pink_pct']}%")
    for n in r["notes"]: print("  - " + n)
    if not r["calibrated"]: print("  (uncalibrated defaults; run: grobie-image calibrate)")

# ---------- thumbs (byte-identical to the 13 live thumbs) ----------
def make_thumb(src, dst):
    im = Image.open(src).convert("RGB")
    if im.width > 1000: im = im.resize((800, round(im.height * 800 / im.width)), Image.LANCZOS)
    im.save(dst, "WEBP", quality=78, method=6); return im.size

# ---------- gallery.json writer (same layout as the existing files) ----------
def j(v): return json.dumps(v, ensure_ascii=False)
def dump_gallery(g):
    L = ["{"]; keys = list(g.keys())
    for ki, k in enumerate(keys):
        comma = "," if ki < len(keys) - 1 else ""
        v = g[k]
        if k == "items":
            L.append('  "items": [')
            for i, it in enumerate(v): L.append("    " + j(it) + ("," if i < len(v) - 1 else ""))
            L.append("  ]" + comma)
        elif k == "packs":
            L.append('  "packs": [')
            for pi, p in enumerate(v):
                L.append("    {"); pk = list(p.keys())
                for qi, q in enumerate(pk):
                    c2 = "," if qi < len(pk) - 1 else ""
                    if q == "items" and any(isinstance(x, dict) for x in p[q]):
                        L.append('      "items": [')
                        for xi, x in enumerate(p[q]): L.append("        " + j(x) + ("," if xi < len(p[q]) - 1 else ""))
                        L.append("      ]" + c2)
                    else: L.append(f'      {j(q)}: {j(p[q])}{c2}')
                L.append("    }" + ("," if pi < len(v) - 1 else ""))
            L.append("  ]" + comma)
        else: L.append(f"  {j(k)}: {j(v)}{comma}")
    L.append("}"); return "\n".join(L) + "\n"
def md5(p): return hashlib.md5(open(p, "rb").read()).hexdigest()
def slug(s): return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")
def today(): return datetime.datetime.now().strftime("%Y-%m-%d")  # box clock is America/Chicago

def add(a):
    gpath = os.path.abspath(a.gallery); gdir = os.path.dirname(gpath)
    protected = [os.path.abspath(p) for p in (getattr(a, "protected_prefixes", None) or os.environ.get("GROBIE_PROTECTED_PREFIXES", "").split(":")) if p]
    if protected and any(gpath.startswith(p) for p in protected) and not a.allow_source_folders:
        sys.exit("refusing to edit a protected gallery path; point --gallery at a copy (or pass --allow-source-folders)")
    raw = open(gpath, encoding="utf-8").read(); g = json.loads(raw)
    roundtrip = dump_gallery(g) == raw
    ext = os.path.splitext(a.image)[1].lower()
    base = a.name or os.path.splitext(os.path.basename(a.image))[0]
    base = slug(base); base = base if base.startswith("grobie-") else "grobie-" + base
    fname = base + ".jpg"; rel = f"{a.subdir.strip('/')}/{fname}"; dst = os.path.join(gdir, rel)
    tdst = os.path.join(gdir, "thumbs", base + ".webp"); trel = f"thumbs/{base}.webp"
    item_id = a.id or re.sub(r"^grobie-", "", base)
    items = g["items"]
    if any(it.get("id") == item_id for it in items) and not a.replace: sys.exit(f"id '{item_id}' already in gallery.json (use --replace or --id)")
    if any(it.get("file") == rel for it in items) and not a.replace: sys.exit(f"file '{rel}' already in gallery.json (use --replace)")
    if a.pack:
        packs = g.get("packs") or sys.exit("this gallery.json has no 'packs' list")
        pk = next((p for p in packs if p["id"] == a.pack), None) or sys.exit(f"pack '{a.pack}' not found; packs: {[p['id'] for p in packs]}")
    r = check(a.image, quiet=True, subject=a.subject)
    print_check(r)
    pr = prop_run(a.image)
    if a.require_pass and r["verdict"] != "PASS": sys.exit("check did not PASS; nothing written (--require-pass)")
    if a.require_pass and pr["verdict"] in ("WARN", "FAIL"): sys.exit(f"proportions {pr['verdict']}; nothing written (--require-pass)")
    os.makedirs(os.path.dirname(dst), exist_ok=True); os.makedirs(os.path.dirname(tdst), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S"); bak = gpath + ".bak-" + stamp
    shutil.copy2(gpath, bak)
    if ext in (".jpg", ".jpeg"):
        if os.path.exists(dst) and md5(dst) != md5(a.image) and not a.replace: sys.exit(f"{dst} exists with different content (use --replace)")
        shutil.copy2(a.image, dst)
    else:
        Image.open(a.image).convert("RGB").save(dst, "JPEG", quality=92, optimize=True)
    tsize = make_thumb(dst, tdst)
    entry = {}
    if any("id" in it for it in items) or a.pack: entry["id"] = item_id
    entry["title"] = a.title or base.replace("grobie-", "").replace("-", " ").capitalize()
    entry.update({"file": rel, "thumb": trel})
    if a.download: entry["download"] = a.download
    entry.update({"caption": a.caption, "section": a.section or ("pack" if a.pack else "archive"), "date": a.date or today()})
    if a.replace: items[:] = [it for it in items if it.get("id") != item_id and it.get("file") != rel]
    items.append(entry)
    if a.pack:
        ref = item_id if not any(isinstance(x, dict) for x in pk["items"]) else ({"id": item_id, "note": a.note} if a.note else {"id": item_id})
        if a.note and not any(isinstance(x, dict) for x in pk["items"]): print("  (note ignored: this pack lists plain ids)")
        pk["items"] = [x for x in pk["items"] if (x if isinstance(x, str) else x["id"]) != item_id] + [ref]
    if "updated" in g: g["updated"] = entry["date"] if entry["date"] > g["updated"] else g["updated"]
    out = dump_gallery(g); json.loads(out); open(gpath, "w", encoding="utf-8").write(out)
    print(f"\nAdded '{item_id}' (date {entry['date']}, NEW badge for 7 days){' to pack ' + a.pack if a.pack else ''}.")
    print(f"gallery.json layout preserved: {'yes (original re-serialized byte-identical)' if roundtrip else 'NO - original had a different layout; check the diff'}")
    print(f"backup of previous gallery.json: {bak}")
    print(f"thumb: {tsize[0]}x{tsize[1]} webp q78 method 6 (same rule as the 13 live thumbs)")
    print("\nFILES TO UPLOAD (only after the site owner's OK):")
    for local, remote in [(dst, rel), (tdst, trel), (gpath, "gallery.json")]:
        print(f"  {remote:55s} {os.path.getsize(local):>9,} bytes  md5 {md5(local)}  <- {local}")
    print("Then open https://grobie.slopcore.army/ and confirm the card shows.")

def cutout(a):
    from rembg import remove, new_session
    s = new_session("u2net"); im = Image.open(a.image).convert("RGB")
    out = remove(im, session=s); out.save(a.out); print(a.out, out.size, f"{os.path.getsize(a.out):,} bytes")

def calibrate(a):
    import glob
    rows = []
    def score(p, group):
        r = check(p, quiet=True); rows.append({"group": group, **{k: r[k] for k in ("file", "consistency", "sharpness", "navy_or_glass_pct", "gold_trim_pct", "off_canon_red_pct", "on_palette_pct", "size")}})
        print(f"{group:13s} {r['consistency']:.3f}  sharp {r['sharpness']:7.1f} navy+glass {r['navy_or_glass_pct']:5.1f} gold {r['gold_trim_pct']:5.2f} red {r['off_canon_red_pct']:5.2f}  {os.path.basename(p)}")
    canon = [os.path.join(KIT, f) for f, _ in REFS]
    V2 = {"grobie-face-lock-master", "grobie-mouth-shapes", "grobie-mouth-shapes-v2", "grobie-turnaround-clean"}  # v2-kit sheets, not refs
    VARIANT = {"grobie-cyber-mech-v1"}
    refkeys = {stem_key(p) for p in canon}
    for p in canon: score(p, "v2-ref-loo")
    for p in sorted(glob.glob(os.path.join(KIT, "*.jpg"))):
        k = stem_key(p)
        if k in V2: score(p, "v2-kit")
        elif k in VARIANT: score(p, "variant")
    older = getattr(a, "older_dir", None) or os.environ.get("GROBIE_OLDER_DIR")
    if older:
        for p in sorted(glob.glob(os.path.join(older, "*.jpg"))): score(p, "older-look")
    thumbs = getattr(a, "thumbs_dir", None) or os.environ.get("GROBIE_THUMBS_DIR")
    if thumbs:
        for p in sorted(glob.glob(os.path.join(thumbs, "*.webp"))):
            k = stem_key(p); score(p, "v2-thumb" if (k in V2 or k in refkeys) else "older-thumb")
    for p in a.negatives: score(p, "negative")
    def grp(gs, k="consistency"): return [r[k] for r in rows if r["group"] in gs]
    V = ["v2-ref-loo", "v2-kit", "v2-thumb"]; O = ["older-look", "older-thumb"]; ALLG = V + O + ["variant"]
    v2 = grp(V); old = grp(O); neg = grp(["negative"])
    th = {
        # PASS line: just under the weakest current-v2 image (leave-one-out for the 4 refs)
        "score_pass": round(min(v2) - 0.02, 3),
        # FAIL floor: just under the weakest real Grobie image of any era (so no real Grobie image FAILs);
        # non-Grobie images reached up to max(neg), so the band between floor and PASS is "check by eye"
        "score_warn": round(min(old + v2) - 0.01, 3),
        "navy_min": round(0.5 * min(grp(V, "navy_or_glass_pct")), 1),
        "gold_min": round(0.5 * min(grp(V, "gold_trim_pct")), 2),
        "sharp_min": round(0.3 * min(grp(ALLG, "sharpness")), 1),
        "red_max": round(max(1.0, 2 * max(grp(V, "off_canon_red_pct"))), 2)}
    rng = lambda xs: [round(min(xs), 3), round(max(xs), 3)] if xs else None
    summ = {"current_v2_kit_and_thumbs": rng(v2), "older_looks_and_thumbs": rng(old), "variant_cyber_mech": rng(grp(["variant"])),
            "negatives_non_grobie": rng(neg), "navy_or_glass_pct_v2": rng(grp(V, "navy_or_glass_pct")), "gold_pct_v2": rng(grp(V, "gold_trim_pct")),
            "sharpness_all_grobie": rng(grp(ALLG, "sharpness"))}
    json.dump({"date": today(), "thresholds": th, "ranges": summ, "rows": rows}, open(CALIB, "w"), indent=1)
    print("\nranges:", json.dumps(summ)); print("thresholds:", json.dumps(th)); print("saved", CALIB)

def aim_run(path, obj, hands=1, debug=None, vlm=False, quiet=False):
    import aim as A
    if debug is None:
        os.makedirs(os.path.join(HERE, "aim-debug"), exist_ok=True)
        debug = os.path.join(HERE, "aim-debug", f"{os.path.splitext(os.path.basename(path))[0]}-aim-{slug(obj)}-h{hands}.jpg")
    r = A.run(path, obj, hands, debug)
    if vlm: r["vlm_answer_advisory"] = A.vlm_vote(path, obj)
    if not quiet: print_aim(r)
    return r
def print_aim(r):
    print(f"AIM {r['verdict']}  {r['file']}  object '{r['object']}', hands required {r['hands_required']}")
    print(f"  {r['reason']}")
    if "hands" in r:
        print(f"  object score {r['object_score']}; hands found {r['hands_found']}, touching {r['hands_in_contact']}, gripping {r['hands_gripping']}")
        for i, h in enumerate(r["hands"], 1):
            print(f"  hand{i} {h['state']:15s} gap {h['gap_px']} px ({h['gap_pct_width']}% of width)  outline-on-object {h['border_share']}  reaching-away {h['far_share']}  closedness(solidity) {h['solidity']}  box {h['box']}")
    if r.get("vlm_answer_advisory"): print(f"  VLM second opinion (advisory, not used in verdict): {r['vlm_answer_advisory']}")
    if r.get("debug_image"): print(f"  debug image: {r['debug_image']}")
    if r.get("seconds"): print(f"  {r['seconds']} s")
def prop_run(path, debug=None, quiet=False):
    import proportions as PR
    if debug is None:
        os.makedirs(os.path.join(HERE, "prop-debug"), exist_ok=True)
        debug = os.path.join(HERE, "prop-debug", f"{os.path.splitext(os.path.basename(path))[0]}-prop.jpg")
    r = PR.run(path, debug)
    if not quiet: print_prop(r)
    return r
def print_prop(r):
    print(f"PROPORTIONS {r['verdict']}  {r['file']}")
    print(f"  {r['reason']}")
    if r.get("heads_tall") is not None and r["verdict"] != "N/A":
        th = r["thresholds"]
        print(f"  heads tall {r['heads_tall']} (WARN < {th['heads_warn']}, FAIL < {th['heads_fail']})  legs/height {r['leg_ratio']} (WARN < {th['leg_warn']}, FAIL < {th['leg_fail']})  legs in heads {r['legs_in_heads']} (WARN < {th['legs_in_heads_warn']}, FAIL < {th['legs_in_heads_fail']})")
        print(f"  crown y {r['crown_y']}, soles y {r['soles_y']}, height {r['height_px']} px, head {r['head_px']} px (eye-based {r['head_px_by_eye']}, nose-based {r['head_px_by_nose']}), hip line y {r['hip_y']}")
    for n in r.get("keypoint_problems", []):
        if n not in r["reason"]: print("  pose note: " + n)
    if not r.get("calibrated", True): print("  (uncalibrated defaults; run: grobie-image calibrate-proportions)")
    if r.get("debug_image"): print(f"  debug image: {r['debug_image']}")
    if r.get("seconds"): print(f"  {r['seconds']} s")
def calibrate_proportions(a):
    """Thresholds from the Proprietor-approved master; the canon turnaround views are measured as a cross-check."""
    import proportions as PR
    if md5(PROP_MASTER) != PROP_MASTER_MD5: sys.exit(f"master md5 {md5(PROP_MASTER)} != {PROP_MASTER_MD5}; refusing to calibrate")
    out_dir = os.path.join(HERE, "calib", "prop-views"); os.makedirs(out_dir, exist_ok=True)
    rows = []
    def meas(p, group):
        r = PR.run(p, os.path.join(HERE, "prop-debug", "calib-" + os.path.splitext(os.path.basename(p))[0] + "-prop.jpg"))
        rows.append({"group": group, "file": p, "verdict": r["verdict"], **{k: r.get(k) for k in ("heads_tall", "leg_ratio", "legs_in_heads", "full_figure", "reason", "debug_image")}})
        print(f"{group:16s} {r['verdict']:4s} heads {r.get('heads_tall')}  legs/height {r.get('leg_ratio')}  legs in heads {r.get('legs_in_heads')}  {os.path.basename(p)}")
        return r
    m = meas(PROP_MASTER, "master")
    if m["verdict"] == "N/A": sys.exit("master could not be measured; not writing thresholds")
    for f in ("grobie-turnaround-shine-v2.jpg", "grobie-turnaround-clean.jpg"):
        im = Image.open(os.path.join(KIT, f)).convert("RGB"); W, H = im.size
        for i in range(4):
            p = os.path.join(out_dir, f"{f[:-4]}-view{i + 1}.png"); im.crop((i * W // 4, 0, (i + 1) * W // 4, H)).save(p)
            meas(p, "canon-turnaround")
    # Grobie's suggested canon/warn pairs (6.8 heads -> WARN under 6.0; legs 0.50 -> WARN under 0.42) applied as RATIOS to
    # the master's own measurements, so the lines move with how this tool measures. FAIL is a bigger drop.
    hm, lm, lh = m["heads_tall"], m["leg_ratio"], m["legs_in_heads"]
    th = {"heads_warn": round(hm * 6.0 / 6.8, 2), "heads_fail": round(hm * 0.80, 2),
          "leg_warn": round(lm * 0.42 / 0.50, 3), "leg_fail": round(lm * 0.75, 3),
          "legs_in_heads_warn": round(lh * 0.85, 2), "legs_in_heads_fail": round(lh * 0.75, 2)}
    canon = [r for r in rows if r["group"] == "canon-turnaround" and r["verdict"] != "N/A"]
    rng = lambda k: [min(r[k] for r in canon), max(r[k] for r in canon)] if canon else None
    json.dump({"date": today(), "model": PR.MID + " (Apache-2.0)", "master": PROP_MASTER, "master_md5": PROP_MASTER_MD5,
               "master_measured": {"heads_tall": hm, "leg_ratio": lm, "legs_in_heads": lh},
               "canon_turnaround_range": {"heads_tall": rng("heads_tall"), "leg_ratio": rng("leg_ratio"), "legs_in_heads": rng("legs_in_heads")},
               "rule": "WARN = master x (6.0/6.8) heads, master x (0.42/0.50) legs/height, master x 0.85 legs-in-heads; FAIL = master x 0.80 / x 0.75 / x 0.75",
               "thresholds": th, "rows": rows}, open(PR.CAL, "w"), indent=1)
    print("thresholds:", json.dumps(th)); print("saved", PR.CAL)
def prompt(a):
    print(open(os.path.join(HERE, "prompt-kit.md"), encoding="utf-8").read())

def main():
    ap = argparse.ArgumentParser(prog="grobie-image", description=__doc__)
    ap.add_argument("--kit", help="folder of canonical Grobie stills (default: $GROBIE_KIT or ./kit next to this script)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("check", help="look (consistency/palette/resolution/sharpness) + body proportions [+ aim with --grip]"); c.add_argument("images", nargs="+"); c.add_argument("--json", action="store_true")
    c.add_argument("--subject", action="store_true", help="also score the cut-out subject (for busy scenes); uses the better score")
    c.add_argument("--grip", metavar="OBJECT", help="also run the aim/contact check: his hands must grip OBJECT")
    c.add_argument("--hands", type=int, default=None, help="hands that must grip (default 2 for --grip, 1 for aim)")
    c.add_argument("--vlm", action="store_true", help="add the advisory SmolVLM yes/no vote to the aim check")
    c.add_argument("--no-proportions", action="store_true", help="skip the body-proportion test (ViTPose)")
    pp = sp.add_parser("proportions", help="body-proportion test only: heads tall and leg length (ViTPose). FAIL exits 1, WARN 2, N/A 3")
    pp.add_argument("images", nargs="+"); pp.add_argument("--debug", help="debug overlay path (one image only; default image/prop-debug/...)"); pp.add_argument("--json", action="store_true")
    sp.add_parser("calibrate-proportions", help="measure the proportions master + canon turnarounds and write calib/proportions-calibration.json")
    m = sp.add_parser("aim", help="aim/contact check: do his hands touch and grip OBJECT? FAIL exits 1")
    m.add_argument("image"); m.add_argument("--object", required=True); m.add_argument("--hands", type=int, default=1, choices=[1, 2])
    m.add_argument("--debug", help="annotated debug image path (default image/aim-debug/...)"); m.add_argument("--vlm", action="store_true"); m.add_argument("--json", action="store_true")
    d = sp.add_parser("add", help="add an image to a gallery.json COPY + thumb, print upload list")
    d.add_argument("image"); d.add_argument("--caption", required=True); d.add_argument("--gallery", required=True)
    d.add_argument("--pack"); d.add_argument("--title"); d.add_argument("--id"); d.add_argument("--name", help="file base name (default: from the image name)")
    d.add_argument("--section", help="canonical|archive|kit|pack (default pack if --pack else archive)"); d.add_argument("--date", help="YYYY-MM-DD (default today, CST)")
    d.add_argument("--subdir", default="character"); d.add_argument("--download"); d.add_argument("--note", help="note for packs that use {id, note} entries")
    d.add_argument("--subject", action="store_true"); d.add_argument("--replace", action="store_true"); d.add_argument("--require-pass", action="store_true"); d.add_argument("--allow-source-folders", action="store_true")
    sp.add_parser("prompt", help="print the character-consistency prompt kit")
    k = sp.add_parser("cutout", help="background removal (rembg u2net) to a transparent PNG"); k.add_argument("image"); k.add_argument("-o", "--out", required=True)
    cal = sp.add_parser("calibrate", help="score existing images and write calibration.json"); cal.add_argument("--negatives", nargs="*", default=[])
    cal.add_argument("--older-dir", help="optional folder of earlier stills (or $GROBIE_OLDER_DIR)")
    cal.add_argument("--thumbs-dir", help="optional folder of webp thumbs (or $GROBIE_THUMBS_DIR)")
    a = ap.parse_args()
    if a.kit:
        os.environ["GROBIE_KIT"] = a.kit
    global KIT, PROP_MASTER
    KIT = kit_dir(); PROP_MASTER = os.path.join(KIT, "grobie-proportions-master-v1.jpg")
    code = {"PASS": 0, "WARN": 2, "FAIL": 1}
    if a.cmd == "check":
        rs = []
        for p in a.images:
            r = check(p, quiet=a.json, subject=a.subject, proportions=not a.no_proportions)
            parts = [("look", r["verdict"])]
            if "proportions" in r: parts.append(("proportions", r["proportions"]["verdict"]))
            if a.grip:
                ar = aim_run(p, a.grip, a.hands or 2, vlm=a.vlm, quiet=a.json); r["aim"] = ar; parts.append(("aim", ar["verdict"]))
            if len(parts) > 1:  # N/A (not a full standing figure) does not change the overall verdict
                worst = max([v for _, v in parts if v != "N/A"], key=lambda v: {"PASS": 0, "WARN": 1, "FAIL": 2}[v])
                if not a.json: print(f"OVERALL {worst}  (" + ", ".join(f"{k} {v}" for k, v in parts) + ")")
                r["overall"] = worst
            rs.append(r)
        if a.json: print(json.dumps(rs, indent=1, default=str))
        sys.exit((1 if any(r.get("overall", r["verdict"]) == "FAIL" for r in rs) else (2 if any(r.get("overall", r["verdict"]) == "WARN" for r in rs) else 0)))
    if a.cmd == "proportions":
        rs = [prop_run(p, a.debug if len(a.images) == 1 else None, quiet=a.json) for p in a.images]
        if a.json: print(json.dumps(rs, indent=1, default=str))
        vs = [r["verdict"] for r in rs]
        sys.exit(1 if "FAIL" in vs else (2 if "WARN" in vs else (3 if "N/A" in vs else 0)))
    if a.cmd == "aim":
        r = aim_run(a.image, a.object, a.hands, a.debug, a.vlm, quiet=a.json)
        if a.json: print(json.dumps(r, indent=1))
        sys.exit(code[r["verdict"]])
    {"add": add, "prompt": prompt, "cutout": cutout, "calibrate": calibrate, "calibrate-proportions": calibrate_proportions}[a.cmd](a)
if __name__ == "__main__": main()
