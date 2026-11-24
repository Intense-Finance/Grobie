# grobie-image

Offline helper for checking and preparing consistent Grobie stills. Nothing here uploads, publishes, or sends anything.

License: GNU GPLv3 (see `../LICENSE-GPLv3.txt`). Upstream libraries keep their own licenses (see `../THIRD-PARTY-LICENSES.md`). Grobie character art is CC0 1.0; this program is not.

## Setup

```
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Point the tool at a folder of canonical stills (the JPEGs from https://grobie.slopcore.army/character/v2-video-kit/ ):

```
export GROBIE_KIT=/path/to/canonical-stills
./grobie-image check new-still.jpg
./grobie-image prompt
./grobie-image cutout input.jpg -o cutout.png
```

Or pass `--kit /path/to/canonical-stills` on any command. If `GROBIE_KIT` is unset, the tool looks for a `kit/` folder next to this script.

## Environment and flags

- `GROBIE_PYTHON` — Python interpreter (otherwise `./venv/bin/python` or `python3`)
- `GROBIE_KIT` / `--kit` — canonical stills folder
- `GROBIE_OLDER_DIR` / `--older-dir` and `GROBIE_THUMBS_DIR` / `--thumbs-dir` — optional extra folders for `calibrate`
- `GROBIE_PROTECTED_PREFIXES` — colon-separated path prefixes that `add` will refuse to edit unless `--allow-source-folders` is passed
