"""
AI-powered pattern generator for dubstep music.

Uses Markov chains and probabilistic models to generate authentic
dubstep drum patterns, bass lines, and wobble parameters.
"""

import random
from typing import Any

# ---------------------------------------------------------------------------
# Markov-chain transition tables
# ---------------------------------------------------------------------------

# Drum pattern transitions: each state is a 16-step bar (1 = hit, 0 = rest).
# Represented compactly as hex bitmasks over 16 steps.
# States are keyed by a "style tag" that corresponds to the DubstepStyle.

_KICK_STATES: dict[str, list[int]] = {
    "classic":    [0b1000100010001000,
                   0b1000100010001010,
                   0b1001100010001000,
                   0b1000100010101000],
    "brostep":    [0b1000100010001000,
                   0b1010100010001000,
                   0b1000100010001010,
                   0b1001000010001000],
    "future_bass":[0b1000000010000000,
                   0b1000100000001000,
                   0b1000000010001000,
                   0b1010000010000000],
}

_SNARE_STATES: dict[str, list[int]] = {
    "classic":    [0b0000100000001000,
                   0b0000100000001001,
                   0b0000100100001000,
                   0b0000100000001010],
    "brostep":    [0b0000100000001000,
                   0b0000100010001000,
                   0b0000100000101000,
                   0b0000110000001000],
    "future_bass":[0b0000100000001000,
                   0b0000100000001100,
                   0b0000000000001000,
                   0b0001000000001000],
}

_HIHAT_STATES: dict[str, list[int]] = {
    "classic":    [0b0101010101010101,
                   0b0101010101010100,
                   0b1101010101010101,
                   0b0101010101010111],
    "brostep":    [0b1010101010101010,
                   0b1110101010101010,
                   0b1010101011101010,
                   0b1010101010111010],
    "future_bass":[0b1111111111111111,
                   0b1111111011111110,
                   0b1011111111111110,
                   0b1111111111011111],
}

# Markov transition weights for state indices (4 states each).
# Row = current state, column = next state.
_DRUM_TRANSITIONS = [
    [0.50, 0.25, 0.15, 0.10],
    [0.20, 0.45, 0.25, 0.10],
    [0.15, 0.20, 0.45, 0.20],
    [0.10, 0.25, 0.25, 0.40],
]

# ---------------------------------------------------------------------------
# Bass note / chord helpers
# ---------------------------------------------------------------------------

# MIDI note numbers for roots in common scales (one octave starting at C2 = 36)
_ROOT_NOTES = {
    "C": 36, "C#": 37, "D": 38, "D#": 39, "E": 40,
    "F": 41, "F#": 42, "G": 43, "G#": 44, "A": 45, "A#": 46, "B": 47,
}

_SCALE_INTERVALS = {
    "minor":     [0, 2, 3, 5, 7, 8, 10],
    "major":     [0, 2, 4, 5, 7, 9, 11],
    "phrygian":  [0, 1, 3, 5, 7, 8, 10],
    "dorian":    [0, 2, 3, 5, 7, 9, 10],
}

# Dubstep bass line rhythm patterns (16 steps, 1 = note-on)
_BASS_RHYTHMS = [
    [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    [1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0],
    [1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0],
]

# Markov transitions for bass note scale-degree selection (7 degrees)
_BASS_NOTE_TRANSITIONS = [
    [0.00, 0.30, 0.15, 0.20, 0.20, 0.10, 0.05],  # from degree 0 (root)
    [0.30, 0.00, 0.25, 0.20, 0.15, 0.05, 0.05],  # from degree 1
    [0.25, 0.20, 0.00, 0.25, 0.15, 0.10, 0.05],  # from degree 2
    [0.30, 0.15, 0.20, 0.00, 0.20, 0.10, 0.05],  # from degree 3
    [0.35, 0.20, 0.10, 0.15, 0.00, 0.15, 0.05],  # from degree 4
    [0.30, 0.15, 0.15, 0.10, 0.20, 0.00, 0.10],  # from degree 5
    [0.40, 0.20, 0.10, 0.10, 0.10, 0.05, 0.05],  # from degree 6
]

# ---------------------------------------------------------------------------
# Wobble / LFO helpers
# ---------------------------------------------------------------------------

_WOBBLE_RATES_BY_STYLE = {
    "classic":    [1, 2, 4],
    "brostep":    [4, 8, 16],
    "future_bass":[2, 4, 8],
}

_WOBBLE_SHAPES = ["sine", "square", "sawtooth", "triangle"]


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------

class DubstepAIGenerator:
    """
    Generates AI-driven dubstep patterns using Markov chains and
    weighted probabilistic models.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        bpm: int = 140,
        key: str = "C",
        scale: str = "minor",
        style: str = "classic",
        bars: int = 4,
    ) -> dict[str, Any]:
        """
        Generate a complete dubstep pattern.

        Parameters
        ----------
        bpm:   Beats per minute (80–180).
        key:   Root key, e.g. "C", "F#".
        scale: Scale type – "minor", "major", "phrygian", or "dorian".
        style: Dubstep sub-genre – "classic", "brostep", or "future_bass".
        bars:  Number of bars to generate (1–16).

        Returns
        -------
        A dictionary containing all pattern data ready for the synthesiser.
        """
        bpm   = max(80, min(180, int(bpm)))
        bars  = max(1,  min(16,  int(bars)))
        key   = key   if key   in _ROOT_NOTES         else "C"
        scale = scale if scale in _SCALE_INTERVALS    else "minor"
        style = style if style in _KICK_STATES        else "classic"

        drum_pattern  = self._generate_drums(style, bars)
        bass_pattern  = self._generate_bass(key, scale, bars)
        wobble_params = self._generate_wobble(style, bars)

        return {
            "bpm":          bpm,
            "key":          key,
            "scale":        scale,
            "style":        style,
            "bars":         bars,
            "steps_per_bar": 16,
            "drums":        drum_pattern,
            "bass":         bass_pattern,
            "wobble":       wobble_params,
        }

    # ------------------------------------------------------------------
    # Drum pattern generation
    # ------------------------------------------------------------------

    def _generate_drums(self, style: str, bars: int) -> dict[str, list[list[int]]]:
        kick_bars   = self._markov_pattern_sequence(_KICK_STATES[style],   bars)
        snare_bars  = self._markov_pattern_sequence(_SNARE_STATES[style],  bars)
        hihat_bars  = self._markov_pattern_sequence(_HIHAT_STATES[style],  bars)
        return {"kick": kick_bars, "snare": snare_bars, "hihat": hihat_bars}

    def _markov_pattern_sequence(self, states: list[int], bars: int) -> list[list[int]]:
        state_idx = self._rng.randrange(len(states))
        result: list[list[int]] = []
        for _ in range(bars):
            bitmask = states[state_idx]
            result.append([(bitmask >> (15 - i)) & 1 for i in range(16)])
            state_idx = self._markov_next(state_idx, _DRUM_TRANSITIONS)
        return result

    # ------------------------------------------------------------------
    # Bass line generation
    # ------------------------------------------------------------------

    def _generate_bass(self, key: str, scale: str, bars: int) -> dict[str, Any]:
        root        = _ROOT_NOTES[key]
        intervals   = _SCALE_INTERVALS[scale]
        degree      = 0  # start on the root
        notes: list[list[dict[str, Any]]] = []

        rhythm_idx = self._rng.randrange(len(_BASS_RHYTHMS))
        for _ in range(bars):
            rhythm = _BASS_RHYTHMS[rhythm_idx]
            bar_notes: list[dict[str, Any]] = []
            for step in range(16):
                if rhythm[step]:
                    midi   = root + intervals[degree]
                    octave = self._rng.choices([0, 12], weights=[0.7, 0.3])[0]
                    bar_notes.append({
                        "step":     step,
                        "midi":     midi + octave,
                        "velocity": self._rng.randint(80, 127),
                        "duration": self._rng.choices([1, 2, 4], weights=[0.5, 0.35, 0.15])[0],
                    })
                    degree = self._markov_next(degree, _BASS_NOTE_TRANSITIONS)
            notes.append(bar_notes)
            rhythm_idx = self._rng.randrange(len(_BASS_RHYTHMS))

        return {
            "root_midi": root,
            "scale":     scale,
            "notes":     notes,
        }

    # ------------------------------------------------------------------
    # Wobble / LFO parameter generation
    # ------------------------------------------------------------------

    def _generate_wobble(self, style: str, bars: int) -> list[dict[str, Any]]:
        wobble_list: list[dict[str, Any]] = []
        rates  = _WOBBLE_RATES_BY_STYLE[style]
        for _ in range(bars):
            wobble_list.append({
                "rate":       self._rng.choice(rates),
                "depth":      round(self._rng.uniform(0.4, 1.0), 2),
                "resonance":  round(self._rng.uniform(0.5, 0.95), 2),
                "shape":      self._rng.choice(_WOBBLE_SHAPES),
                "cutoff_min": self._rng.randint(80, 400),
                "cutoff_max": self._rng.randint(1200, 4000),
            })
        return wobble_list

    # ------------------------------------------------------------------
    # Markov utility
    # ------------------------------------------------------------------

    def _markov_next(self, current: int, transitions: list[list[float]]) -> int:
        weights = transitions[current % len(transitions)]
        population = list(range(len(weights)))
        return self._rng.choices(population, weights=weights)[0]
