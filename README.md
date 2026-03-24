# Nightmare AI Music Maker

An AI-powered application that generates authentic EDM music using Markov-chain models and real-time audio synthesis. Supports multiple genres including dubstep, riddim, house, techno, trance, drum & bass, trap, and electro.

## Features

- **AI Pattern Generation** – Markov-chain models produce drum patterns, bass lines, and synth parameters that follow real EDM music-theory rules.
- **10 EDM Genres** – Classic Dubstep, Brostep, Riddim, Future Bass, House, Techno, Electro House, Trance, Drum & Bass, and Trap each have their own transition tables and synth characteristics.
- **Audio Synthesis** – Pure Python (NumPy) synthesises 808-style kicks, electronic snares, hi-hats, and wobble bass with LFO filter modulation.
- **Interactive UI** – Control BPM (80–180), key, scale, style, and bar count; view the pattern grid and waveform; play or download a WAV file.
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
| POST   | `/generate` | Generate a pattern (JSON body → JSON response)     |
| POST   | `/render`   | Render a pattern or params to a downloadable WAV   |

### `/generate` example

**Request:**

```json
{ "bpm": 140, "key": "D", "scale": "minor", "style": "riddim", "bars": 4 }
```

**Response (truncated):**

```json
{ "bpm": 140, "key": "D", "scale": "minor", "style": "riddim", "bars": 4,
  "drums": { "kick": [[0,0,0,0],[0,0,0,0]], "snare": [[0,0,0,0]], "hihat": [[0,0,0,0]] },
  "bass":  { "root_midi": 38, "notes": [[38,0,38,0]] },
  "wobble": [{ "rate": 4, "depth": 0.87, "resonance": 0.72 }] }
```

## Project Structure

```
app.py                   Flask web application
gui.py                   Native desktop window launcher (pywebview)
run_windows.bat          Double-click launcher for Windows
generator/
  ai_generator.py        Markov-chain AI pattern generator (EDMAIGenerator)
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
```

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```
