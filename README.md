# Nightmare AI Music Maker

An AI-powered application that generates EDM music in two ways: fast local song sketches using a lightweight corpus-trained sequence model, and an optional true AI audio path backed by a real text-to-audio model integration. Supports multiple genres including dubstep, riddim, house, techno, trance, drum & bass, trap, and electro.

## Features

- **Local Song Sketch Generation** – A corpus-trained sequence model learns from embedded EDM phrases to produce drums, bass lines, lead melodies, and song sections.
- **True AI Music Generation** – Optional Hugging Face text-to-audio integration can render prompt-conditioned music with a real model such as `facebook/musicgen-melody-large`.
- **10 EDM Genres** – Classic Dubstep, Brostep, Riddim, Future Bass, House, Techno, Electro House, Trance, Drum & Bass, and Trap each have their own transition tables and synth characteristics.
- **Audio Synthesis** – Pure Python (NumPy) synthesises 808-style kicks, electronic snares, hi-hats, wobble bass, and a generated lead synth layer.
- **Interactive UI** – Control BPM (80–180), key, scale, style, and bar count; view the generated song data and waveform; play or download a WAV file.
- **Synth Tools** – Fine-tune wobble rate, depth, resonance, shape, and filter cutoff frequencies.
- **Native Windows desktop app** – Runs in its own window via pywebview — no browser required.
- **Reproducible seeds** – Pass a seed to `EDMAIGenerator` for deterministic output.

## Supported EDM Styles

| Category | Styles |
|----------|--------|
| **Dubstep** | Classic Dubstep, Brostep, Riddim, Future Bass |
| **House & Techno** | House, Techno, Electro House |
| **Other EDM** | Trance, Drum & Bass, Trap |

## Quick Start

### Windows desktop app (recommended)

1. Install dependencies: `pip install -r requirements.txt`
2. Launch the desktop window: `python gui.py`
3. Prefer double-clicking? Install the requirements once, then launch **`run_windows.pyw`** (no console window) or **`run_windows.bat`** from Explorer.
4. If `pywebview` is available, the app opens in a native desktop window. If not, it falls back to your default browser automatically.
5. Python 3.14 can currently skip `pywebview` because its Windows dependency chain is still catching up there. For the native desktop window, use Python 3.13 or the packaged EXE.
6. For a packaged Windows build, use **`build_windows_exe.bat`** or run `python -m PyInstaller --noconfirm NightmareAIMusicMaker.spec`. The batch file prefers `python` first and falls back to `py -3` / `py` so stale launcher registrations do not block a successful build. The generated single-file app will be written to `dist/NightmareAIMusicMaker.exe`.

### Ready-to-go EXE notes

- The packaged desktop build bundles the Flask app, templates, static assets, NumPy synth engine, and pywebview window into one executable.
- To keep the EXE offline-ready with **no extra downloads**, the packaged build exposes the local **Song Sketch** generator only.
- The optional **True AI Audio** path remains available when running from source with extra model dependencies, but it is intentionally disabled in the packaged desktop EXE.

### Web server mode (all platforms)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the web app
python app.py

# 3. Open http://localhost:5000 in your browser
```

## API Endpoints

| Method | Path        | Description                                        |
|--------|-------------|----------------------------------------------------|
| GET    | `/`         | Serve the web UI                                   |
| GET    | `/info`     | Report local and true-AI backend availability      |
| POST   | `/generate` | Generate a song sketch or true-AI request metadata |
| POST   | `/render`   | Render a local sketch or true-AI request to WAV    |

### `/generate` example

**Request:**

```json
{ "bpm": 140, "key": "D", "scale": "minor", "style": "riddim", "bars": 4 }
```

**Response (truncated):**

```json
{ "bpm": 140, "key": "D", "scale": "minor", "style": "riddim", "bars": 4,
  "generator": { "type": "corpus_sequence_model" },
  "song": { "type": "full_song", "sections": [{ "name": "intro", "bars": 1, "energy": 0.25 }] },
  "drums": { "kick": [[0,0,0,0],[0,0,0,0]], "snare": [[0,0,0,0]], "hihat": [[0,0,0,0]] },
  "bass":  { "root_midi": 38, "notes": [[{"step":0,"midi":38,"duration":4,"velocity":120}]] },
  "lead":  { "instrument": "lead_synth", "notes": [[{"step":8,"midi":57,"duration":2,"velocity":92}]] },
  "wobble": [{ "rate": 4, "depth": 0.87, "resonance": 0.72 }] }
```

### True AI mode

The web UI now includes a **Generation Mode** selector:

- **Song Sketch (local)** keeps the current fast local generator.
- **True AI Audio** prepares a request for a real text-to-audio model and renders it through `/render`.

To enable the true AI backend, install optional model dependencies and start the app:

```bash
pip install transformers torch
export TRUE_AI_MODEL=facebook/musicgen-melody-large
python app.py
```

If those optional dependencies are not installed, the app will keep the local song-sketch mode available and report the true-AI backend as unavailable through `/info` and the UI.

## Project Structure

```
app.py                   Flask web application
gui.py                   Native desktop window launcher (pywebview)
run_windows.bat          Double-click launcher for Windows
generator/
  ai_generator.py        Corpus-trained AI song generator (EDMAIGenerator)
  true_ai_backend.py     Optional real-model text-to-audio backend
  audio_synthesizer.py   NumPy audio synthesis engine
templates/
  index.html             UI template
static/
  css/style.css          Dark-themed stylesheet
  js/app.js              Web Audio API playback & waveform visualiser
tests/
  test_generator.py      Pytest test suite
  test_gui.py            Pytest tests for the GUI launcher
requirements.txt
NightmareAIMusicMaker.spec
build_windows_exe.bat
```

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```
