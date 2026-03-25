"""
Tests for the AI EDM Music Maker.
Run with: python -m pytest tests/ -v
"""

import builtins
import importlib.util
import io
from pathlib import Path
import wave

import pytest

from generator.ai_generator import EDMAIGenerator, DubstepAIGenerator
from generator.audio_synthesizer import DubstepSynthesizer
from generator.true_ai_backend import TrueAIMusicBackend


def _wav_bytes_for_test() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 64)
    return buf.getvalue()


class _AvailableTrueAIBackend:

    def __init__(self):
        self._info = {
            "type": "true_ai_audio",
            "provider": "test_provider",
            "model_name": "test-model",
            "available": True,
            "error": None,
        }
        self._descriptor_backend = TrueAIMusicBackend(
            pipeline_factory=lambda *args, **kwargs: None
        )

    def is_available(self):
        return True

    def get_info(self):
        return dict(self._info)

    def build_descriptor(self, prompt, bpm, key, scale, style, bars):
        return self._descriptor_backend.build_descriptor(prompt, bpm, key, scale, style, bars)

    def render_wav(self, prompt, bpm, key, scale, style, bars):
        return _wav_bytes_for_test()


class _UnavailableTrueAIBackend:

    def is_available(self):
        return False

    def get_info(self):
        return {
            "type": "true_ai_audio",
            "provider": "test_provider",
            "model_name": "missing-model",
            "available": False,
            "error": "missing optional true AI dependencies",
        }


# ---------------------------------------------------------------------------
# EDMAIGenerator tests
# ---------------------------------------------------------------------------

class TestEDMAIGenerator:

    def setup_method(self):
        self.gen = EDMAIGenerator(seed=42)

    def test_generate_returns_dict(self):
        result = self.gen.generate()
        assert isinstance(result, dict)

    def test_generate_required_keys(self):
        result = self.gen.generate()
        for key in ("bpm", "key", "scale", "style", "bars", "steps_per_bar",
                    "generator", "song", "drums", "bass", "lead", "wobble"):
            assert key in result, f"Missing key: {key}"

    def test_generate_bpm_range(self):
        low  = self.gen.generate(bpm=50)    # clamped to 80
        high = self.gen.generate(bpm=999)   # clamped to 180
        assert low["bpm"]  == 80
        assert high["bpm"] == 180

    def test_generate_bars_range(self):
        low  = self.gen.generate(bars=0)   # clamped to 1
        high = self.gen.generate(bars=999) # clamped to 16
        assert low["bars"]  == 1
        assert high["bars"] == 16

    def test_generate_invalid_key_fallback(self):
        result = self.gen.generate(key="ZZ")
        assert result["key"] == "C"

    def test_generate_invalid_scale_fallback(self):
        result = self.gen.generate(scale="chromatic")
        assert result["scale"] == "minor"

    def test_generate_invalid_style_fallback(self):
        result = self.gen.generate(style="jazz")
        assert result["style"] == "classic"

    @pytest.mark.parametrize("style", ["classic", "brostep", "future_bass"])
    def test_generate_dubstep_styles(self, style):
        result = self.gen.generate(style=style)
        assert result["style"] == style

    @pytest.mark.parametrize("style", ["riddim", "house", "techno", "trance", "drum_and_bass", "trap", "electro"])
    def test_generate_all_edm_styles(self, style):
        result = self.gen.generate(style=style)
        assert result["style"] == style

    @pytest.mark.parametrize("scale", ["minor", "major", "phrygian", "dorian"])
    def test_generate_all_scales(self, scale):
        result = self.gen.generate(scale=scale)
        assert result["scale"] == scale

    def test_drums_structure(self):
        result = self.gen.generate(bars=2)
        drums = result["drums"]
        assert set(drums.keys()) == {"kick", "snare", "hihat"}
        for part in drums.values():
            assert len(part) == 2           # 2 bars
            for bar in part:
                assert len(bar) == 16       # 16 steps
                assert all(v in (0, 1) for v in bar)

    def test_bass_structure(self):
        result = self.gen.generate(bars=3)
        bass = result["bass"]
        assert "root_midi" in bass
        assert "notes" in bass
        assert len(bass["notes"]) == 3       # 3 bars
        for bar_notes in bass["notes"]:
            for note in bar_notes:
                assert "step" in note
                assert "midi" in note
                assert "velocity" in note
                assert "duration" in note
                assert 0 <= note["step"] < 16
                assert 0 < note["velocity"] <= 127

    def test_lead_structure(self):
        result = self.gen.generate(bars=3)
        lead = result["lead"]
        assert lead["instrument"] == "lead_synth"
        assert len(lead["notes"]) == 3
        for bar_notes in lead["notes"]:
            for note in bar_notes:
                assert "step" in note
                assert "midi" in note
                assert "velocity" in note
                assert "duration" in note
                assert 0 <= note["step"] < 16
                assert 0 < note["velocity"] <= 127

    def test_song_structure(self):
        result = self.gen.generate(bars=6)
        song = result["song"]
        assert song["type"] == "full_song"
        assert song["total_bars"] == 6
        assert len(song["bar_energies"]) == 6
        assert sum(section["bars"] for section in song["sections"]) == 6
        for section in song["sections"]:
            assert section["bars"] >= 1
            assert 0.0 <= section["energy"] <= 1.0
        expanded = []
        for section in song["sections"]:
            expanded.extend([section["energy"]] * section["bars"])
        assert song["bar_energies"] == expanded

    def test_generator_metadata(self):
        result = self.gen.generate()
        generator = result["generator"]
        assert generator["type"] == "corpus_sequence_model"
        assert generator["version"] == 2
        assert "lead" in generator["trained_parts"]
        assert "energy_aware_arrangement" in generator["features"]

    def test_high_energy_bars_are_more_active(self):
        result = self.gen.generate(style="classic", bars=8)
        energies = result["song"]["bar_energies"]
        activity = []
        for bar_index, energy in enumerate(energies):
            drum_hits = (
                sum(result["drums"]["kick"][bar_index])
                + sum(result["drums"]["snare"][bar_index])
                + sum(result["drums"]["hihat"][bar_index])
            )
            melodic_notes = (
                len(result["bass"]["notes"][bar_index])
                + len(result["lead"]["notes"][bar_index])
            )
            activity.append((energy, drum_hits + melodic_notes))

        low_energy_activity = [score for energy, score in activity if energy <= 0.35]
        high_energy_activity = [score for energy, score in activity if energy >= 0.9]

        assert low_energy_activity
        assert high_energy_activity
        assert min(high_energy_activity) > max(low_energy_activity)

    def test_wobble_structure(self):
        result = self.gen.generate(bars=4)
        wobble = result["wobble"]
        assert len(wobble) == 4
        for w in wobble:
            assert "rate"       in w
            assert "depth"      in w
            assert "resonance"  in w
            assert "shape"      in w
            assert "cutoff_min" in w
            assert "cutoff_max" in w
            assert 0.0 <= w["depth"] <= 1.0
            assert 0.0 <= w["resonance"] <= 1.0
            assert w["cutoff_min"] < w["cutoff_max"]

    def test_high_energy_bars_get_faster_wobble(self):
        result = self.gen.generate(style="brostep", bars=8)
        energies = result["song"]["bar_energies"]
        low_energy_rates = [w["rate"] for w, energy in zip(result["wobble"], energies) if energy <= 0.35]
        high_energy_rates = [w["rate"] for w, energy in zip(result["wobble"], energies) if energy >= 0.9]

        assert low_energy_rates
        assert high_energy_rates
        assert (sum(high_energy_rates) / len(high_energy_rates)) >= (
            sum(low_energy_rates) / len(low_energy_rates)
        )

    def test_reproducibility_with_seed(self):
        g1 = EDMAIGenerator(seed=7)
        g2 = EDMAIGenerator(seed=7)
        assert g1.generate(bars=2) == g2.generate(bars=2)

    def test_different_seeds_differ(self):
        g1 = EDMAIGenerator(seed=1)
        g2 = EDMAIGenerator(seed=2)
        # Very unlikely to be equal
        assert g1.generate(bars=4) != g2.generate(bars=4)

    def test_backward_compatibility_alias(self):
        # DubstepAIGenerator should be an alias for EDMAIGenerator
        assert DubstepAIGenerator is EDMAIGenerator
        gen = DubstepAIGenerator(seed=42)
        result = gen.generate(style="classic")
        assert result["style"] == "classic"

    # ------------------------------------------------------------------
    # Synth Tools / Wobble Override tests
    # ------------------------------------------------------------------

    def test_wobble_override_rate(self):
        result = self.gen.generate(bars=2, wobble_override={"rate": 8})
        for w in result["wobble"]:
            assert w["rate"] == 8

    def test_wobble_override_depth(self):
        result = self.gen.generate(bars=2, wobble_override={"depth": 0.85})
        for w in result["wobble"]:
            assert w["depth"] == 0.85

    def test_wobble_override_resonance(self):
        result = self.gen.generate(bars=2, wobble_override={"resonance": 0.9})
        for w in result["wobble"]:
            assert w["resonance"] == 0.9

    def test_wobble_override_shape(self):
        result = self.gen.generate(bars=2, wobble_override={"shape": "square"})
        for w in result["wobble"]:
            assert w["shape"] == "square"

    def test_wobble_override_cutoff_range(self):
        result = self.gen.generate(
            bars=2,
            wobble_override={"cutoff_min": 150, "cutoff_max": 5000}
        )
        for w in result["wobble"]:
            assert w["cutoff_min"] == 150
            assert w["cutoff_max"] == 5000

    def test_wobble_override_multiple_params(self):
        override = {
            "rate": 16,
            "depth": 0.95,
            "resonance": 0.8,
            "shape": "sawtooth",
            "cutoff_min": 100,
            "cutoff_max": 6000,
        }
        result = self.gen.generate(bars=3, wobble_override=override)
        for w in result["wobble"]:
            assert w["rate"] == 16
            assert w["depth"] == 0.95
            assert w["resonance"] == 0.8
            assert w["shape"] == "sawtooth"
            assert w["cutoff_min"] == 100
            assert w["cutoff_max"] == 6000

    def test_wobble_partial_override(self):
        # Only override rate, other params should still be valid
        result = self.gen.generate(bars=2, wobble_override={"rate": 4})
        for w in result["wobble"]:
            assert w["rate"] == 4
            assert 0.0 <= w["depth"] <= 1.0
            assert 0.0 <= w["resonance"] <= 1.0
            assert w["shape"] in ["sine", "square", "sawtooth", "triangle"]


# ---------------------------------------------------------------------------
# DubstepSynthesizer tests
# ---------------------------------------------------------------------------

class TestDubstepSynthesizer:

    def setup_method(self):
        self.gen   = DubstepAIGenerator(seed=0)
        self.synth = DubstepSynthesizer()

    def test_render_returns_bytes(self):
        pattern = self.gen.generate(bars=1)
        wav     = self.synth.render(pattern)
        assert isinstance(wav, bytes)

    def test_render_valid_wav_header(self):
        pattern = self.gen.generate(bars=1)
        wav     = self.synth.render(pattern)
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"

    def test_render_wav_length_increases_with_bars(self):
        p1 = self.gen.generate(bars=1)
        p2 = self.gen.generate(bars=4)
        w1 = self.synth.render(p1)
        w2 = self.synth.render(p2)
        assert len(w2) > len(w1)

    def test_render_bpm_affects_length(self):
        # Higher BPM → shorter duration → smaller file
        p_slow = self.gen.generate(bars=2, bpm=80)
        p_fast = self.gen.generate(bars=2, bpm=160)
        w_slow = self.synth.render(p_slow)
        w_fast = self.synth.render(p_fast)
        assert len(w_slow) > len(w_fast)

    def test_audio_synthesizer_imports_without_scipy(self, monkeypatch):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "generator"
            / "audio_synthesizer.py"
        )
        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "scipy" or name.startswith("scipy."):
                raise ImportError("scipy blocked for test")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", guarded_import)

        spec = importlib.util.spec_from_file_location(
            "audio_synthesizer_no_scipy", module_path
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None, (
            "expected a loader for audio_synthesizer.py so the test can execute "
            "the module with SciPy imports blocked"
        )
        spec.loader.exec_module(module)

        assert hasattr(module, "DubstepSynthesizer")

    @pytest.mark.parametrize("style", ["classic", "brostep", "future_bass"])
    def test_render_all_styles(self, style):
        pattern = self.gen.generate(bars=1, style=style)
        wav     = self.synth.render(pattern)
        assert len(wav) > 100  # non-trivial output


# ---------------------------------------------------------------------------
# True AI backend tests
# ---------------------------------------------------------------------------

class TestTrueAIMusicBackend:

    def test_defaults_to_musicgen_melody_large(self):
        backend = TrueAIMusicBackend(pipeline_factory=lambda *args, **kwargs: None)
        assert backend.model_name == "facebook/musicgen-melody-large"
        assert backend.get_info()["offline_only"] is True

    def test_packaged_build_disables_true_ai(self, monkeypatch):
        monkeypatch.setattr("generator.true_ai_backend.sys.frozen", True, raising=False)

        backend = TrueAIMusicBackend(pipeline_factory=lambda *args, **kwargs: None)

        assert not backend.is_available()
        assert "offline-ready" in backend.get_info()["error"]

    def test_render_uses_local_files_only(self):
        seen = {}

        def fake_pipeline_factory(*args, **kwargs):
            seen["args"] = args
            seen["kwargs"] = kwargs

            def fake_pipeline(prompt_text, **_kwargs):
                return {
                    "audio": [0.0, 0.1, -0.1, 0.0],
                    "sampling_rate": 16000,
                }

            return fake_pipeline

        backend = TrueAIMusicBackend(pipeline_factory=fake_pipeline_factory)

        wav_bytes = backend.render_wav("offline test", 140, "C", "minor", "classic", 4)

        assert wav_bytes[:4] == b"RIFF"
        assert seen["args"] == ("text-to-audio",)
        assert seen["kwargs"]["model"] == backend.model_name
        assert seen["kwargs"]["local_files_only"] is True

    def test_render_raises_runtime_error_when_model_is_not_available_locally(self):
        backend = TrueAIMusicBackend(
            pipeline_factory=lambda *args, **kwargs: (_ for _ in ()).throw(
                OSError("missing local model files")
            )
        )

        with pytest.raises(RuntimeError, match="offline-only"):
            backend.render_wav("offline test", 140, "C", "minor", "classic", 4)


# ---------------------------------------------------------------------------
# Flask app integration tests
# ---------------------------------------------------------------------------

class TestFlaskApp:

    def setup_method(self):
        import app as flask_app
        self.flask_app = flask_app
        flask_app.app.config["TESTING"] = True
        self.client = flask_app.app.test_client()

    def test_index_returns_200(self):
        rv = self.client.get("/")
        assert rv.status_code == 200
        assert b"Nightmare AI Music Maker" in rv.data

    def test_generate_endpoint(self):
        rv = self.client.post(
            "/generate",
            json={"bpm": 140, "key": "A", "scale": "minor", "style": "classic", "bars": 2},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["bpm"] == 140
        assert data["key"] == "A"
        assert data["bars"] == 2
        assert data["generator"]["type"] == "corpus_sequence_model"
        assert "sections" in data["song"]
        assert "notes" in data["lead"]

    def test_generate_defaults(self):
        rv = self.client.post("/generate", json={})
        assert rv.status_code == 200
        data = rv.get_json()
        assert "bpm" in data

    def test_info_endpoint_reports_true_ai_backend(self):
        rv = self.client.get("/info")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["default_mode"] == "song_sketch"
        assert data["song_sketch"]["type"] == "corpus_sequence_model"
        assert "true_ai" in data

    def test_info_endpoint_uses_packaged_resource_paths(self, monkeypatch):
        import app as flask_app

        monkeypatch.setattr(flask_app.sys, "frozen", True, raising=False)
        monkeypatch.setattr(flask_app.sys, "_MEIPASS", "/tmp/frozen-app", raising=False)

        resource_root = flask_app._resource_root()

        assert str(resource_root) == "/tmp/frozen-app"

    def test_generate_true_ai_descriptor_when_backend_available(self, monkeypatch):
        monkeypatch.setattr(self.flask_app, "_true_ai_backend", _AvailableTrueAIBackend())
        rv = self.client.post(
            "/generate",
            json={
                "generation_mode": "true_ai",
                "prompt": "melodic dubstep anthem",
                "bpm": 150,
                "style": "brostep",
                "bars": 4,
            },
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["generation_mode"] == "true_ai"
        assert data["generator"]["type"] == "true_ai_audio"
        assert "melodic dubstep anthem" in data["true_ai"]["prompt_text"]

    def test_generate_true_ai_returns_503_when_backend_unavailable(self, monkeypatch):
        monkeypatch.setattr(self.flask_app, "_true_ai_backend", _UnavailableTrueAIBackend())
        rv = self.client.post(
            "/generate",
            json={"generation_mode": "true_ai", "prompt": "future bass ballad"},
        )
        assert rv.status_code == 503
        assert "missing optional true AI dependencies" in rv.get_json()["error"]

    def test_render_returns_wav(self):
        # First generate a pattern
        rv_gen  = self.client.post(
            "/generate",
            json={"bpm": 140, "bars": 1, "style": "classic"},
        )
        pattern = rv_gen.get_json()

        rv_wav = self.client.post("/render", json={"pattern": pattern})
        assert rv_wav.status_code == 200
        assert rv_wav.content_type == "audio/wav"
        assert rv_wav.data[:4] == b"RIFF"

    def test_render_without_pattern_still_works(self):
        rv = self.client.post(
            "/render",
            json={"bpm": 140, "bars": 1, "style": "classic"},
        )
        assert rv.status_code == 200
        assert rv.content_type == "audio/wav"

    def test_render_true_ai_pattern_returns_wav(self, monkeypatch):
        monkeypatch.setattr(self.flask_app, "_true_ai_backend", _AvailableTrueAIBackend())
        pattern = _AvailableTrueAIBackend().build_descriptor(
            "epic synthwave crossover",
            128,
            "C",
            "minor",
            "classic",
            4,
        )
        rv = self.client.post("/render", json={"pattern": pattern})
        assert rv.status_code == 200
        assert rv.content_type == "audio/wav"
        assert rv.data[:4] == b"RIFF"

    # ------------------------------------------------------------------
    # Dubstep Tools API tests
    # ------------------------------------------------------------------

    def test_generate_with_wobble_rate(self):
        rv = self.client.post(
            "/generate",
            json={"bpm": 140, "bars": 2, "wobble_rate": 8},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        for w in data["wobble"]:
            assert w["rate"] == 8

    def test_generate_with_wobble_shape(self):
        rv = self.client.post(
            "/generate",
            json={"bpm": 140, "bars": 2, "wobble_shape": "square"},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        for w in data["wobble"]:
            assert w["shape"] == "square"

    def test_generate_with_wobble_depth(self):
        rv = self.client.post(
            "/generate",
            json={"bpm": 140, "bars": 2, "wobble_depth": 0.9},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        for w in data["wobble"]:
            assert w["depth"] == 0.9

    def test_generate_with_resonance(self):
        rv = self.client.post(
            "/generate",
            json={"bpm": 140, "bars": 2, "resonance": 0.85},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        for w in data["wobble"]:
            assert w["resonance"] == 0.85

    def test_generate_with_cutoff_range(self):
        rv = self.client.post(
            "/generate",
            json={"bpm": 140, "bars": 2, "cutoff_min": 150, "cutoff_max": 5500},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        for w in data["wobble"]:
            assert w["cutoff_min"] == 150
            assert w["cutoff_max"] == 5500

    def test_generate_with_all_synth_tools(self):
        rv = self.client.post(
            "/generate",
            json={
                "bpm": 150,
                "bars": 2,
                "style": "brostep",
                "wobble_rate": 16,
                "wobble_depth": 0.95,
                "resonance": 0.8,
                "wobble_shape": "sawtooth",
                "cutoff_min": 100,
                "cutoff_max": 6000,
            },
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["style"] == "brostep"
        for w in data["wobble"]:
            assert w["rate"] == 16
            assert w["depth"] == 0.95
            assert w["resonance"] == 0.8
            assert w["shape"] == "sawtooth"
            assert w["cutoff_min"] == 100
            assert w["cutoff_max"] == 6000

    @pytest.mark.parametrize("style", ["riddim", "house", "techno", "trance", "drum_and_bass", "trap", "electro"])
    def test_generate_new_edm_styles_via_api(self, style):
        rv = self.client.post(
            "/generate",
            json={"bpm": 140, "bars": 2, "style": style},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["style"] == style
