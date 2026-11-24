# grobie-mv

Beat-locked 16:9 music-video assembler and mastering tool for Grobie / SLOPCORE TV.

License: MIT (`LICENSE-MIT.txt`, also at `../LICENSE-MIT.txt`). Upstream libraries, fonts, and codecs keep their own free licenses (see `../THIRD-PARTY-LICENSES.md`). Grobie character art and the WARP978 lyrics and cue sheet are CC0 1.0; this program is not.

`assemble_mv.py` takes a JSON shot list, a mastered audio file, and a `beat-grid.json`, then writes a loud, broadcast-style MP4: H.264 High profile, 1280x720 or 1920x1080, yuv420p, AAC 256 kbps 48 kHz stereo, `+faststart`.

`assemble_dc_v2.py` is the Director's Cut assembler used for *Fun, Fun, Fun (The Director's Cut)* 4:12. Lip-sync close-up pixels are trimmed into a lossless intermediate; the only H.264 encode of those pixels is the final export.

`lipsync_mouthmask_v4.py` is a CPU-only, model-free rigid-face mouth-mask lip-sync helper: a smile-curved slit, amber spill, per-viseme width, and a small rate-limited jaw translate. It does not warp the head.

## Setup

```
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Install `ffmpeg` and `ffprobe` with libx264 and AAC support and put them on your PATH. Optional system fonts, if present, are used for title cards: Rajdhani (OFL-1.1, preferred) or DejaVu Sans (Bitstream Vera). No fonts are bundled.

## Usage

```
./grobie-mv --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output video.mp4
./grobie-mv --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output video-1080p.mp4 --resolution 1080p --fps 30
./grobie-mv --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output video.mp4 --title "Fun, Fun, Fun"
./grobie-mv --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output video.mp4 --no-grade --no-title-cards
python3 assemble_mv.py --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output video.mp4
python3 assemble_dc_v2.py --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output video.mp4
python3 lipsync_mouthmask_v4.py --clip closeup.mp4 --cues cues.json --song-start 160.0 --mouth 640,421,180,55 --out lipsync.mp4
```

### assemble_mv.py options

| Option | Default | Meaning |
|---|---|---|
| `--shot-list` | required | JSON shot list (schema in the `assemble_mv.py` header) |
| `--audio` | required | Mastered audio (WAV preferred) |
| `--beat-grid` | required | JSON grid with at least `bar_sec` (default 2.0) and `duration_sec` |
| `--output` | shot list `output`, if set | Destination MP4 |
| `--resolution` | `720p` | `720p` (1280x720) or `1080p` (1920x1080) |
| `--fps` | `24` | `24`, `25`, or `30` |
| `--no-grade` | off | Skip the unified cinematic color grade |
| `--no-title-cards` | off | Skip opening title, hit, and end cards |
| `--audio-start` | `0` | Start reading the audio and grid at this time (seconds) |
| `--duration` | to end of audio/grid | Output length in seconds |
| `--crf` | `18` | libx264 quality |
| `--title` / `--artist` / `--album` | from the shot list | MP4 metadata (the MP4 title metadata defaults to the shot-list title) |
| `--keep-temp` | off | Leave the working directory in place for inspection |

Shot times may be given as inclusive `start_bar` / `end_bar` from the beat grid, or as `start_sec` / `end_sec`. Fit modes: `trim`, `stretch`, `loop`, `ken_burns`. Transitions into a shot: `cut`, `crossfade`, `flash`, `dip_black`. Grades: `default` (dark steel + cyan/amber), `shadow_fault`, `gold_blaze`, `storm`, `none`.

Environment:

- `GROBIE_PYTHON` — Python interpreter (otherwise `./venv/bin/python` or `python3`)

## Portable dry-run

`test_assemble_mv.py` builds synthetic clips and, if you do not pass a master, a short tone and 120 BPM beat grid, then assembles 720p and 1080p proofs.

```
python3 test_assemble_mv.py
python3 test_assemble_mv.py --out-dir ./dryrun
python3 test_assemble_mv.py --audio /path/to/master.wav --beat-grid /path/to/beat-grid.json --out-dir ./dryrun
```

Hardcoded machine paths are not required.
