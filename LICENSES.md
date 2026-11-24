# License map

Every first-party file in this repository is covered by one of the licenses below. Upstream dependencies keep their own licenses; see [NOTICE](NOTICE) and [tools/THIRD-PARTY-LICENSES.md](tools/THIRD-PARTY-LICENSES.md).

## Folder map

| Path | License | Notes |
|---|---|---|
| `LICENSE-CC0.txt`, `character/LICENSE.txt` | CC0 1.0 Universal (legal code + character policy) | Policy text names what the CC0 covers and what it does not (trademarks). |
| `character/` | CC0 1.0 Universal | Character art, 4K masters, earlier stills, bible, video-kit docs, approved voice clips, WARP978 v2 lyrics and cue sheet. |
| `character.json`, `PROMPT.txt` | CC0 1.0 Universal | Canonical machine-readable kit and prompt. |
| `packs/` | Documentation is CC0 1.0; the zip files themselves are Release assets, not in git | The zips bundle CC0 character files plus a snapshot of the tools (those tool copies keep GPLv3 / MIT). |
| `videos/` | Documentation is CC0 1.0; the approved MP4 masters are Release assets, not in git | The videos use the CC0 character and lyrics; the assembler that built them is MIT. |
| `tools/grobie-voice/` | GNU GPLv3 | First-party voice helper. Kokoro-82M and other deps keep their own licenses. |
| `tools/grobie-image/` | GNU GPLv3 | First-party image helper. |
| `tools/build_character_sheet_v2.py` | GNU GPLv3 | Compositor for Master Character Sheet v2. |
| `tools/LICENSE-GPLv3.txt` | GNU GPLv3 legal code | Official text. Do not edit. |
| `tools/grobie-mv/` | MIT License | `assemble_mv.py`, `assemble_dc_v2.py`, `lipsync_mouthmask_v4.py`, `test_assemble_mv.py`, launcher. |
| `tools/grobie-mv/LICENSE-MIT.txt`, `tools/LICENSE-MIT.txt` | MIT License legal code | Official text. Do not edit. |
| `tools/README.md`, `tools/THIRD-PARTY-LICENSES.md` | Documentation accompanying the tools | Describes the split licenses; not a substitute for the legal codes. |
| `docs/` | CC0 1.0 Universal | Story, tools, character, videos, and credits documentation. Story credit: [IF.FINANCE](https://if.finance/). |
| `README.md`, `LICENSE.md`, `LICENSES.md`, `NOTICE`, `.gitignore`, `.gitattributes` | CC0 1.0 Universal | Repository orientation and license map. |

The earlier downloadable bundles at https://grobie.slopcore.army/tools/grobie-free-tools.zip and https://grobie.slopcore.army/tools/grobie-free-tools-gplv3.zip remain available so existing links keep working. This repository's `tools/` folder is the source and includes later MIT scripts (`assemble_dc_v2.py`, `lipsync_mouthmask_v4.py`) that those zips may not yet contain.

## What is not licensed here

- Trademarks and trade names: SLOPCORE.ARMY, IF.FINANCE, INTENSE FINANCE, and the name Grobie used as a mark.
- Third-party model weights (Kokoro-82M and optional image models). They are not bundled. Download them from their upstream projects under those projects' licenses.
- Non-commercial-only models (for example InsightFace, FLUX.1-dev, and LRS2) and paid or rented GPU services are excluded from this project on purpose.

## Full legal texts

- CC0 1.0 Universal (with the character policy preamble): [LICENSE-CC0.txt](LICENSE-CC0.txt)
- GNU GPLv3: [tools/LICENSE-GPLv3.txt](tools/LICENSE-GPLv3.txt)
- MIT License: [tools/LICENSE-MIT.txt](tools/LICENSE-MIT.txt)
