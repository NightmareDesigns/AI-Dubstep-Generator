"""
Nightmare AI Music Maker Dubstep Edition – Flask web application.

Endpoints
---------
GET  /           → Serve the web UI
POST /generate   → Generate a pattern (JSON)
POST /render     → Render a pattern to a WAV file
"""

import io

from flask import Flask, jsonify, render_template, request, send_file

from generator.ai_generator import DubstepAIGenerator
from generator.audio_synthesizer import DubstepSynthesizer

app = Flask(__name__)

_synthesizer = DubstepSynthesizer()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """Generate an AI dubstep pattern and return it as JSON."""
    data  = request.get_json(silent=True) or {}

    # Build wobble_override dict from dubstep tools parameters
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

    try:
        pattern = DubstepAIGenerator().generate(
            bpm   = int(data.get("bpm",   140)),
            key   = str(data.get("key",   "C")),
            scale = str(data.get("scale", "minor")),
            style = str(data.get("style", "classic")),
            bars  = int(data.get("bars",  4)),
            wobble_override = wobble_override if wobble_override else None,
        )
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(pattern)


@app.route("/render", methods=["POST"])
def render_audio():
    """Render an AI-generated pattern to a WAV file."""
    data = request.get_json(silent=True) or {}

    if "pattern" in data:
        pattern = data["pattern"]
    else:
        try:
            pattern = DubstepAIGenerator().generate(
                bpm   = int(data.get("bpm",   140)),
                key   = str(data.get("key",   "C")),
                scale = str(data.get("scale", "minor")),
                style = str(data.get("style", "classic")),
                bars  = int(data.get("bars",  4)),
            )
        except (ValueError, TypeError) as exc:
            return jsonify({"error": str(exc)}), 400

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
        download_name="dubstep.wav",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(port=5000)
