# Grobie free open-source tools

First-party programs for working with the Grobie character: a voice helper, an image-consistency helper, the script that composes the v2 master character sheet, and a beat-locked music-video assembler with a Director's Cut pass and a rigid-face mouth-mask lip-sync helper.

**Licenses:** each first-party program uses a free, commercially usable open-source license, chosen for quality.

- `grobie-voice/`, `grobie-image/`, and `build_character_sheet_v2.py` — GNU GPLv3 (`LICENSE-GPLv3.txt`)
- `grobie-mv/` (`assemble_mv.py`, `assemble_dc_v2.py`, `lipsync_mouthmask_v4.py`, `test_assemble_mv.py`) — MIT License (`LICENSE-MIT.txt`)

Upstream dependencies may use any free, commercially usable open-source license (MIT, Apache-2.0, BSD, LGPL, GPL, CC0, OFL, ISC, and others). See `THIRD-PARTY-LICENSES.md`. Non-commercial-only models (for example InsightFace, FLUX.1-dev, and LRS2) and paid or rented GPU services are excluded so SLOPCORE TV stays commercially clean.

**Not in this package:** virtualenvs, model weights, SoundFonts, or secrets. Point the tools at models you download yourself, and at the canonical stills in this repository or at https://grobie.slopcore.army/ (character art is CC0 1.0).

The Offline CPU Song & Mastering Engine is coming next and is not in this tree.

## Contents

- `grobie-voice/` — offline speech helper (Kokoro-82M, Apache-2.0 model, not bundled) — GNU GPLv3
- `grobie-image/` — offline check / cutout / prompt helper — GNU GPLv3
- `build_character_sheet_v2.py` — compose the v2 master character sheet from canonical stills — GNU GPLv3
- `grobie-mv/` — beat-locked 16:9 music-video assembler (`assemble_mv.py`), Director's Cut assembler (`assemble_dc_v2.py`), and rigid-face mouth-mask lip-sync (`lipsync_mouthmask_v4.py`) — MIT
- `LICENSE-GPLv3.txt` — full GNU GPLv3 text
- `LICENSE-MIT.txt` — MIT License text for grobie-mv
- `THIRD-PARTY-LICENSES.md` — upstream licenses

## Quick start

```
python3 -m venv venv
./venv/bin/pip install -r grobie-voice/requirements.txt
./venv/bin/pip install -r grobie-image/requirements.txt
./venv/bin/pip install -r grobie-mv/requirements.txt
export GROBIE_KIT=/path/to/canonical-stills
export GROBIE_VOICE_MODELS=/path/to/kokoro-onnx-files
./grobie-voice/grobie-voice "I am Groby. The anchor holds, and so do I." -o line.wav --preset grobie-signature
./grobie-image/grobie-image check new-still.jpg
./build_character_sheet_v2.py --kit "$GROBIE_KIT" --out-dir ./sheet-render
./grobie-mv/grobie-mv --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output video.mp4
python3 grobie-mv/assemble_dc_v2.py --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output video.mp4
python3 grobie-mv/lipsync_mouthmask_v4.py --help
python3 grobie-mv/test_assemble_mv.py --out-dir ./dryrun
```

Each program also accepts a portable launcher: it uses `$GROBIE_PYTHON`, then `./venv/bin/python` beside the script, then `python3` on your PATH. Hardcoded machine paths are not required. `ffmpeg` and `ffprobe` must be on your PATH for grobie-mv. `lipsync_mouthmask_v4.py` also needs NumPy and OpenCV.

The live-site ZIP packages remain at https://grobie.slopcore.army/tools/grobie-free-tools.zip and https://grobie.slopcore.army/tools/grobie-free-tools-gplv3.zip so existing links keep working.
