from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from typing import Final

from ava.voice.interfaces import AudioChunk, AudioGateway

try:
    import numpy as np
    import sounddevice as sd
except ImportError:  # pragma: no cover - optional dependency guard
    np = None
    sd = None


_SENTINEL: Final = object()
logger = logging.getLogger(__name__)


class SoundDeviceAudioGateway(AudioGateway):
    def __init__(self, *, input_sample_rate_hz: int, input_chunk_ms: int) -> None:
        self._input_sample_rate_hz = input_sample_rate_hz
        self._input_chunk_ms = input_chunk_ms
        self._queue: asyncio.Queue[AudioChunk | object] = asyncio.Queue()
        self._input_stream = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._muted = False
        self._input_device_name: str | None = None
        self._output_device_name: str | None = None
        self._active_input_sample_rate_hz = input_sample_rate_hz
        self._output_queue: asyncio.Queue[tuple[bytes, int]] = asyncio.Queue()
        self._output_task: asyncio.Task[None] | None = None
        self._output_stream = None
        self._output_sample_rate_hz: int | None = None
        self._queued_output_bytes = 0
        self._queued_output_chunks = 0
        self._output_turn_active = False

    async def start_input(self) -> None:
        if sd is None or np is None:
            raise RuntimeError("sounddevice and numpy are required for microphone capture.")
        if self._input_stream is not None:
            return

        self._loop = asyncio.get_running_loop()
        input_device = await asyncio.to_thread(sd.query_devices, None, "input")
        self._input_device_name = str(input_device.get("name", "unknown"))
        requested_sample_rate_hz = self._input_sample_rate_hz
        try:
            await asyncio.to_thread(
                sd.check_input_settings,
                device=None,
                channels=1,
                dtype="int16",
                samplerate=requested_sample_rate_hz,
            )
            self._active_input_sample_rate_hz = requested_sample_rate_hz
        except Exception:
            fallback_rate_hz = int(
                float(input_device.get("default_samplerate", requested_sample_rate_hz))
            )
            self._active_input_sample_rate_hz = fallback_rate_hz
            logger.warning(
                "Microphone sample rate fallback applied",
                extra={
                    "event": "mic_sample_rate_fallback",
                    "requested_sample_rate_hz": requested_sample_rate_hz,
                    "fallback_sample_rate_hz": fallback_rate_hz,
                    "device_name": self._input_device_name,
                },
            )

        blocksize = max(1, int(self._active_input_sample_rate_hz * (self._input_chunk_ms / 1000)))
        logger.info(
            "Microphone device selected",
            extra={
                "event": "mic_device_selected",
                "device_name": self._input_device_name,
                "sample_rate_hz": self._active_input_sample_rate_hz,
                "blocksize": blocksize,
            },
        )

        def callback(indata, _frames, _time_info, _status) -> None:
            if self._muted or self._loop is None:
                return
            if _status:
                logger.warning(
                    "Microphone callback reported a stream status",
                    extra={"event": "mic_callback_status", "status": str(_status)},
                )
            chunk = AudioChunk(
                data=bytes(indata),
                sample_rate_hz=self._active_input_sample_rate_hz,
                captured_at=datetime.now(UTC),
            )
            self._loop.call_soon_threadsafe(self._queue.put_nowait, chunk)

        self._input_stream = sd.RawInputStream(
            samplerate=self._active_input_sample_rate_hz,
            channels=1,
            dtype="int16",
            blocksize=blocksize,
            callback=callback,
        )
        self._input_stream.start()
        logger.info(
            "Microphone stream started",
            extra={
                "event": "mic_stream_started",
                "device_name": self._input_device_name,
                "sample_rate_hz": self._active_input_sample_rate_hz,
            },
        )

    async def stop_input(self) -> None:
        if self._input_stream is None:
            return
        await asyncio.to_thread(self._input_stream.stop)
        await asyncio.to_thread(self._input_stream.close)
        self._input_stream = None
        await self._queue.put(_SENTINEL)
        logger.info(
            "Microphone stream stopped",
            extra={"event": "mic_stream_stopped", "device_name": self._input_device_name},
        )

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

        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        if self._output_device_name is None:
            output_device = await asyncio.to_thread(sd.query_devices, None, "output")
            self._output_device_name = str(output_device.get("name", "unknown"))
            logger.info(
                "Speaker device selected",
                extra={
                    "event": "speaker_device_selected",
                    "device_name": self._output_device_name,
                    "sample_rate_hz": sample_rate_hz,
                },
            )

        if self._output_task is None or self._output_task.done():
            self._output_task = asyncio.create_task(
                self._output_loop(),
                name="ava-audio-output",
            )
        if not self._output_turn_active:
            self._output_turn_active = True
            self._queued_output_bytes = 0
            self._queued_output_chunks = 0
            logger.info(
                "Speaker playback started",
                extra={
                    "event": "playback_started",
                    "device_name": self._output_device_name,
                    "sample_rate_hz": sample_rate_hz,
                },
            )
        self._queued_output_bytes += len(data)
        self._queued_output_chunks += 1
        await self._output_queue.put((data, sample_rate_hz))

    async def flush_output(self) -> None:
        if self._output_task is None:
            return
        await self._output_queue.join()
        if not self._output_turn_active:
            return
        logger.info(
            "Speaker playback finished",
            extra={
                "event": "playback_finished",
                "device_name": self._output_device_name,
                "sample_rate_hz": self._output_sample_rate_hz,
                "byte_count": self._queued_output_bytes,
                "chunk_count": self._queued_output_chunks,
            },
        )
        self._output_turn_active = False
        self._queued_output_bytes = 0
        self._queued_output_chunks = 0

    async def mute(self) -> None:
        self._muted = True
        await self.interrupt_output()
        logger.info("Audio gateway muted", extra={"event": "audio_muted"})

    async def unmute(self) -> None:
        self._muted = False
        logger.info("Audio gateway unmuted", extra={"event": "audio_unmuted"})

    async def interrupt_output(self) -> None:
        if sd is None:
            return
        await asyncio.to_thread(sd.stop)
        while not self._output_queue.empty():
            try:
                self._output_queue.get_nowait()
                self._output_queue.task_done()
            except asyncio.QueueEmpty:
                break
        if self._output_task is not None:
            self._output_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._output_task
            self._output_task = None
        self._output_turn_active = False
        self._queued_output_bytes = 0
        self._queued_output_chunks = 0
        logger.info("Speaker playback interrupted", extra={"event": "playback_interrupted"})

    async def _output_loop(self) -> None:
        try:
            while True:
                data, sample_rate_hz = await self._output_queue.get()
                try:
                    await self._ensure_output_stream(sample_rate_hz)
                    await asyncio.to_thread(self._output_stream.write, data)
                finally:
                    self._output_queue.task_done()
        except asyncio.CancelledError:
            raise
        finally:
            await self._close_output_stream()

    async def _ensure_output_stream(self, sample_rate_hz: int) -> None:
        if sd is None:
            raise RuntimeError("sounddevice is required for audio playback.")
        if self._output_stream is not None and self._output_sample_rate_hz == sample_rate_hz:
            return
        await self._close_output_stream()

        def _create_stream():
            stream = sd.RawOutputStream(
                samplerate=sample_rate_hz,
                channels=1,
                dtype="int16",
            )
            stream.start()
            return stream

        self._output_stream = await asyncio.to_thread(_create_stream)
        self._output_sample_rate_hz = sample_rate_hz

    async def _close_output_stream(self) -> None:
        if self._output_stream is None:
            self._output_sample_rate_hz = None
            return
        await asyncio.to_thread(self._output_stream.stop)
        await asyncio.to_thread(self._output_stream.close)
        self._output_stream = None
        self._output_sample_rate_hz = None
