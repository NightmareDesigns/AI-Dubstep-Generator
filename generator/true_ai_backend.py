"""
True AI audio generation backend.

Uses an optional text-to-audio model integration when the transformers stack
is installed. This provides a real model-backed generation path separate from
the local corpus-based song sketch generator.
"""

from __future__ import annotations

import io
import os
import wave
from typing import Any, Callable

import numpy as np


_DEFAULT_MODEL_NAME = "facebook/musicgen-small"
_MIN_DURATION_SECONDS = 4.0
_DEFAULT_SAMPLE_RATE = 32000
_TOKENS_PER_SECOND = 50


def _audio_array_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=0)
    peak = float(np.abs(audio).max()) if audio.size else 0.0
    if peak > 0:
        audio = audio / peak * 0.85
    pcm = (audio * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


class TrueAIMusicBackend:
    """Optional real-model backend for text-conditioned music generation."""

    def __init__(
        self,
        model_name: str | None = None,
        pipeline_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.model_name = model_name or os.environ.get("TRUE_AI_MODEL", _DEFAULT_MODEL_NAME)
        self._pipeline_factory = pipeline_factory
        self._pipeline = None
        self._device = -1
        self._error: str | None = None

        if self._pipeline_factory is None:
            try:
                from transformers import pipeline
            except ImportError:
                self._error = (
                    "True AI generation requires optional dependencies. "
                    "Install `transformers` and a supported runtime such as `torch`, "
                    f"then configure model `{self.model_name}`."
                )
                return

            self._pipeline_factory = pipeline

            try:
                import torch
            except ImportError:
                self._device = -1
            else:
                self._device = 0 if torch.cuda.is_available() else -1

    def is_available(self) -> bool:
        return self._error is None

    def get_info(self) -> dict[str, Any]:
        return {
            "type": "true_ai_audio",
            "provider": "huggingface_transformers",
            "model_name": self.model_name,
            "available": self.is_available(),
            "error": self._error,
        }

    def compose_prompt(
        self,
        prompt: str,
        bpm: int,
        key: str,
        scale: str,
        style: str,
        bars: int,
    ) -> str:
        user_prompt = prompt.strip()
        base_prompt = (
            user_prompt
            or "Generate a polished EDM song with a strong groove, melodic hooks, and modern production"
        )
        style_label = style.replace("_", " ")
        return (
            f"{base_prompt}. Style: {style_label}. Tempo: {bpm} BPM. "
            f"Key: {key} {scale}. Length: roughly {bars} bars. "
            "Make it sound like a complete musical idea with arrangement and dynamics."
        )

    def estimate_duration_seconds(self, bpm: int, bars: int) -> float:
        beat_duration = 60.0 / max(1, int(bpm))
        return max(_MIN_DURATION_SECONDS, beat_duration * 4 * max(1, int(bars)))

    def build_descriptor(
        self,
        prompt: str,
        bpm: int,
        key: str,
        scale: str,
        style: str,
        bars: int,
    ) -> dict[str, Any]:
        prompt_text = self.compose_prompt(prompt, bpm, key, scale, style, bars)
        info = self.get_info()
        return {
            "bpm": bpm,
            "key": key,
            "scale": scale,
            "style": style,
            "bars": bars,
            "steps_per_bar": 16,
            "generation_mode": "true_ai",
            "prompt": prompt,
            "generator": {
                **info,
                "prompt_conditioned": True,
            },
            "song": {
                "type": "true_ai_audio",
                "sections": [],
                "total_bars": bars,
            },
            "drums": {"kick": [], "snare": [], "hihat": []},
            "bass": {"root_midi": 0, "scale": scale, "notes": []},
            "lead": {
                "root_midi": 0,
                "scale": scale,
                "instrument": "true_ai_audio",
                "notes": [],
            },
            "wobble": [],
            "true_ai": {
                "prompt_text": prompt_text,
                "estimated_duration_seconds": round(
                    self.estimate_duration_seconds(bpm, bars), 2
                ),
            },
        }

    def _get_pipeline(self) -> Any:
        if not self.is_available():
            raise RuntimeError(self._error or "True AI backend is unavailable")
        if self._pipeline is None:
            assert self._pipeline_factory is not None
            self._pipeline = self._pipeline_factory(
                "text-to-audio",
                model=self.model_name,
                device=self._device,
            )
        return self._pipeline

    def render_wav(
        self,
        prompt: str,
        bpm: int,
        key: str,
        scale: str,
        style: str,
        bars: int,
    ) -> bytes:
        pipeline = self._get_pipeline()
        prompt_text = self.compose_prompt(prompt, bpm, key, scale, style, bars)
        max_new_tokens = max(
            256,
            int(self.estimate_duration_seconds(bpm, bars) * _TOKENS_PER_SECOND),
        )

        try:
            result = pipeline(prompt_text, forward_params={"max_new_tokens": max_new_tokens})
        except TypeError:
            result = pipeline(prompt_text)

        if isinstance(result, list):
            result = result[0]
        if not isinstance(result, dict) or "audio" not in result:
            raise ValueError("True AI model returned an unexpected response")

        audio = np.asarray(result["audio"], dtype=np.float32)
        sample_rate = int(result.get("sampling_rate", _DEFAULT_SAMPLE_RATE))
        return _audio_array_to_wav_bytes(audio, sample_rate)
