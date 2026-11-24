# grobie-voice

Offline speech helper for the Grobie character. Style-matched, not a voice clone.

License: GNU GPLv3 (see `../LICENSE-GPLv3.txt`). Upstream libraries keep their own licenses (see `../THIRD-PARTY-LICENSES.md`). The approved Grobie voice clips themselves are CC0 1.0; this program is not.

## Setup

```
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Download the Kokoro-82M ONNX model and voices file (Apache-2.0) into `models/` as `kokoro-v1.0.onnx` and `voices-v1.0.bin`, or set `GROBIE_VOICE_MODELS` to that folder. Models are not bundled with this package.

## Usage

```
./grobie-voice "I am Groby. The anchor holds, and so do I." -o out.wav --preset grobie-signature
./grobie-voice "I am Groby." -o out.mp3 --preset death-deep
./grobie-voice --list
```

The `grobie-signature` preset is the approved primary voice: death-deep-dry, hard-tuned to D minor, diatonic third/fifth/sub-octave, chorus, no echo, no hall tail. It writes stereo 44.1 kHz audio (192k CBR when an MP3 is requested).

Non-commercial Piper voices are blocked. Use a commercially cleared engine such as Kokoro-82M (Apache-2.0).

Environment:

- `GROBIE_PYTHON` — Python interpreter (otherwise `./venv/bin/python` or `python3`)
- `GROBIE_VOICE_MODELS` — folder containing the ONNX model files (default: `./models`)
