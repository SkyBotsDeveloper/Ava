from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from ava.voice.interfaces import AudioChunk, WakeWordEngine, WakeWordEvent

try:
    import numpy as np
    from openwakeword.model import Model
except ImportError:  # pragma: no cover - optional dependency guard
    np = None
    Model = None


class OpenWakeWordEngine(WakeWordEngine):
    def __init__(
        self,
        *,
        model_paths: tuple[str, ...],
        trigger_phrase: str,
        threshold: float,
        patience_frames: int,
    ) -> None:
        self._model_paths = tuple(path for path in model_paths if path)
        self._trigger_phrase = trigger_phrase
        self._threshold = threshold
        self._patience_frames = patience_frames
        self._model: Model | None = None

    async def start(self) -> None:
        if Model is None or np is None:
            raise RuntimeError("openwakeword and numpy are required for wake-word detection.")
        if not self._model_paths:
            raise RuntimeError("No wake-word model paths are configured for Ava.")
        self._model = await asyncio.to_thread(
            Model,
            wakeword_models=list(self._model_paths),
            inference_framework="onnx",
        )

    async def stop(self) -> None:
        if self._model is not None:
            await asyncio.to_thread(self._model.reset)
        self._model = None

    async def process_chunk(self, chunk: AudioChunk) -> WakeWordEvent | None:
        if self._model is None:
            return None
        if np is None:
            return None

        samples = np.frombuffer(chunk.data, dtype=np.int16)
        model_names = tuple(self._model.models.keys())
        predictions = await asyncio.to_thread(
            self._model.predict,
            samples,
            patience={model_name: self._patience_frames for model_name in model_names},
            threshold={model_name: self._threshold for model_name in model_names},
        )
        if not predictions:
            return None

        best_label = max(predictions, key=predictions.get)
        best_score = float(predictions[best_label])
        if best_score < self._threshold:
            return None
        return WakeWordEvent(
            phrase=self._trigger_phrase if len(predictions) == 1 else best_label,
            confidence=best_score,
            detected_at=datetime.now(UTC),
        )
