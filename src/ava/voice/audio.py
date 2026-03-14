from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from functools import partial
from typing import Final

from ava.voice.interfaces import AudioChunk, AudioGateway

try:
    import numpy as np
    import sounddevice as sd
except ImportError:  # pragma: no cover - optional dependency guard
    np = None
    sd = None


_SENTINEL: Final = object()


class SoundDeviceAudioGateway(AudioGateway):
    def __init__(self, *, input_sample_rate_hz: int, input_chunk_ms: int) -> None:
        self._input_sample_rate_hz = input_sample_rate_hz
        self._input_chunk_ms = input_chunk_ms
        self._queue: asyncio.Queue[AudioChunk | object] = asyncio.Queue()
        self._input_stream = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._muted = False

    async def start_input(self) -> None:
        if sd is None or np is None:
            raise RuntimeError("sounddevice and numpy are required for microphone capture.")
        if self._input_stream is not None:
            return

        self._loop = asyncio.get_running_loop()
        blocksize = max(1, int(self._input_sample_rate_hz * (self._input_chunk_ms / 1000)))

        def callback(indata, _frames, _time_info, _status) -> None:
            if self._muted or self._loop is None:
                return
            chunk = AudioChunk(
                data=bytes(indata),
                sample_rate_hz=self._input_sample_rate_hz,
                captured_at=datetime.now(UTC),
            )
            self._loop.call_soon_threadsafe(self._queue.put_nowait, chunk)

        self._input_stream = sd.RawInputStream(
            samplerate=self._input_sample_rate_hz,
            channels=1,
            dtype="int16",
            blocksize=blocksize,
            callback=callback,
        )
        self._input_stream.start()

    async def stop_input(self) -> None:
        if self._input_stream is None:
            return
        await asyncio.to_thread(self._input_stream.stop)
        await asyncio.to_thread(self._input_stream.close)
        self._input_stream = None
        await self._queue.put(_SENTINEL)

    async def input_chunks(self):
        while True:
            item = await self._queue.get()
            if item is _SENTINEL:
                break
            yield item

    async def play_output_chunk(self, data: bytes, *, sample_rate_hz: int) -> None:
        if self._muted or not data:
            return
        if sd is None or np is None:
            raise RuntimeError("sounddevice and numpy are required for audio playback.")

        samples = np.frombuffer(data, dtype=np.int16)
        await asyncio.to_thread(partial(sd.play, samples, samplerate=sample_rate_hz, blocking=True))

    async def mute(self) -> None:
        self._muted = True
        await self.interrupt_output()

    async def unmute(self) -> None:
        self._muted = False

    async def interrupt_output(self) -> None:
        if sd is None:
            return
        await asyncio.to_thread(sd.stop)
