from __future__ import annotations

from dataclasses import dataclass, field

try:
    import webrtcvad
except ImportError:  # pragma: no cover - optional dependency guard
    webrtcvad = None


@dataclass(slots=True)
class VoiceActivityDetector:
    aggressiveness: int = 2
    frame_ms: int = 20
    _vad: object | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        self._vad = webrtcvad.Vad(self.aggressiveness) if webrtcvad is not None else None

    @property
    def available(self) -> bool:
        return self._vad is not None

    def contains_speech(self, pcm_bytes: bytes, sample_rate_hz: int) -> bool:
        if self._vad is None or not pcm_bytes:
            return False

        frame_bytes = int(sample_rate_hz * (self.frame_ms / 1000) * 2)
        if frame_bytes <= 0:
            return False

        for start in range(0, len(pcm_bytes) - frame_bytes + 1, frame_bytes):
            frame = pcm_bytes[start : start + frame_bytes]
            if self._vad.is_speech(frame, sample_rate_hz):
                return True
        return False
