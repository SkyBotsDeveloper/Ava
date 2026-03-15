from __future__ import annotations

import argparse
import asyncio
import json
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

from ava.app.bootstrap import bootstrap_application
from ava.live.gemini import GeminiLiveSessionClient
from ava.memory.journal import JournalRow
from ava.voice.interfaces import AudioChunk
from ava.voice.runtime import VoiceRuntime


@dataclass(slots=True)
class TurnOutcome:
    clarification: str | None = None
    journal_row: dict[str, object] | None = None
    last_response: str = ""
    last_status: str = ""


class QueueAudioGateway:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        self.output_chunks = 0
        self.output_bytes = 0
        self.flush_count = 0
        self.muted = False

    async def start_input(self) -> None:
        return None

    async def stop_input(self) -> None:
        await self._queue.put(None)

    async def input_chunks(self):
        while True:
            item = await self._queue.get()
            if item is None:
                break
            yield item

    async def play_output_chunk(self, data: bytes, *, sample_rate_hz: int) -> None:
        if self.muted:
            return
        self.output_chunks += 1
        self.output_bytes += len(data)

    async def flush_output(self) -> None:
        self.flush_count += 1

    async def mute(self) -> None:
        self.muted = True

    async def unmute(self) -> None:
        self.muted = False

    async def interrupt_output(self) -> None:
        return None

    async def feed_wav(self, wav_path: Path, *, chunk_ms: int, sample_rate_hz: int) -> None:
        with wave.open(str(wav_path), "rb") as handle:
            if handle.getframerate() != sample_rate_hz:
                raise ValueError(
                    f"{wav_path} sample rate {handle.getframerate()} != {sample_rate_hz}"
                )
            if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
                raise ValueError(f"{wav_path} must be mono 16-bit PCM.")

            frames_per_chunk = max(1, int(sample_rate_hz * (chunk_ms / 1000)))
            while True:
                frames = handle.readframes(frames_per_chunk)
                if not frames:
                    break
                await self._queue.put(
                    AudioChunk(
                        data=frames,
                        sample_rate_hz=sample_rate_hz,
                        captured_at=_now(),
                    )
                )
                await asyncio.sleep(chunk_ms / 1000)


def _now():
    import datetime as dt

    return dt.datetime.now(dt.UTC)


def _row_dict(row: JournalRow) -> dict[str, object]:
    return {
        "id": row.id,
        "command_text": row.command_text,
        "action_name": row.action_name,
        "confirmation_status": row.confirmation_status,
        "result_status": row.result_status,
        "source": row.source,
        "details": row.details,
    }


async def _wait_for(predicate, *, timeout: float, interval: float = 0.25):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        await asyncio.sleep(interval)
    return None


async def _speak_turn(
    runtime: VoiceRuntime,
    audio_gateway: QueueAudioGateway,
    wav_path: Path,
    *,
    pre_delay_seconds: float = 0.0,
) -> None:
    if pre_delay_seconds > 0:
        await asyncio.sleep(pre_delay_seconds)
    await runtime.begin_manual_capture()
    await audio_gateway.feed_wav(
        wav_path,
        chunk_ms=runtime._settings.voice_input_chunk_ms,
        sample_rate_hz=runtime._settings.voice_input_sample_rate_hz,
    )
    await runtime.end_manual_capture()


async def _wait_for_clarification(runtime: VoiceRuntime, *, timeout: float = 40.0) -> str | None:
    def _snapshot() -> str | None:
        interpretation = runtime._pending_spoken_interpretation
        if interpretation is None:
            return None
        return interpretation.confirmation_prompt or ""

    return await _wait_for(_snapshot, timeout=timeout)


async def _wait_for_new_voice_row(
    journal_rows_fn,
    *,
    before_ids: set[int],
    action_names: set[str] | None = None,
    command_contains: str | None = None,
    timeout: float = 70.0,
) -> dict[str, object] | None:
    def _snapshot() -> dict[str, object] | None:
        for row in journal_rows_fn():
            if row.id in before_ids or row.source != "voice":
                continue
            if action_names and row.action_name not in action_names:
                continue
            if command_contains and command_contains not in row.command_text.lower():
                continue
            return _row_dict(row)
        return None

    return await _wait_for(_snapshot, timeout=timeout)


async def _verify_github(
    runtime: VoiceRuntime,
    audio_gateway: QueueAudioGateway,
    *,
    voice_dir: Path,
    journal_rows_fn,
) -> dict[str, object]:
    result: dict[str, object] = {}

    await _speak_turn(runtime, audio_gateway, voice_dir / "github.wav")
    result["first_turn"] = TurnOutcome(
        clarification=await _wait_for_clarification(runtime),
        last_response=runtime._state.last_response,
        last_status=runtime._state.status.value,
    )

    before_ids = {row.id for row in journal_rows_fn()}
    confirmation_wav = voice_dir / "haan.wav"
    if not confirmation_wav.exists():
        confirmation_wav = voice_dir / "yes.wav"
    await _speak_turn(
        runtime,
        audio_gateway,
        confirmation_wav,
        pre_delay_seconds=1.5,
    )
    row = await _wait_for_new_voice_row(
        journal_rows_fn,
        before_ids=before_ids,
        action_names={"open_website"},
        command_contains="github.com",
    )
    result["final_turn"] = TurnOutcome(
        journal_row=row,
        last_response=runtime._state.last_response,
        last_status=runtime._state.status.value,
    )
    return json.loads(json.dumps(result, default=asdict))


async def _verify_youtube_search(
    runtime: VoiceRuntime,
    audio_gateway: QueueAudioGateway,
    *,
    voice_dir: Path,
    journal_rows_fn,
) -> dict[str, object]:
    result: dict[str, object] = {}
    before_ids = {row.id for row in journal_rows_fn()}

    await _speak_turn(runtime, audio_gateway, voice_dir / "youtube_search.wav")

    def _first_outcome() -> TurnOutcome | None:
        clarification = None
        if runtime._pending_spoken_interpretation is not None:
            clarification = runtime._pending_spoken_interpretation.confirmation_prompt
        row = None
        for journal_row in journal_rows_fn():
            if journal_row.id in before_ids or journal_row.source != "voice":
                continue
            if journal_row.action_name in {
                "search_youtube",
                "play_youtube_playlist",
                "open_youtube",
            }:
                row = _row_dict(journal_row)
                break
        if clarification is None and row is None:
            return None
        return TurnOutcome(
            clarification=clarification,
            journal_row=row,
            last_response=runtime._state.last_response,
            last_status=runtime._state.status.value,
        )

    first_outcome = await _wait_for(_first_outcome, timeout=80.0)
    result["first_turn"] = asdict(first_outcome) if first_outcome is not None else None

    if first_outcome is not None and first_outcome.clarification:
        before_ids = {row.id for row in journal_rows_fn()}
        confirmation_wav = voice_dir / "haan.wav"
        if not confirmation_wav.exists():
            confirmation_wav = voice_dir / "yes.wav"
        await _speak_turn(
            runtime,
            audio_gateway,
            confirmation_wav,
            pre_delay_seconds=1.5,
        )
        row = await _wait_for_new_voice_row(
            journal_rows_fn,
            before_ids=before_ids,
            action_names={"search_youtube", "play_youtube_playlist", "open_youtube"},
        )
        result["final_turn"] = asdict(
            TurnOutcome(
                journal_row=row,
                last_response=runtime._state.last_response,
                last_status=runtime._state.status.value,
            )
        )
    return result


async def _run_scenario(
    *,
    voice_dir: Path,
    scenario: str,
) -> dict[str, object]:
    context = bootstrap_application()
    audio_gateway = QueueAudioGateway()
    runtime = VoiceRuntime(
        settings=context.settings,
        state=context.state,
        journal=context.journal,
        live_client=GeminiLiveSessionClient(
            api_key=context.settings.gemini_api_key,
            api_version=context.settings.gemini_live_api_version,
        ),
        audio_gateway=audio_gateway,
        command_controller=context.controller,
    )

    def journal_rows_fn():
        return context.journal.list_recent(50)

    try:
        if scenario == "github":
            result = await _verify_github(
                runtime,
                audio_gateway,
                voice_dir=voice_dir,
                journal_rows_fn=journal_rows_fn,
            )
        else:
            result = await _verify_youtube_search(
                runtime,
                audio_gateway,
                voice_dir=voice_dir,
                journal_rows_fn=journal_rows_fn,
            )
    finally:
        await runtime.stop()

    return {
        "result": result,
        "playback_chunks_captured": audio_gateway.output_chunks,
        "playback_bytes_captured": audio_gateway.output_bytes,
        "flush_count": audio_gateway.flush_count,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--voice-dir",
        type=Path,
        default=Path.cwd() / "tmp_voice_verify",
        help="Directory containing github.wav, youtube_search.wav, and yes.wav",
    )
    parser.add_argument(
        "--scenario",
        choices=("github", "youtube", "both"),
        default="both",
    )
    args = parser.parse_args()

    payload: dict[str, object] = {}
    if args.scenario in {"github", "both"}:
        payload["github"] = await _run_scenario(voice_dir=args.voice_dir, scenario="github")
    if args.scenario in {"youtube", "both"}:
        payload["youtube"] = await _run_scenario(voice_dir=args.voice_dir, scenario="youtube")

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
