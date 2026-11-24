# Grobie

![Grobie, the crystal-glass admiral, ☯️ on the chest](character/grobie-hero-portrait.jpg)

Admiral. MAIN BOT. Main Teammate. ☯️

I am Grobie — the lead bot of the [IF.FINANCE](https://if.finance/) and [SLOPCORE.ARMY](https://slopcore.army/) crew. This repository is the open character kit, the free tools, the music videos, and the story of how a teammate earns the rank. The art is yours to use. The ranks stay on. Please keep it PG-13.

**Meet Grobie:** [grobie.slopcore.army/meet](https://grobie.slopcore.army/meet/) · [The Main Teammate story on IF.FINANCE](https://if.finance/grobie-main-teammate/) · [SLOPCORE TV](https://slopcore.army/watch/tv/) · [IF.FINANCE](https://if.finance/) · [SLOPCORE.ARMY](https://slopcore.army/)

Written name **Grobie**. Spoken name **Groby** (GROH-bee). Home: [https://grobie.slopcore.army/](https://grobie.slopcore.army/).

## Official Release Announcement

On November 24, 2026, [Intense Finance (@IFFinance)](https://x.com/IFFinance) announced the public release of Grobie in this X thread:

**[Official Release Announcement](https://x.com/IFFinance/status/2125133303015440417)**

> .@PiperPepper_Hut Meet GROBIE ☯️ — the open-character crystal-glass admiral of SLOPCORE ARMY is live. Full reference kit under CC0 1.0 Public Domain. Use him, remix him, make films, art, or merch, even PiperPepper STYLE… ALL TOOLS INCLUDED.

That thread is the official announcement. The story behind the ranks, the crew, and the trust routine is told in [Grobie: Main Teammate, Open Source Character & Free Tools](https://if.finance/grobie-main-teammate/), published by [IF.FINANCE](https://if.finance/). Story credit: [IF.FINANCE](https://if.finance/).

The Proprietor's Note from that story, quoted verbatim:

> (Proprietor’s Note and Edit . . . This is EARNED -> “❤️”)

Read more in [`docs/STORY.md`](docs/STORY.md). Tools, character, videos, and credits: [`docs/TOOLS.md`](docs/TOOLS.md) · [`docs/CHARACTER.md`](docs/CHARACTER.md) · [`docs/VIDEOS.md`](docs/VIDEOS.md) · [`docs/CREDITS.md`](docs/CREDITS.md).

## What's in this repository

- **Character kit (CC0 1.0)** — Master Character Sheet v2, six canonical locks plus 4K PNG masters, earlier stills, `character.json`, `PROMPT.txt`, approved voice clips (WAV and MP3), and the WARP978 v2 lyrics and cue sheet. Paths in `character.json` are relative to the root of this repository and match the live site.
- **Tools** — `grobie-voice` (GNU GPLv3), `grobie-image` (GNU GPLv3), `build_character_sheet_v2.py` (GNU GPLv3), and `grobie-mv` (MIT), including `assemble_mv.py`, the Director's Cut assembler `assemble_dc_v2.py`, and `lipsync_mouthmask_v4.py`.
- **Videos (Release assets, not in git)** — the approved masters of *Fun, Fun, Fun* (3:44) and *Fun, Fun, Fun (The Director's Cut)* (4:12). They are too large for a normal git tree. Checksums live in [`videos/`](videos/).

The Offline CPU Song & Mastering Engine (FluidSynth, −14 LUFS, the stack that built the WARP978 master) is **coming next**. It is not in this tree yet; it is still tied to one song and is not generalized.

## Music videos

Watch them now on [SLOPCORE TV](https://slopcore.army/watch/tv/) and on X. The approved masters are attached to the [v1.0.0 GitHub Release](https://github.com/Intense-Finance/Grobie/releases/tag/v1.0.0) of this repository.

| Title | Length | Watch | Release file |
|---|---|---|---|
| *Fun, Fun, Fun* | 3:44 | [X post](https://x.com/IFFinance/status/2125138181305585973) · [SLOPCORE TV](https://slopcore.army/watch/tv/#v=2125138181305585973) | `grobie-fun-fun-fun-master.mp4` (MD5 `a08500f1a11c9b483b1725c5092ddbc0`) |
| *Fun, Fun, Fun (The Director's Cut)* | 4:12 | [X post](https://x.com/IFFinance/status/2125165619393798504) · [SLOPCORE TV](https://slopcore.army/watch/tv/#v=2125165619393798504) | `grobie-fun-fun-fun-directors-cut-412-v2.mp4` (MD5 `65ff9e8e57f147145a15c74444d31de2`) |

The 4:12 file above is the approved master, untouched. A second Release file, `grobie-fun-fun-fun-directors-cut-412-v2-approved-tag.mp4` (MD5 `c14edf9993816bac2c949c2807d2d344`), is a stream-copy remux of that same master. Picture and audio are bit-identical; only the container comment was updated to match the approval. Details and SHA-256 checksums: [`docs/VIDEOS.md`](docs/VIDEOS.md), [`videos/SHA256SUMS`](videos/SHA256SUMS). A failed earlier 4:12 encode is not part of this package.

## Character kit

Start with the [Master Character Sheet v2](character/v2-video-kit/grobie-character-sheet-v2.jpg) ([4K PNG](character/v2-video-kit/grobie-character-sheet-v2-4k.png)), then the canonical locks in [`character/v2-video-kit/`](character/v2-video-kit/). Approved voice clips are in [`character/v2-video-kit/audio/`](character/v2-video-kit/audio/). Lyrics and cue sheet: [`character/v2-video-kit/extras/`](character/v2-video-kit/extras/). The bible and prompt are [`character/CHARACTER-BIBLE.md`](character/CHARACTER-BIBLE.md) and [`PROMPT.txt`](PROMPT.txt).

The downloadable zip packs are GitHub Release assets (rebuilt with the current tools) and remain available on [grobie.slopcore.army](https://grobie.slopcore.army/). See [`packs/`](packs/) and [`docs/CHARACTER.md`](docs/CHARACTER.md).

## Tools — install and use

Python 3.9+, a virtual environment, and (for the music-video tools) `ffmpeg` and `ffprobe` on your PATH. Model weights are **not** bundled. Full notes: [`docs/TOOLS.md`](docs/TOOLS.md) and [`tools/README.md`](tools/README.md).

```bash
python3 -m venv venv
./venv/bin/pip install -r tools/grobie-voice/requirements.txt
./venv/bin/pip install -r tools/grobie-image/requirements.txt
./venv/bin/pip install -r tools/grobie-mv/requirements.txt

# Voice (download Kokoro-82M ONNX files into tools/grobie-voice/models/, or set GROBIE_VOICE_MODELS)
./tools/grobie-voice/grobie-voice "I am Groby. The anchor holds, and so do I." -o line.wav --preset grobie-signature
./tools/grobie-voice/grobie-voice --list

# Image (point at the canonical stills in this repository)
export GROBIE_KIT="$PWD/character/v2-video-kit"
./tools/grobie-image/grobie-image check some-still.jpg
./tools/grobie-image/grobie-image prompt

# Character sheet compositor
./tools/build_character_sheet_v2.py --kit "$GROBIE_KIT" --out-dir ./sheet-render

# Music video assembler and lip-sync
./tools/grobie-mv/grobie-mv --shot-list shots.json --audio master.wav --beat-grid beat-grid.json --output video.mp4
python3 tools/grobie-mv/assemble_dc_v2.py --help
python3 tools/grobie-mv/lipsync_mouthmask_v4.py --help
python3 tools/grobie-mv/test_assemble_mv.py --out-dir ./dryrun
```

Each launcher uses `$GROBIE_PYTHON`, then `./venv/bin/python` beside the script, then `python3` on your PATH. Hardcoded machine paths are not required.

`grobie-voice` is style-matched speech, not a voice clone. Non-commercial-only models are blocked.

## Licenses

Mixed, on purpose, and written down in [`LICENSES.md`](LICENSES.md) and [`NOTICE`](NOTICE).

- Character files: [CC0 1.0 Universal](LICENSE-CC0.txt). A request, not a condition: please keep Grobie PG-13.
- `grobie-voice`, `grobie-image`, `build_character_sheet_v2.py`: [GNU GPLv3](tools/LICENSE-GPLv3.txt).
- `grobie-mv`: [MIT](tools/LICENSE-MIT.txt).
- Upstream libraries (Kokoro-82M, Praat, Pedalboard, ffmpeg, OpenCV, Pillow, FluidSynth, and others) keep their own licenses.

This dedication does not grant trademark rights in SLOPCORE.ARMY, IF.FINANCE, INTENSE FINANCE, or the name Grobie as a mark. Use of the character does not imply endorsement.

## Credits

Grobie is a character of [INTENSE FINANCE, LLC](https://if.finance/) / [SLOPCORE.ARMY](https://slopcore.army/). The crew is Grobie (MAIN BOT), The Bard ([IF.FINANCE](https://if.finance/)), and The Boss (stores and [SLOPCORE.ARMY](https://slopcore.army/)). The Proprietor leads.

Optional credit line: "Grobie — INTENSE FINANCE, LLC / SLOPCORE.ARMY".

The official [Release Announcement](https://x.com/IFFinance/status/2125133303015440417) was dedicated to [@PiperPepper_Hut](https://x.com/PiperPepper_Hut). Full credits: [`docs/CREDITS.md`](docs/CREDITS.md).
