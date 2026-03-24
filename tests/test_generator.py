"""
Tests for the AI Dubstep Generator.
Run with: python -m pytest tests/ -v
"""

import pytest

from generator.ai_generator import DubstepAIGenerator
from generator.audio_synthesizer import DubstepSynthesizer


# ---------------------------------------------------------------------------
# DubstepAIGenerator tests
# ---------------------------------------------------------------------------

class TestDubstepAIGenerator:

    def setup_method(self):
        self.gen = DubstepAIGenerator(seed=42)

    def test_generate_returns_dict(self):
        result = self.gen.generate()
        assert isinstance(result, dict)

    def test_generate_required_keys(self):
        result = self.gen.generate()
        for key in ("bpm", "key", "scale", "style", "bars", "steps_per_bar",
                    "drums", "bass", "wobble"):
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
    def test_generate_all_styles(self, style):
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

    def test_reproducibility_with_seed(self):
        g1 = DubstepAIGenerator(seed=7)
        g2 = DubstepAIGenerator(seed=7)
        assert g1.generate(bars=2) == g2.generate(bars=2)

    def test_different_seeds_differ(self):
        g1 = DubstepAIGenerator(seed=1)
        g2 = DubstepAIGenerator(seed=2)
        # Very unlikely to be equal
        assert g1.generate(bars=4) != g2.generate(bars=4)


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

    @pytest.mark.parametrize("style", ["classic", "brostep", "future_bass"])
    def test_render_all_styles(self, style):
        pattern = self.gen.generate(bars=1, style=style)
        wav     = self.synth.render(pattern)
        assert len(wav) > 100  # non-trivial output


# ---------------------------------------------------------------------------
# Flask app integration tests
# ---------------------------------------------------------------------------

class TestFlaskApp:

    def setup_method(self):
        import app as flask_app
        flask_app.app.config["TESTING"] = True
        self.client = flask_app.app.test_client()

    def test_index_returns_200(self):
        rv = self.client.get("/")
        assert rv.status_code == 200
        assert b"AI Dubstep Generator" in rv.data

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

    def test_generate_defaults(self):
        rv = self.client.post("/generate", json={})
        assert rv.status_code == 200
        data = rv.get_json()
        assert "bpm" in data

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
