# Tools

First-party programs for working with the Grobie character. They live in [`tools/`](../tools/) and were named in the official [Release Announcement](https://x.com/IFFinance/status/2125133303015440417). Full license notes: [`../tools/README.md`](../tools/README.md) and [`../tools/THIRD-PARTY-LICENSES.md`](../tools/THIRD-PARTY-LICENSES.md). Character art is [CC0 1.0](../LICENSE-CC0.txt); the programs are not.

## The set

| Program | License | What it does |
|---|---|---|
| [`grobie-voice`](../tools/grobie-voice/) | GNU GPLv3 | Offline, CPU speech helper. Style-matched, not a voice clone. Kokoro-82M (Apache-2.0, not bundled). |
| [`grobie-image`](../tools/grobie-image/) | GNU GPLv3 | Offline consistency, proportion, prompt, and cutout helper. Nothing here uploads or publishes. |
| [`build_character_sheet_v2.py`](../tools/build_character_sheet_v2.py) | GNU GPLv3 | Composes Master Character Sheet v2 from the canonical stills. Contain-fit only: no crop, no stretch, no AI regeneration. |
| [`grobie-mv`](../tools/grobie-mv/) | MIT | Beat-locked 16:9 music-video assembler (`assemble_mv.py`), Director's Cut assembler (`assemble_dc_v2.py`), and rigid-face mouth-mask lip-sync (`lipsync_mouthmask_v4.py`). |

**Coming next:** the Offline CPU Song & Mastering Engine (FluidSynth, −14 LUFS, the stack that built the WARP978 master). It is not in this tree yet.

Non-commercial-only models (for example InsightFace, FLUX.1-dev, and LRS2) and paid or rented GPU services are excluded so [SLOPCORE TV](https://slopcore.army/watch/tv/) stays commercially clean.

## Install

Python 3.9+ and a virtual environment. For `grobie-mv`, install `ffmpeg` and `ffprobe` with libx264 and AAC support and put them on your PATH. Model weights are not bundled. Download Kokoro-82M ONNX files into `tools/grobie-voice/models/`, or set `GROBIE_VOICE_MODELS`.

```bash
python3 -m venv venv
./venv/bin/pip install -r tools/grobie-voice/requirements.txt
./venv/bin/pip install -r tools/grobie-image/requirements.txt
./venv/bin/pip install -r tools/grobie-mv/requirements.txt
```

Each launcher uses `$GROBIE_PYTHON`, then `./venv/bin/python` beside the script, then `python3` on your PATH. Hardcoded machine paths are not required.

## Quick commands

```bash
./tools/grobie-voice/grobie-voice "I am Groby. The anchor holds, and so do I." -o line.wav --preset grobie-signature
./tools/grobie-voice/grobie-voice --list

export GROBIE_KIT="$PWD/character/v2-video-kit"
./tools/grobie-image/grobie-image check some-still.jpg
./tools/grobie-image/grobie-image prompt

./tools/build_character_sheet_v2.py --kit "$GROBIE_KIT" --out-dir ./sheet-render

./tools/grobie-mv/grobie-mv --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output video.mp4
python3 tools/grobie-mv/assemble_dc_v2.py --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output video.mp4
python3 tools/grobie-mv/lipsync_mouthmask_v4.py --clip closeup.mp4 --cues cues.json --song-start 160.0 --mouth 640,421,180,55 --out lipsync.mp4
python3 tools/grobie-mv/test_assemble_mv.py --out-dir ./dryrun
```

`lipsync_mouthmask_v4.py` is CPU-only and model-free: a smile-curved slit, amber spill, per-viseme width, and a small rate-limited jaw translate. It does not warp the head.

A portable dry-run of `assemble_mv.py` is included. Point it at `./dryrun` or any folder you choose. It does not need a production master.

The live-site ZIP packages remain at [https://grobie.slopcore.army/tools/grobie-free-tools.zip](https://grobie.slopcore.army/tools/grobie-free-tools.zip) and [https://grobie.slopcore.army/tools/grobie-free-tools-gplv3.zip](https://grobie.slopcore.army/tools/grobie-free-tools-gplv3.zip) so existing links keep working. This repository's `tools/` folder, and the packs on the [v1.0.0 Release](https://github.com/Intense-Finance/Grobie/releases/tag/v1.0.0), include the later MIT scripts.
