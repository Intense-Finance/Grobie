# Third-party licenses

First-party programs in this `tools/` package each use a free, commercially usable open-source license, chosen for quality: `grobie-voice`, `grobie-image`, and `build_character_sheet_v2.py` are GNU GPLv3 (see `LICENSE-GPLv3.txt`); `grobie-mv` (`assemble_mv.py`, `assemble_dc_v2.py`, `lipsync_mouthmask_v4.py`) is MIT (see `LICENSE-MIT.txt`). The libraries, fonts, models, and codecs they use keep their own free licenses. This file lists the upstream dependencies those programs actually import, plus the free commercial-clean tools used to master WARP978 audio. None of these dependencies are bundled here except as you install them yourself.

Upstream dependencies may use any free, commercially usable open-source license (MIT, Apache-2.0, BSD, LGPL, GPL, CC0, OFL, ISC, and others). Non-commercial-only models (for example InsightFace, FLUX.1-dev, and LRS2) and paid or rented GPU services are excluded so SLOPCORE TV stays commercially clean.

## grobie-voice (GNU GPLv3)

| Dependency | Used for | License (as published by the upstream project) |
|---|---|---|
| Kokoro-82M (`kokoro-v1.0.onnx`, `voices-v1.0.bin`) | Speech model (not bundled; download separately) | Apache-2.0 |
| kokoro-onnx | ONNX runtime wrapper for Kokoro | MIT |
| onnxruntime | Model inference | MIT |
| NumPy | Audio arrays | BSD-3-Clause |
| SoundFile | WAV I/O | BSD-3-Clause |
| Praat / praat-parselmouth | Pitch, formant, and gender-change processing | GNU GPLv3 |
| Pedalboard | Filters, chorus, reverb, limiter | GNU GPLv3 |
| piper-tts (optional) | Optional alternate speech engine | MIT |

## grobie-image (GNU GPLv3)

| Dependency | Used for | License (as published by the upstream project) |
|---|---|---|
| Pillow | Image I/O and compositing | MIT-CMU (PIL / Pillow) |
| NumPy | Array math | BSD-3-Clause |
| rembg | Background removal (`cutout`) | MIT |
| onnxruntime | rembg model inference | MIT |
| scikit-image | Color difference and morphology | BSD-3-Clause |
| SciPy | Image morphology helpers | BSD-3-Clause |
| PyTorch (optional) | Consistency embeddings, pose, and aim checks | BSD-style (PyTorch) |
| transformers / Hugging Face (optional) | OWL-ViT, SAM, ViTPose, optional VLM | Apache-2.0 |

## build_character_sheet_v2.py (GNU GPLv3)

| Dependency | Used for | License (as published by the upstream project) |
|---|---|---|
| Pillow | Compositing the v2 master character sheet | MIT-CMU (PIL / Pillow) |

## grobie-mv (`assemble_mv.py`, `assemble_dc_v2.py`, `lipsync_mouthmask_v4.py`, MIT)

| Dependency | Used for | License (as published by the upstream project) |
|---|---|---|
| ffmpeg / ffprobe | Trim, grade, concatenate, and mux the finished MP4 | LGPL or GPL, depending on the build |
| libx264 (via ffmpeg) | H.264 High-profile video encode | GPL |
| Pillow | Title, hit, and end cards | MIT-CMU (PIL / Pillow) |
| fontTools (optional) | Glyph-coverage checks for title-card fonts | MIT |
| NumPy | Arrays for `lipsync_mouthmask_v4.py` | BSD-3-Clause |
| OpenCV (`opencv-python-headless`) | Optical-flow tracking and drawing for `lipsync_mouthmask_v4.py` | Apache-2.0 |
| Rajdhani | Preferred title-card typeface, if installed on the system (not bundled) | OFL-1.1 |
| DejaVu Sans | Fallback title-card typeface, if installed on the system (not bundled) | Bitstream Vera |

## Audio mastering toolchain (WARP978 master; free commercial-clean stack)

These tools were used to compose and master the WARP978 audio track. They are not all imported by `assemble_mv.py`. They are documented here so a rebuild can stay commercially clean. The Offline CPU Song & Mastering Engine that wraps this stack is coming next and is not in this tree.

| Dependency | Used for | License (as published by the upstream project) |
|---|---|---|
| FluidSynth | SoundFont playback / orchestration | LGPL-2.1-or-later |
| FluidR3_GM.sf2 | General MIDI SoundFont (not bundled) | MIT |
| mido | MIDI file I/O | MIT |
| pyloudnorm | ITU-R BS.1770 loudness measurement and -14 LUFS mastering | MIT |
| NumPy | Audio arrays | BSD-3-Clause |
| SciPy | Signal processing | BSD-3-Clause |
| SoundFile | WAV I/O | BSD-3-Clause |
| Kokoro-82M / kokoro-onnx | Sung and spoken vocal rendering | Apache-2.0 / MIT |
| Praat / praat-parselmouth | Vocal pitch and formant processing | GNU GPLv3 |
| Pedalboard | Vocal and mix processing (chorus, reverb, compression) | GNU GPLv3 |
| faster-whisper / Systran `small.en` | Optional speech-recognition QA of the vocal stem (not bundled) | MIT |
| ffmpeg | Format conversion and preview encodes | LGPL or GPL, depending on the build |

If a listed license conflicts with how you want to use a tool, do not use that optional extra, or follow that upstream license for the combination. Character art, docs, approved voice clips, and the WARP978 lyrics and cue sheet are not covered by the tool licenses; they are CC0 1.0 Universal (see ../LICENSE-CC0.txt and https://grobie.slopcore.army/LICENSE.txt).
