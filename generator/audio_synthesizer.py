"""
Audio synthesizer for dubstep patterns.

Converts AI-generated pattern dictionaries into PCM audio data (WAV).
All synthesis is done with NumPy – no external audio libraries required.
"""

import io
import math
import struct
import wave
from typing import Any

import numpy as np


SAMPLE_RATE = 44100  # Hz


# ---------------------------------------------------------------------------
# Low-level waveform helpers
# ---------------------------------------------------------------------------

def _sine(freq: float, dur: float, amp: float = 0.8) -> np.ndarray:
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    return (amp * np.sin(2 * math.pi * freq * t)).astype(np.float32)


def _sawtooth(freq: float, dur: float, amp: float = 0.8) -> np.ndarray:
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    phase = (t * freq) % 1.0
    return (amp * (2 * phase - 1)).astype(np.float32)


def _square(freq: float, dur: float, amp: float = 0.8) -> np.ndarray:
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    return (amp * np.sign(np.sin(2 * math.pi * freq * t))).astype(np.float32)


def _noise(dur: float, amp: float = 0.5) -> np.ndarray:
    n = int(SAMPLE_RATE * dur)
    return (amp * (np.random.random(n).astype(np.float32) * 2 - 1))


def _adsr(
    signal: np.ndarray,
    attack: float = 0.005,
    decay: float = 0.05,
    sustain: float = 0.7,
    release: float = 0.1,
) -> np.ndarray:
    n = len(signal)
    sr = SAMPLE_RATE
    a = min(int(attack  * sr), n)
    d = min(int(decay   * sr), n - a)
    r = min(int(release * sr), n - a - d)
    s = n - a - d - r

    env = np.concatenate([
        np.linspace(0, 1, a),
        np.linspace(1, sustain, d),
        np.full(s, sustain),
        np.linspace(sustain, 0, r),
    ]).astype(np.float32)
    return signal * env


def _lowpass(signal: np.ndarray, cutoff: float, resonance: float = 0.5) -> np.ndarray:
    """Windowed-sinc low-pass filter with a resonance-shaped transition width."""
    cutoff = max(20.0, min(cutoff, SAMPLE_RATE * 0.49))
    resonance = max(0.0, min(resonance, 1.0))
    normalized_cutoff = cutoff / SAMPLE_RATE

    # Keep the FIR kernel fairly short for real-time rendering while allowing
    # a slightly narrower transition band at lower resonance settings.
    taps = int(31 + (1.0 - resonance) * 32)
    max_taps = len(signal) if len(signal) % 2 == 1 else len(signal) - 1
    taps = min(taps, max_taps)

    # A symmetric FIR kernel needs an odd tap count centered on the current
    # sample, and single-sample chunks still need a valid fallback.
    taps = max(1, taps)
    if taps % 2 == 0:
        taps += 1

    idx = np.arange(taps, dtype=np.float32) - (taps - 1) / 2
    kernel = 2 * normalized_cutoff * np.sinc(2 * normalized_cutoff * idx)
    kernel *= np.hamming(taps).astype(np.float32)
    kernel /= np.sum(kernel)

    filtered = np.convolve(signal.astype(np.float32), kernel, mode="same")
    return filtered.astype(np.float32)


def _midi_to_hz(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


# ---------------------------------------------------------------------------
# Drum synthesizers
# ---------------------------------------------------------------------------

def _synth_kick(dur: float = 0.5) -> np.ndarray:
    """Classic 808-style kick drum."""
    t   = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    env = np.exp(-t * 12)
    freq_env = 120 * np.exp(-t * 30) + 45
    sig = np.sin(2 * math.pi * np.cumsum(freq_env) / SAMPLE_RATE) * env
    click = _noise(0.005, amp=0.6)
    n = min(len(click), len(sig))
    sig[:n] += click[:n]
    return (0.9 * sig).astype(np.float32)


def _synth_snare(dur: float = 0.25) -> np.ndarray:
    """Electronic snare with body tone + noise."""
    body  = _adsr(_sine(180, dur, amp=0.7), attack=0.002, decay=0.06, sustain=0.1, release=0.05)
    snap  = _adsr(_noise(dur, amp=0.8),     attack=0.001, decay=0.04, sustain=0.0, release=0.05)
    body  = body[:len(snap)]
    return (0.6 * body + 0.5 * snap).astype(np.float32)


def _synth_hihat(dur: float = 0.08, open_hat: bool = False) -> np.ndarray:
    """Closed or open hi-hat."""
    actual_dur = 0.3 if open_hat else dur
    noise = _noise(actual_dur, amp=0.5)
    filtered = _lowpass(noise, cutoff=8000, resonance=0.3)
    env = np.exp(-np.linspace(0, 20 if not open_hat else 8, len(filtered)))
    return (filtered * env).astype(np.float32)


# ---------------------------------------------------------------------------
# Bass synthesizer with wobble
# ---------------------------------------------------------------------------

def _synth_bass_note(
    midi_note: int,
    dur_steps: int,
    step_dur: float,
    wobble: dict[str, Any],
) -> np.ndarray:
    """
    Synthesise a single bass note with LFO wobble on the filter cutoff.
    """
    dur    = dur_steps * step_dur
    freq   = _midi_to_hz(midi_note)
    t      = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)

    # Waveform: detuned saw pair for fatness
    sig  = _sawtooth(freq,       dur, amp=0.5)
    sig += _sawtooth(freq * 1.01, dur, amp=0.4)

    # LFO for filter cutoff (wobble)
    rate      = wobble.get("rate", 4)
    shape     = wobble.get("shape", "sine")
    cutoff_lo = float(wobble.get("cutoff_min", 200))
    cutoff_hi = float(wobble.get("cutoff_max", 2000))
    resonance = float(wobble.get("resonance", 0.7))

    if shape == "sine":
        lfo = (np.sin(2 * math.pi * rate * t) + 1) / 2
    elif shape == "square":
        lfo = (np.sign(np.sin(2 * math.pi * rate * t)) + 1) / 2
    elif shape == "sawtooth":
        lfo = ((rate * t) % 1.0)
    else:  # triangle
        lfo = 1 - 2 * np.abs((rate * t) % 1.0 - 0.5)
        lfo = (lfo + 1) / 2

    cutoffs = cutoff_lo + lfo * (cutoff_hi - cutoff_lo)

    # Apply filter in segments (piecewise approximation for varying cutoff)
    segment = max(1, len(sig) // 32)
    filtered = np.empty_like(sig)
    for i in range(0, len(sig), segment):
        cutoff_val = float(cutoffs[min(i, len(cutoffs) - 1)])
        chunk = sig[i:i + segment]
        filtered[i:i + len(chunk)] = _lowpass(chunk, cutoff_val, resonance)

    return _adsr(filtered, attack=0.01, decay=0.08, sustain=0.8, release=0.1)


# ---------------------------------------------------------------------------
# Pattern → audio renderer
# ---------------------------------------------------------------------------

class DubstepSynthesizer:
    """Converts a pattern dict (from DubstepAIGenerator) to a WAV byte buffer."""

    def render(self, pattern: dict[str, Any]) -> bytes:
        """
        Render pattern to WAV bytes.

        Parameters
        ----------
        pattern: dict returned by DubstepAIGenerator.generate()

        Returns
        -------
        Raw WAV file bytes.
        """
        bpm      = pattern["bpm"]
        bars     = pattern["bars"]
        steps    = pattern["steps_per_bar"]
        drums    = pattern["drums"]
        bass     = pattern["bass"]
        wobble   = pattern["wobble"]

        # Duration of one 16th-note step (seconds)
        beat_dur = 60.0 / bpm          # one quarter note
        step_dur = beat_dur / 4        # one 16th note
        bar_dur  = step_dur * steps    # one bar

        total_samples = int(SAMPLE_RATE * bar_dur * bars) + SAMPLE_RATE
        mix = np.zeros(total_samples, dtype=np.float32)

        # ---- drums ----
        for bar_idx in range(bars):
            bar_offset = int(SAMPLE_RATE * bar_dur * bar_idx)
            kick_pat  = drums["kick"][bar_idx]
            snare_pat = drums["snare"][bar_idx]
            hihat_pat = drums["hihat"][bar_idx]

            for step in range(steps):
                step_offset = bar_offset + int(SAMPLE_RATE * step_dur * step)
                if kick_pat[step]:
                    sig = _synth_kick()
                    end = step_offset + len(sig)
                    mix[step_offset:min(end, total_samples)] += sig[:min(len(sig), total_samples - step_offset)]
                if snare_pat[step]:
                    sig = _synth_snare()
                    end = step_offset + len(sig)
                    mix[step_offset:min(end, total_samples)] += sig[:min(len(sig), total_samples - step_offset)]
                if hihat_pat[step]:
                    sig = _synth_hihat()
                    end = step_offset + len(sig)
                    mix[step_offset:min(end, total_samples)] += sig[:min(len(sig), total_samples - step_offset)]

        # ---- bass ----
        bass_notes = bass["notes"]
        for bar_idx in range(bars):
            bar_offset = int(SAMPLE_RATE * bar_dur * bar_idx)
            w = wobble[bar_idx % len(wobble)]
            for note in bass_notes[bar_idx]:
                step       = note["step"]
                midi       = note["midi"]
                duration   = note["duration"]
                velocity   = note["velocity"] / 127.0
                step_offset = bar_offset + int(SAMPLE_RATE * step_dur * step)
                sig = _synth_bass_note(midi, duration, step_dur, w) * velocity * 0.6
                end = step_offset + len(sig)
                mix[step_offset:min(end, total_samples)] += sig[:min(len(sig), total_samples - step_offset)]

        # ---- normalise & convert to 16-bit PCM ----
        peak = np.max(np.abs(mix))
        if peak > 0:
            mix = mix / peak * 0.85
        pcm = (mix * 32767).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm.tobytes())
        return buf.getvalue()
