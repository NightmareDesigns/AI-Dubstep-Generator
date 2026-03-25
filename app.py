"""
Nightmare AI Music Maker – Flask web application.

Endpoints
---------
GET  /           → Serve the web UI
GET  /info       → Describe available generation backends
POST /generate   → Generate a song sketch or true-AI request (JSON)
POST /render     → Render a song sketch or true-AI audio request to WAV
"""

import io

from flask import Flask, jsonify, render_template, request, send_file

from generator.ai_generator import EDMAIGenerator
from generator.audio_synthesizer import DubstepSynthesizer
from generator.true_ai_backend import TrueAIMusicBackend

app = Flask(__name__)

_synthesizer = DubstepSynthesizer()
_true_ai_backend = TrueAIMusicBackend()


def _is_true_ai_pattern(pattern: dict) -> bool:
    return (
        pattern.get("generation_mode") == "true_ai"
        or pattern.get("generator", {}).get("type") == "true_ai_audio"
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/info")
def info():
    """Expose the currently available generation backends."""
    return jsonify({
        "default_mode": "song_sketch",
        "song_sketch": {
            "type": "corpus_sequence_model",
            "label": "Song Sketch (local)",
        },
        "true_ai": _true_ai_backend.get_info(),
    })


@app.route("/generate", methods=["POST"])
def generate():
    """Generate a local song sketch or true-AI audio request descriptor."""
    data  = request.get_json(silent=True) or {}
    generation_mode = str(data.get("generation_mode", "song_sketch"))

    # Build wobble_override dict from synth tools parameters
    wobble_override = {}
    if "wobble_rate" in data:
        wobble_override["rate"] = int(data["wobble_rate"])
    if "wobble_shape" in data:
        wobble_override["shape"] = str(data["wobble_shape"])
    if "wobble_depth" in data:
        wobble_override["depth"] = float(data["wobble_depth"])
    if "resonance" in data:
        wobble_override["resonance"] = float(data["resonance"])
    if "cutoff_min" in data:
        wobble_override["cutoff_min"] = int(data["cutoff_min"])
    if "cutoff_max" in data:
        wobble_override["cutoff_max"] = int(data["cutoff_max"])

    if generation_mode == "true_ai":
        if not _true_ai_backend.is_available():
            return jsonify({"error": _true_ai_backend.get_info()["error"]}), 503
        descriptor = _true_ai_backend.build_descriptor(
            prompt=str(data.get("prompt", "")),
            bpm=int(data.get("bpm", 140)),
            key=str(data.get("key", "C")),
            scale=str(data.get("scale", "minor")),
            style=str(data.get("style", "classic")),
            bars=int(data.get("bars", 4)),
        )
        return jsonify(descriptor)

    try:
        pattern = EDMAIGenerator().generate(
            bpm=int(data.get("bpm", 140)),
            key=str(data.get("key", "C")),
            scale = str(data.get("scale", "minor")),
            style=str(data.get("style", "classic")),
            bars=int(data.get("bars", 4)),
            wobble_override=wobble_override if wobble_override else None,
        )
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(pattern)


@app.route("/render", methods=["POST"])
def render_audio():
    """Render a local song sketch or true-AI music request to WAV."""
    data = request.get_json(silent=True) or {}

    if "pattern" in data:
        pattern = data["pattern"]
    else:
        generation_mode = str(data.get("generation_mode", "song_sketch"))
        if generation_mode == "true_ai":
            pattern = _true_ai_backend.build_descriptor(
                prompt=str(data.get("prompt", "")),
                bpm=int(data.get("bpm", 140)),
                key=str(data.get("key", "C")),
                scale=str(data.get("scale", "minor")),
                style=str(data.get("style", "classic")),
                bars=int(data.get("bars", 4)),
            )
        else:
            try:
                pattern = EDMAIGenerator().generate(
                    bpm=int(data.get("bpm", 140)),
                    key=str(data.get("key", "C")),
                    scale=str(data.get("scale", "minor")),
                    style=str(data.get("style", "classic")),
                    bars=int(data.get("bars", 4)),
                )
            except (ValueError, TypeError) as exc:
                return jsonify({"error": str(exc)}), 400

    if _is_true_ai_pattern(pattern):
        if not _true_ai_backend.is_available():
            return jsonify({"error": _true_ai_backend.get_info()["error"]}), 503
        try:
            wav_bytes = _true_ai_backend.render_wav(
                prompt=str(pattern.get("prompt", "")),
                bpm=int(pattern.get("bpm", 140)),
                key=str(pattern.get("key", "C")),
                scale=str(pattern.get("scale", "minor")),
                style=str(pattern.get("style", "classic")),
                bars=int(pattern.get("bars", 4)),
            )
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503
        except (ValueError, TypeError) as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:  # noqa: BLE001
            return jsonify({"error": "True AI synthesis error"}), 500
    else:
        try:
            wav_bytes = _synthesizer.render(pattern)
        except (KeyError, TypeError, ValueError) as exc:
            return jsonify({"error": f"Invalid pattern: {exc}"}), 400
        except Exception:  # noqa: BLE001
            return jsonify({"error": "Synthesis error"}), 500

    return send_file(
        io.BytesIO(wav_bytes),
        mimetype="audio/wav",
        as_attachment=False,
        download_name="edm_track.wav",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(port=5000)
