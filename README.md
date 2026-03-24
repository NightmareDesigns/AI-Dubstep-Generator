# AI Dubstep Generator

An AI-powered web application that generates authentic dubstep music using Markov-chain models and real-time audio synthesis.

## Features

- **AI Pattern Generation** – Markov-chain models produce drum patterns, bass lines, and wobble parameters that follow real dubstep music-theory rules.
- **Three sub-genres** – Classic Dubstep, Brostep, and Future Bass each have their own transition tables and wobble characteristics.
- **Audio Synthesis** – Pure Python (NumPy/SciPy) synthesises 808-style kicks, electronic snares, hi-hats, and wobble bass with LFO filter modulation.
- **Interactive Web UI** – Control BPM (80–180), key, scale, style, and bar count; view the pattern grid and waveform; play in-browser or download a WAV file.
- **Reproducible seeds** – Pass a seed to `DubstepAIGenerator` for deterministic output.

## Quick Start

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

```json
// Request
{ "bpm": 140, "key": "D", "scale": "minor", "style": "brostep", "bars": 4 }

// Response (truncated)
{ "bpm": 140, "key": "D", "scale": "minor", "style": "brostep", "bars": 4,
  "drums": { "kick": [[…],[…],…], "snare": [[…],…], "hihat": [[…],…] },
  "bass":  { "root_midi": 38, "notes": [[…],…] },
  "wobble": [{ "rate": 4, "depth": 0.87, "resonance": 0.72, … }, …] }
```

## Project Structure

```
app.py                   Flask web application
generator/
  ai_generator.py        Markov-chain AI pattern generator
  audio_synthesizer.py   NumPy/SciPy audio synthesis engine
templates/
  index.html             Web UI template
static/
  css/style.css          Dark-themed stylesheet
  js/app.js              Web Audio API playback & waveform visualiser
tests/
  test_generator.py      Pytest test suite (31 tests)
requirements.txt
```

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```
