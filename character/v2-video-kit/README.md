# Grobie v2 video kit — file inventory

Released for external sharing on November 23, 2026 (5:17–5:18 PM America/Chicago) so the first Grobie video can be built. This kit is tool-agnostic: any image, video, or voice software can use it. Fetch https://grobie.slopcore.army/character.json and https://grobie.slopcore.army/PROMPT.txt for automated ingest.

License: character files in this folder, including approved audio and the WARP978 extras, are CC0 1.0 Universal (https://grobie.slopcore.army/LICENSE.txt). Optional first-party tools at https://grobie.slopcore.army/tools/ use free, commercially usable open-source licenses (GPLv3 or MIT, per program).

## Upscale method

JPEG locks have a PNG master with the suffix `-4k.png`. Square sources were scaled to 4096x4096, 16:9 sources to 3840x2160, 3:4 sources to 3072x4096, and 4:3 sources to 4096x3072. Upscale method: interpolated resize (Pillow LANCZOS plus a light unsharp mask, radius 1.2, percent 60, threshold 3), not an AI upscaler. The v2 master character sheet 4K plate is a native 3840x2160 composite, not an interpolated resize.

## Files in this folder

| File | Size (px) | Bytes | md5 | Notes |
|---|---:|---:|---|---|
| `VIDEO-KIT.md` | — | 15,954 | `7236a6d03cad2e6e51b65b40b5674dd0` | Kit guide: prompt, locks, colors, scale, NEVER-DO, visemes, voice (primary vs WIP), extras, tools, first-video notes |
| `audio/APPROVED-grobie-signature-reference-20261123.mp3` | — | 70,887 | `92f2b8600e1bb76e067d7f4b3f638258` | Approved Primary Voice — signature reference, MP3 (Kokoro-82M, Apache-2.0) |
| `audio/APPROVED-grobie-signature-reference-20261123.wav` | — | 508,834 | `4c9cd4daf9784b2bf8d52ee2eb2b507d` | Approved Primary Voice — signature reference, uncompressed PCM 16-bit 44.1 kHz stereo (decoded from the approved MP3). Prefer this for lip-sync and voice tools. |
| `audio/grobie-death-deep.mp3` | — | 120,332 | `d5d863ed76e4bfe4dc549708f4c10bf3` | Approved Primary Voice — base DEATH-style voice, MP3 |
| `audio/grobie-death-deep.wav` | — | 852,260 | `5a1c4b88fd5285e27791150a9b32e1fb` | Approved Primary Voice — base DEATH-style voice, lossless WAV (original 24 kHz PCM) |
| `audio/grobie-signature-line-1-anchor-holds.mp3` | — | 110,384 | `33ef4a341bdeb5c6123d8fdec6e8a780` | Approved Primary Voice — mandatory first-video line, MP3: "I am Groby. The anchor holds, and so do I." |
| `audio/grobie-signature-line-1-anchor-holds.wav` | — | 797,498 | `317f60974295c3821ee79482250f3347` | Approved Primary Voice — mandatory first-video line, lossless WAV |
| `audio/grobie-signature-v1.mp3` | — | 195,021 | `f6a5af9d2696df94abbade3f145e7b7f` | Approved Primary Voice — extended signature reference, MP3 |
| `audio/grobie-signature-v1.wav` | — | 1,422,670 | `6e6e4c73a6e029c5e3bd92a46052de4c` | Approved Primary Voice — extended signature reference, lossless WAV |
| `audio/grobie-tv-match-v2-signature-line.mp3` | — | 248,937 | `2fa09c5d8e1fd7d6e59f5bc39f04e5ba` | WIP alternate voice target — SLOPCORE TV style v2, not yet owner-reviewed (approved signature voice is primary) |
| `audio/grobie-tv-match-v2-welcome.mp3` | — | 219,471 | `b1f6b233a5c2bd508b85fb24ca72fd66` | WIP alternate voice target — SLOPCORE TV style v2 welcome, not yet owner-reviewed (approved signature voice is primary) |
| `extras/warp978-cue-sheet-v2.csv` | — | 752 | `d53a5d8094613fb200f0df5fa78b1e6f` | EXTRAS — WARP978 v2 machine-readable cue sheet (CC0 1.0 Universal) |
| `extras/warp978-song-v2.md` | — | 9,128 | `be190f99f5d83dc35d71e1a79fe7664c` | EXTRAS — WARP978 v2 lyrics, written by The Bard (CC0 1.0 Universal) |
| `grobie-character-sheet-v2-4k.png` | 3840x2160 | 4,453,335 | `1f291a93a244e61bd7c8f408ba037f85` | 4K master of the v2 character sheet (3840x2160) |
| `grobie-character-sheet-v2.jpg` | 1920x1080 | 520,241 | `82df11a38440136481d67a80f4c97921` | CANONICAL — LEAD master character sheet v2 (studio composite of the locked looks, palette, specs, and extras) |
| `grobie-cyber-mech-v1-4k.png` | 3840x2160 | 5,747,666 | `8ce08b26d5b741891b0994e6a88b8a48` | 4K master of the Cyber-Mech Direction still (interpolated resize) |
| `grobie-cyber-mech-v1.jpg` | 1280x720 | 295,507 | `7803a184131b22b1e377b6101abe585b` | SECTION 9 — Cyber-Mech Direction look basis (less anime, more real human or real bot look). Not a replacement for the six canonical locks. |
| `grobie-face-lock-master-4k.png` | 4096x4096 | 10,833,201 | `4a70de24a16637505c2eee94af2a8a9d` | 4K master of the earlier face bust (interpolated resize) |
| `grobie-face-lock-master.jpg` | 1024x1024 | 382,619 | `74b6f87c6a9f24c2ed2f417df7904400` | Earlier face bust (kept). Not the outfit, collar, or core lock: it still shows a ribcage and a taller split collar. |
| `grobie-going-for-anchor-v1-4k.png` | 4096x3072 | 10,196,525 | `c8895b5c6f8bb9f5904b11e98988d1db` | 4K master of the approved anchor-lunge gag art (interpolated resize) |
| `grobie-going-for-anchor-v1.jpg` | 1152x864 | 403,073 | `fc67ff65a16108c7259c2ee3afe2c233` | ANCHOR PACK — approved anchor-lunge gag art |
| `grobie-grabs-anchor-v2-4k.png` | 4096x3072 | 9,270,526 | `530d1dc73ba28e961131609c974338a2` | 4K master of the approved grab pose (interpolated resize) |
| `grobie-grabs-anchor-v2.jpg` | 1152x864 | 367,195 | `0af35e062b6aa1b09ee129709ee8ed5a` | ANCHOR PACK — approved grab pose |
| `grobie-head-turnaround-v2-4k.png` | 3840x2160 | 5,274,741 | `3ae94adc8e149f28af1932b8d3368958` | 4K master of the head lock (interpolated resize) |
| `grobie-head-turnaround-v2.jpg` | 1280x720 | 293,266 | `c219a3388a80e5e2cbc960453cb5cbb3` | CANONICAL — head lock (front, 3/4, profile, back) |
| `grobie-mouth-shapes-4k.png` | 4096x4096 | 17,035,980 | `b9db72bad5749d321a6d860f2fb9c7eb` | 4K master of superseded v1 visemes (interpolated resize) |
| `grobie-mouth-shapes-v2-4k.png` | 4096x4096 | 15,562,560 | `52e8b52771eda92b9d9043d9b5961cc0` | 4K master of superseded v2 visemes (interpolated resize) |
| `grobie-mouth-shapes-v2.jpg` | 1024x1024 | 536,187 | `a1b8d9e706bb3fe04a0953bfaf1d6e31` | Superseded v2 viseme sheet (kept) |
| `grobie-mouth-shapes-v3-4k.png` | 4096x4096 | 16,159,822 | `9e35ff3037cf375ce27fb9a21a40c0f0` | 4K master of the v3 viseme sheet (interpolated resize) |
| `grobie-mouth-shapes-v3.jpg` | 1024x1024 | 551,057 | `f4e20f2b6b087b2a082686e18c17620d` | CANONICAL — viseme sheet (rest, AH, EE, OH, OO/W, M/B/P, F/V, L/TH, S) |
| `grobie-mouth-shapes.jpg` | 1024x1024 | 579,495 | `44af513003199afa5c0ac625b48b38e0` | Superseded v1 viseme sheet (kept) |
| `grobie-outfit-master-v2-4k.png` | 3072x4096 | 5,140,898 | `3d1224fe771bcf26a02d9d9895efc959` | 4K master of the outfit lock (interpolated resize) |
| `grobie-outfit-master-v2.jpg` | 864x1152 | 227,610 | `4212236991302f0ca3f89cd77413abff` | CANONICAL — outfit lock |
| `grobie-proportions-master-v1-4k.png` | 3072x4096 | 7,609,929 | `e8330457498c9631dcf46ceee805f729` | 4K master of the proportions lock (interpolated resize) |
| `grobie-proportions-master-v1.jpg` | 864x1152 | 306,307 | `118825eb55e1153ece7a28ff53918df4` | CANONICAL — PRIMARY body-proportions lock (tall/slim, ~6.8 heads, two-hand grip on the anchor shank). Also the lead image of the Anchor Pack. |
| `grobie-turnaround-clean-4k.png` | 3840x2160 | 4,952,028 | `8e96d040a5da8269ec0853b1dd109925` | 4K master of superseded v1 turnaround (interpolated resize) |
| `grobie-turnaround-clean.jpg` | 1280x720 | 272,296 | `e7e6020da265785fe75d2bac29c186ae` | Superseded v1 full-body turnaround (kept; open coat, visible skeleton) |
| `grobie-turnaround-shine-v2-4k.png` | 3840x2160 | 3,754,573 | `254e440373b8a571315ea382a47ae3cd` | 4K master of the shine turnaround (interpolated resize) |
| `grobie-turnaround-shine-v2.jpg` | 1280x720 | 218,845 | `255acb7ff7b46ab8b98b48b1c986f44c` | Full-body reference (navy trousers and boots, energy core, no skeleton). Outfit master still locks the coat, collar, and badges. |
| `README.md` | — | (this file) | — | This inventory |

## Related files outside this folder

- https://grobie.slopcore.army/character.json — tool-agnostic JSON manifest for any bot or video software.
- https://grobie.slopcore.army/PROMPT.txt — plain UTF-8 prompt kit.
- https://grobie.slopcore.army/character/CHARACTER-BIBLE.md — character bible.
- https://grobie.slopcore.army/LICENSE.txt — license policy: CC0 1.0 for character files (including WARP978 lyrics and cue sheet); free commercially usable open-source licenses for first-party tools (GPLv3 or MIT, per program).
- https://grobie.slopcore.army/tools/grobie-free-tools.zip — optional first-party voice, image, character-sheet, and music-video tools.
- https://grobie.slopcore.army/tools/grobie-free-tools-gplv3.zip — earlier GPLv3 bundle (still available).
- https://grobie.slopcore.army/tools/grobie-mv/README.md — grobie-mv assembler (MIT).
- https://grobie.slopcore.army/tools/LICENSE-GPLv3.txt — full official GNU GPLv3 text.
- https://grobie.slopcore.army/tools/LICENSE-MIT.txt — MIT License text for grobie-mv.
- https://grobie.slopcore.army/tools/THIRD-PARTY-LICENSES.md — upstream licenses for the tools.
- https://grobie.slopcore.army/packs/grobie-piper-video-kit.zip — Piper video kit (six canonical locks including the v2 master character sheet, Anchor Pack, Cyber-Mech Direction, approved and WIP audio, WARP978 extras, docs, character.json, PROMPT.txt, and the free tools including grobie-mv).
- https://grobie.slopcore.army/packs/grobie-full-archive.zip — the Piper kit plus superseded v1/v2 sheets, earlier character stills, and the free tools including grobie-mv.

## Earlier stills (not in this folder; non-canonical for video)

- https://grobie.slopcore.army/character/grobie-hero-portrait.jpg and https://grobie.slopcore.army/character/grobie-featured.jpg are the same file (both 1280x720, 403,610 bytes, MD5 `b19b868985a9ed087d109be9c346a09b`). They are **non-canonical for video**.
- https://grobie.slopcore.army/character/grobie-radiant-earned.jpg is a warmer recolor of that same hero composition (different MD5). It is **non-canonical for video**.
- The other parent-folder looks (https://grobie.slopcore.army/character/grobie-character-sheet-v1.jpg, https://grobie.slopcore.army/character/grobie-sir-grobie.jpg, https://grobie.slopcore.army/character/grobie-warp978-pirate.jpg) are 1280x720 stills with unlocked faces and, in several cases, baked-in text. They are **non-canonical for video**.
