"""
AI-powered pattern generator for EDM music.

Uses a lightweight corpus-trained sequence model to generate
EDM drum patterns, bass lines, lead melodies, and song structure.
Supports dubstep, riddim, house, techno, trance, drum & bass, and more.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from functools import lru_cache
from typing import Any, Hashable

# ---------------------------------------------------------------------------
# Training corpus
# ---------------------------------------------------------------------------

# Drum pattern corpus bars: each state is a 16-step bar (1 = hit, 0 = rest),
# represented as a 16-bit integer.
_KICK_STATES: dict[str, list[int]] = {
    "classic": [0b1000100010001000, 0b1000100010001010, 0b1001100010001000, 0b1000100010101000],
    "brostep": [0b1000100010001000, 0b1010100010001000, 0b1000100010001010, 0b1001000010001000],
    "future_bass": [0b1000000010000000, 0b1000100000001000, 0b1000000010001000, 0b1010000010000000],
    "riddim": [0b1000000010000000, 0b1000000010001000, 0b1000100010000000, 0b1000000010000010],
    "house": [0b1000100010001000, 0b1000100010001000, 0b1000100010001000, 0b1000100010001001],
    "techno": [0b1000100010001000, 0b1000100010001010, 0b1000100110001000, 0b1001100010001000],
    "trance": [0b1000100010001000, 0b1000100010001000, 0b1000100010001000, 0b1000100010001000],
    "drum_and_bass": [0b1000001000100010, 0b1000010010000100, 0b1000001010001000, 0b1010000010001000],
    "trap": [0b1000000010000000, 0b1000001000000010, 0b1000000010000100, 0b1000100000001000],
    "electro": [0b1000100010001000, 0b1000100010001010, 0b1000100010101000, 0b1010100010001000],
}

_SNARE_STATES: dict[str, list[int]] = {
    "classic": [0b0000100000001000, 0b0000100000001001, 0b0000100100001000, 0b0000100000001010],
    "brostep": [0b0000100000001000, 0b0000100010001000, 0b0000100000101000, 0b0000110000001000],
    "future_bass": [0b0000100000001000, 0b0000100000001100, 0b0000000000001000, 0b0001000000001000],
    "riddim": [0b0000100000001000, 0b0000100000001000, 0b0000100000001010, 0b0000100000101000],
    "house": [0b0000100000001000, 0b0000100000001000, 0b0000100000001001, 0b0000100100001000],
    "techno": [0b0000100000001000, 0b0000100000001010, 0b0000100010001000, 0b0010100000001000],
    "trance": [0b0000100000001000, 0b0000100000001000, 0b0000100000001001, 0b0000100000001000],
    "drum_and_bass": [0b0000100001001000, 0b0000100100001000, 0b0010100000001000, 0b0000100000101000],
    "trap": [0b0000100000001000, 0b0000100000001000, 0b0000100000001001, 0b0000100000011000],
    "electro": [0b0000100000001000, 0b0000100000001010, 0b0000100000001000, 0b0000110000001000],
}

_HIHAT_STATES: dict[str, list[int]] = {
    "classic": [0b0101010101010101, 0b0101010101010100, 0b1101010101010101, 0b0101010101010111],
    "brostep": [0b1010101010101010, 0b1110101010101010, 0b1010101011101010, 0b1010101010111010],
    "future_bass": [0b1111111111111111, 0b1111111011111110, 0b1011111111111110, 0b1111111111011111],
    "riddim": [0b0100010001000100, 0b0101010101010101, 0b0100010001010100, 0b0101010001000101],
    "house": [0b0101010101010101, 0b0101010101010101, 0b0111010101010101, 0b0101010101010111],
    "techno": [0b1111111111111111, 0b1111111111111110, 0b1110111111111111, 0b1111111011111111],
    "trance": [0b1111111111111111, 0b1111111111111111, 0b1111111011111111, 0b1111111111111110],
    "drum_and_bass": [0b1111111111111111, 0b1110111011101110, 0b1111111111111111, 0b1111011111110111],
    "trap": [0b0101010101010101, 0b0101011101010111, 0b0101010111110101, 0b1111010101010101],
    "electro": [0b0101010101010101, 0b1101010101010101, 0b0101010101010111, 0b0101011101010101],
}

_ROOT_NOTES = {
    "C": 36, "C#": 37, "D": 38, "D#": 39, "E": 40,
    "F": 41, "F#": 42, "G": 43, "G#": 44, "A": 45, "A#": 46, "B": 47,
}

_SCALE_INTERVALS = {
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
}

_STYLE_FAMILIES = {
    "classic": "dubstep",
    "brostep": "dubstep",
    "future_bass": "dubstep",
    "riddim": "dubstep",
    "house": "club",
    "techno": "club",
    "trance": "club",
    "electro": "club",
    "drum_and_bass": "breakbeat",
    "trap": "breakbeat",
}

_FAMILY_BASS_PHRASES: dict[str, tuple[tuple[tuple[tuple[int, int, int, int], ...], ...], ...]] = {
    "dubstep": (
        (
            ((0, 0, 4, 124), (8, 4, 2, 116), (12, 5, 2, 112)),
            ((0, 0, 2, 122), (4, 2, 2, 112), (8, 4, 4, 118)),
            ((0, 5, 2, 114), (4, 4, 2, 116), (8, 2, 4, 112)),
            ((0, 0, 4, 126), (8, 6, 2, 114), (12, 4, 2, 112)),
        ),
        (
            ((0, 0, 2, 120), (4, 0, 2, 112), (8, 3, 4, 118)),
            ((0, 4, 2, 116), (4, 2, 2, 112), (8, 0, 4, 120)),
            ((0, 5, 4, 114), (8, 4, 2, 110), (12, 2, 2, 108)),
            ((0, 0, 2, 124), (4, 6, 2, 114), (8, 4, 4, 116)),
        ),
    ),
    "club": (
        (
            ((0, 0, 4, 116), (8, 4, 4, 112)),
            ((0, 0, 2, 118), (4, 2, 2, 110), (8, 4, 4, 114)),
            ((0, 5, 4, 112), (8, 4, 4, 110)),
            ((0, 0, 4, 118), (8, 6, 2, 110), (12, 4, 2, 108)),
        ),
        (
            ((0, 0, 2, 116), (4, 3, 2, 108), (8, 4, 4, 112)),
            ((0, 2, 2, 110), (4, 4, 2, 112), (8, 5, 4, 114)),
            ((0, 4, 4, 112), (8, 2, 4, 110)),
            ((0, 0, 4, 118), (8, 4, 4, 112)),
        ),
    ),
    "breakbeat": (
        (
            ((0, 0, 2, 126), (6, 4, 2, 116), (10, 5, 2, 112), (14, 4, 2, 110)),
            ((0, 0, 2, 122), (4, 2, 2, 114), (8, 4, 2, 116), (12, 6, 2, 112)),
            ((0, 5, 2, 114), (4, 4, 2, 112), (10, 2, 2, 110), (14, 0, 2, 118)),
            ((0, 0, 4, 124), (8, 4, 2, 116), (12, 6, 2, 112)),
        ),
        (
            ((0, 0, 2, 122), (4, 3, 2, 112), (8, 0, 2, 118), (12, 4, 2, 114)),
            ((0, 5, 2, 114), (6, 4, 2, 110), (10, 2, 2, 108), (14, 0, 2, 116)),
            ((0, 0, 2, 120), (4, 2, 2, 112), (8, 5, 2, 110), (12, 6, 2, 108)),
            ((0, 0, 4, 124), (8, 4, 4, 116)),
        ),
    ),
}

_FAMILY_LEAD_PHRASES: dict[str, tuple[tuple[tuple[tuple[int, int, int, int], ...], ...], ...]] = {
    "dubstep": (
        (
            tuple(),
            ((4, 4, 2, 90), (8, 5, 2, 94), (12, 6, 2, 90)),
            ((0, 7, 2, 98), (4, 6, 2, 92), (8, 5, 2, 90), (12, 4, 4, 96)),
            ((0, 7, 4, 100), (8, 9, 4, 96)),
        ),
        (
            tuple(),
            ((6, 4, 2, 88), (10, 5, 2, 92)),
            ((0, 7, 2, 98), (4, 9, 2, 94), (8, 7, 4, 92)),
            ((0, 5, 4, 90), (8, 4, 4, 88)),
        ),
    ),
    "club": (
        (
            ((0, 7, 2, 94), (4, 9, 2, 98), (8, 7, 2, 96), (12, 5, 2, 92)),
            ((0, 4, 2, 90), (4, 5, 2, 92), (8, 7, 4, 96)),
            ((0, 9, 2, 98), (4, 7, 2, 96), (8, 5, 4, 92)),
            ((0, 7, 4, 98), (8, 11, 4, 100)),
        ),
        (
            ((2, 7, 2, 94), (6, 9, 2, 96), (10, 11, 2, 98)),
            ((0, 7, 2, 96), (4, 5, 2, 92), (8, 4, 4, 90)),
            ((0, 9, 2, 98), (4, 7, 2, 96), (8, 5, 4, 92)),
            ((0, 7, 4, 100), (8, 12, 4, 98)),
        ),
    ),
    "breakbeat": (
        (
            tuple(),
            ((4, 7, 2, 92), (8, 9, 2, 96), (12, 7, 2, 92)),
            ((0, 10, 2, 98), (4, 9, 2, 94), (8, 7, 2, 92), (12, 5, 2, 90)),
            ((0, 7, 4, 100), (8, 12, 4, 96)),
        ),
        (
            tuple(),
            ((6, 7, 2, 90), (10, 5, 2, 88)),
            ((0, 9, 2, 96), (4, 7, 2, 94), (8, 5, 2, 92), (12, 4, 2, 90)),
            ((0, 7, 4, 98), (8, 10, 4, 94)),
        ),
    ),
}

_FAMILY_ARRANGEMENTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "dubstep": (
        ("intro", "build", "drop", "breakdown", "drop", "outro"),
        ("intro", "build", "pre_drop", "drop", "breakdown", "drop"),
    ),
    "club": (
        ("intro", "groove", "build", "drop", "breakdown", "drop", "outro"),
        ("intro", "groove", "build", "anthem", "breakdown", "drop"),
    ),
    "breakbeat": (
        ("intro", "build", "drop", "switchup", "drop", "outro"),
        ("intro", "tension", "drop", "breakdown", "drop"),
    ),
}

_SECTION_BAR_HINTS = {
    "intro": 4,
    "groove": 4,
    "build": 4,
    "pre_drop": 2,
    "drop": 8,
    "anthem": 8,
    "switchup": 4,
    "breakdown": 4,
    "tension": 4,
    "outro": 4,
}

_SECTION_ENERGY = {
    "intro": 0.25,
    "groove": 0.45,
    "build": 0.6,
    "pre_drop": 0.72,
    "drop": 0.95,
    "anthem": 0.9,
    "switchup": 0.8,
    "breakdown": 0.35,
    "tension": 0.7,
    "outro": 0.2,
}

_STEP_JITTER_CHOICES = [0, 0, 0, 1, -1]
_MIN_SONG_SECTIONS = 1
_MAX_SONG_SECTIONS = 6
_DEFAULT_BAR_ENERGY = 0.6

_WOBBLE_RATES_BY_STYLE = {
    "classic": [1, 2, 4],
    "brostep": [4, 8, 16],
    "future_bass": [2, 4, 8],
    "riddim": [1, 2, 4],
    "house": [1, 2, 4],
    "techno": [2, 4, 8],
    "trance": [1, 2, 4],
    "drum_and_bass": [4, 8, 16],
    "trap": [1, 2, 4],
    "electro": [2, 4, 8],
}

_WOBBLE_SHAPES = ["sine", "square", "sawtooth", "triangle"]


# ---------------------------------------------------------------------------
# Corpus model helpers
# ---------------------------------------------------------------------------

def _weighted_choice(counter: Counter[Hashable], rng: random.Random) -> Hashable:
    if not counter:
        raise ValueError("weighted choice requires at least one candidate")
    population = list(counter.keys())
    weights = list(counter.values())
    return rng.choices(population, weights=weights, k=1)[0]


class CorpusSequenceModel:
    """Simple sequence model trained from example token sequences."""

    def __init__(self, sequences: list[list[Hashable]]) -> None:
        self._starts: Counter[Hashable] = Counter()
        self._transitions: dict[Hashable, Counter[Hashable]] = defaultdict(Counter)
        self._fallback: Counter[Hashable] = Counter()

        for sequence in sequences:
            if not sequence:
                continue
            self._starts[sequence[0]] += 1
            self._fallback.update(sequence)
            for current, nxt in zip(sequence, sequence[1:]):
                self._transitions[current][nxt] += 1

        if not self._fallback:
            raise ValueError("CorpusSequenceModel requires at least one token")

    def sample(self, length: int, rng: random.Random) -> list[Hashable]:
        if length <= 0:
            return []

        current = _weighted_choice(self._starts if self._starts else self._fallback, rng)
        output = [current]
        for _ in range(length - 1):
            transitions = self._transitions.get(current) or self._fallback
            current = _weighted_choice(transitions, rng)
            output.append(current)
        return output


def _augment_sequences(tokens: list[Hashable]) -> list[list[Hashable]]:
    if not tokens:
        return []
    return [
        list(tokens),
        list(tokens[1:] + tokens[:1]),
        list(reversed(tokens)),
    ]


def _phrases_to_sequences(
    phrases: tuple[tuple[tuple[tuple[int, int, int, int], ...], ...], ...]
) -> list[list[Hashable]]:
    sequences: list[list[Hashable]] = []
    for phrase in phrases:
        bar_tokens = [tuple(bar) for bar in phrase]
        sequences.extend(_augment_sequences(bar_tokens))
    return sequences


@lru_cache(maxsize=None)
def _drum_model(style: str, part: str) -> CorpusSequenceModel:
    state_map = {
        "kick": _KICK_STATES,
        "snare": _SNARE_STATES,
        "hihat": _HIHAT_STATES,
    }[part]
    return CorpusSequenceModel(_augment_sequences(state_map[style]))


@lru_cache(maxsize=None)
def _bass_model(style: str) -> CorpusSequenceModel:
    family = _STYLE_FAMILIES[style]
    return CorpusSequenceModel(_phrases_to_sequences(_FAMILY_BASS_PHRASES[family]))


@lru_cache(maxsize=None)
def _lead_model(style: str) -> CorpusSequenceModel:
    family = _STYLE_FAMILIES[style]
    return CorpusSequenceModel(_phrases_to_sequences(_FAMILY_LEAD_PHRASES[family]))


@lru_cache(maxsize=None)
def _arrangement_model(style: str) -> CorpusSequenceModel:
    family = _STYLE_FAMILIES[style]
    sequences = [list(phrase) for phrase in _FAMILY_ARRANGEMENTS[family]]
    return CorpusSequenceModel(sequences)


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------

class EDMAIGenerator:
    """
    Generates EDM music using a lightweight corpus-trained sequence model.

    The generator learns transitions from embedded drum, bass, lead, and song
    arrangement examples instead of relying only on fixed hand-authored output
    tables, while keeping the API lightweight and offline-friendly.
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
        wobble_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a complete EDM song sketch.

        Parameters
        ----------
        bpm:   Beats per minute (80–180).
        key:   Root key, e.g. "C", "F#".
        scale: Scale type – "minor", "major", "phrygian", or "dorian".
        style: EDM genre – "classic" (dubstep), "brostep", "future_bass",
               "riddim", "house", "techno", "trance", "drum_and_bass",
               "trap", or "electro".
        bars:  Number of bars to generate (1–16).
        wobble_override: Optional dict with wobble parameters to override:
               rate, depth, resonance, shape, cutoff_min, cutoff_max.

        Returns
        -------
        A dictionary containing all pattern data ready for the synthesiser.
        """
        bpm = max(80, min(180, int(bpm)))
        bars = max(1, min(16, int(bars)))
        key = key if key in _ROOT_NOTES else "C"
        scale = scale if scale in _SCALE_INTERVALS else "minor"
        style = style if style in _KICK_STATES else "classic"

        song_structure = self._generate_song_structure(style, bars)
        bar_energies = song_structure["bar_energies"]
        drum_pattern = self._generate_drums(style, bars, bar_energies)
        bass_pattern = self._generate_bass(key, scale, style, bars, bar_energies)
        lead_pattern = self._generate_lead(key, scale, style, bars, bar_energies)
        wobble_params = self._generate_wobble(style, bars, bar_energies, wobble_override)

        return {
            "bpm": bpm,
            "key": key,
            "scale": scale,
            "style": style,
            "bars": bars,
            "steps_per_bar": 16,
            "generator": {
                "type": "corpus_sequence_model",
                "model_name": "embedded-edm-song-model",
                "version": 2,
                "trained_parts": ["drums", "bass", "lead", "arrangement"],
                "features": [
                    "energy_aware_arrangement",
                    "section_conditioned_layers",
                    "motif_variation",
                ],
            },
            "song": song_structure,
            "drums": drum_pattern,
            "bass": bass_pattern,
            "lead": lead_pattern,
            "wobble": wobble_params,
        }

    # ------------------------------------------------------------------
    # Drum generation
    # ------------------------------------------------------------------

    def _generate_drums(
        self,
        style: str,
        bars: int,
        bar_energies: list[float],
    ) -> dict[str, list[list[int]]]:
        return {
            "kick": self._sample_drum_bars(style, "kick", bars, bar_energies),
            "snare": self._sample_drum_bars(style, "snare", bars, bar_energies),
            "hihat": self._sample_drum_bars(style, "hihat", bars, bar_energies),
        }

    def _sample_drum_bars(
        self,
        style: str,
        part: str,
        bars: int,
        bar_energies: list[float],
    ) -> list[list[int]]:
        model = _drum_model(style, part)
        bitmasks = model.sample(bars, self._rng)
        return [
            self._shape_drum_bar(
                [(int(bitmask) >> (15 - i)) & 1 for i in range(16)],
                self._bar_energy(bar_energies, index),
                part,
            )
            for index, bitmask in enumerate(bitmasks)
        ]

    def _shape_drum_bar(self, bar: list[int], energy: float, part: str) -> list[int]:
        shaped = list(bar)

        if part == "kick":
            if energy < 0.4:
                shaped = [1 if index in {0, 8} and (bar[index] or index == 0) else 0 for index in range(16)]
            elif energy >= 0.85:
                shaped[0] = 1
                shaped[8] = 1
                if sum(shaped) < 4:
                    for step in (6, 10, 14):
                        shaped[step] = 1

        elif part == "snare":
            shaped[4] = 1
            shaped[12] = 1
            if energy < 0.4:
                for step in range(16):
                    if step not in {4, 12}:
                        shaped[step] = 0
            elif energy >= 0.85:
                shaped[15] = 1

        elif part == "hihat":
            if energy < 0.4:
                shaped = [1 if index in {2, 6, 10, 14} else 0 for index in range(16)]
            elif energy >= 0.7:
                for step in range(1, 16, 2):
                    shaped[step] = 1
                if energy >= 0.92:
                    for step in (3, 7, 11, 15):
                        shaped[step] = 1

        return shaped

    # ------------------------------------------------------------------
    # Bass / lead generation
    # ------------------------------------------------------------------

    def _generate_bass(
        self,
        key: str,
        scale: str,
        style: str,
        bars: int,
        bar_energies: list[float],
    ) -> dict[str, Any]:
        root = _ROOT_NOTES[key]
        intervals = _SCALE_INTERVALS[scale]
        bar_tokens = _bass_model(style).sample(bars, self._rng)
        notes = [
            self._materialize_note_bar(
                bar,
                root,
                intervals,
                0,
                [0, 12],
                self._bar_energy(bar_energies, index),
                "bass",
            )
            for index, bar in enumerate(bar_tokens)
        ]
        return {
            "root_midi": root,
            "scale": scale,
            "notes": notes,
        }

    def _generate_lead(
        self,
        key: str,
        scale: str,
        style: str,
        bars: int,
        bar_energies: list[float],
    ) -> dict[str, Any]:
        root = _ROOT_NOTES[key] + 12
        intervals = _SCALE_INTERVALS[scale]
        bar_tokens = _lead_model(style).sample(bars, self._rng)
        notes = [
            self._materialize_note_bar(
                bar,
                root,
                intervals,
                12,
                [12, 24],
                self._bar_energy(bar_energies, index),
                "lead",
            )
            for index, bar in enumerate(bar_tokens)
        ]
        return {
            "root_midi": root,
            "scale": scale,
            "instrument": "lead_synth",
            "notes": notes,
        }

    def _materialize_note_bar(
        self,
        template_bar: Hashable,
        root: int,
        intervals: list[int],
        transpose: int,
        octave_choices: list[int],
        energy: float,
        role: str,
    ) -> list[dict[str, Any]]:
        notes: list[dict[str, Any]] = []
        low_octave_weight = max(0.2, 1.0 - (energy * 0.6))
        high_octave_weight = max(0.2, 0.35 + (energy * 0.6))
        for step, degree, duration, velocity in tuple(template_bar):
            degree_idx = degree % len(intervals)
            octave = self._rng.choices(
                octave_choices,
                weights=[low_octave_weight, high_octave_weight],
                k=1,
            )[0]
            note_step = max(0, min(15, int(step + self._rng.choice(_STEP_JITTER_CHOICES))))
            notes.append({
                "step": note_step,
                "midi": root + intervals[degree_idx] + transpose + octave,
                "velocity": max(
                    70,
                    min(127, velocity + self._rng.randint(-6, 6) + int(round((energy - 0.5) * 18))),
                ),
                "duration": max(
                    1,
                    min(4, duration + self._rng.choice([0, 0, 1, -1]) + (1 if energy < 0.35 else 0)),
                ),
            })
        notes = self._shape_note_activity(
            notes,
            energy,
            role,
            root + intervals[0] + transpose + min(octave_choices),
            root + intervals[min(4, len(intervals) - 1)] + transpose + max(octave_choices),
        )
        notes.sort(key=lambda note: (note["step"], note["midi"]))
        return notes

    def _shape_note_activity(
        self,
        notes: list[dict[str, Any]],
        energy: float,
        role: str,
        anchor_midi: int,
        accent_midi: int,
    ) -> list[dict[str, Any]]:
        shaped = [dict(note) for note in notes]

        if role == "bass":
            if energy < 0.4:
                if shaped:
                    anchor = dict(shaped[0])
                    anchor.update({"step": 0, "duration": max(3, anchor["duration"]), "velocity": min(anchor["velocity"], 108)})
                    return [anchor]
                return [{"step": 0, "midi": anchor_midi, "velocity": 96, "duration": 4}]

            if energy >= 0.85:
                if not shaped:
                    shaped = [{"step": 0, "midi": anchor_midi, "velocity": 112, "duration": 2}]
                accent_step = min(15, max(shaped[-1]["step"] + 2, 12))
                shaped.append({
                    "step": accent_step,
                    "midi": max(anchor_midi, accent_midi - 12),
                    "velocity": min(127, shaped[-1]["velocity"] + 6),
                    "duration": 1 if energy >= 0.95 else 2,
                })
            return shaped

        if energy < 0.35:
            if not shaped:
                return []
            anchor = dict(shaped[0])
            anchor.update({"step": 0, "duration": max(3, anchor["duration"]), "velocity": max(70, anchor["velocity"] - 8)})
            return [anchor]

        if energy < 0.6 and len(shaped) > 2:
            shaped = shaped[:2]

        if energy >= 0.85:
            if not shaped:
                shaped = [{"step": 0, "midi": anchor_midi, "velocity": 92, "duration": 2}]
            response_seed = shaped[-1]
            shaped.append({
                "step": min(15, max(response_seed["step"] + 2, 8)),
                "midi": max(response_seed["midi"], accent_midi),
                "velocity": min(127, response_seed["velocity"] + 6),
                "duration": 1 if energy >= 0.95 else 2,
            })
        return shaped

    # ------------------------------------------------------------------
    # Song structure generation
    # ------------------------------------------------------------------

    def _generate_song_structure(self, style: str, bars: int) -> dict[str, Any]:
        section_count = max(_MIN_SONG_SECTIONS, min(_MAX_SONG_SECTIONS, bars))
        labels = [str(label) for label in _arrangement_model(style).sample(section_count, self._rng)]
        hints = [_SECTION_BAR_HINTS[label] for label in labels]
        total_hint = sum(hints)
        remaining = bars
        sections: list[dict[str, Any]] = []

        for idx, label in enumerate(labels):
            sections_left = len(labels) - idx - 1
            if idx == len(labels) - 1:
                section_bars = remaining
            else:
                proportional = round((bars * hints[idx]) / total_hint)
                section_bars = max(1, proportional)
                section_bars = min(section_bars, remaining - sections_left)

            sections.append({
                "name": label,
                "bars": section_bars,
                "energy": _SECTION_ENERGY[label],
            })
            remaining -= section_bars

        return {
            "type": "full_song",
            "sections": sections,
            "total_bars": bars,
            "bar_energies": self._expand_section_energies(sections, bars),
        }

    def _expand_section_energies(self, sections: list[dict[str, Any]], bars: int) -> list[float]:
        bar_energies: list[float] = []
        for section in sections:
            bar_energies.extend([float(section["energy"])] * int(section["bars"]))
        if len(bar_energies) < bars:
            filler = bar_energies[-1] if bar_energies else _DEFAULT_BAR_ENERGY
            bar_energies.extend([filler] * (bars - len(bar_energies)))
        return bar_energies[:bars]

    def _bar_energy(self, bar_energies: list[float], index: int) -> float:
        if 0 <= index < len(bar_energies):
            return float(bar_energies[index])
        return _DEFAULT_BAR_ENERGY

    # ------------------------------------------------------------------
    # Wobble / LFO parameter generation
    # ------------------------------------------------------------------

    def _generate_wobble(
        self,
        style: str,
        bars: int,
        bar_energies: list[float],
        override: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        wobble_list: list[dict[str, Any]] = []
        rates = _WOBBLE_RATES_BY_STYLE[style]
        override = override or {}

        for index in range(bars):
            energy = self._bar_energy(bar_energies, index)
            rate_index = min(len(rates) - 1, int(round(energy * (len(rates) - 1))))
            cutoff_floor = int(80 + (energy * 260))
            cutoff_ceiling = int(1800 + (energy * 2400))
            wobble_params = {
                "rate": override.get("rate", rates[rate_index]),
                "depth": round(override.get("depth", self._rng.uniform(0.35 + (energy * 0.15), 0.7 + (energy * 0.25))), 2),
                "resonance": round(override.get("resonance", self._rng.uniform(0.45 + (energy * 0.2), 0.7 + (energy * 0.25))), 2),
                "shape": override.get("shape", self._rng.choice(_WOBBLE_SHAPES)),
                "cutoff_min": override.get("cutoff_min", self._rng.randint(cutoff_floor, cutoff_floor + 160)),
                "cutoff_max": override.get("cutoff_max", self._rng.randint(cutoff_ceiling, cutoff_ceiling + 500)),
            }
            wobble_list.append(wobble_params)
        return wobble_list


# Backward compatibility alias
DubstepAIGenerator = EDMAIGenerator
