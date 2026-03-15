from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import shutil
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil

from ava.app.bootstrap import bootstrap_application
from ava.automation.windows import app_process_names, known_folder_path
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


async def _wait_for_generation_complete(runtime: VoiceRuntime, *, timeout: float = 12.0) -> bool:
    def _snapshot() -> bool:
        return bool(runtime._generation_complete_received)

    return bool(await _wait_for(_snapshot, timeout=timeout))


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
    action_names: set[str],
    timeout: float = 70.0,
) -> dict[str, object] | None:
    def _snapshot() -> dict[str, object] | None:
        for row in journal_rows_fn():
            if row.id in before_ids or row.source != "voice":
                continue
            if row.action_name not in action_names:
                continue
            return _row_dict(row)
        return None

    return await _wait_for(_snapshot, timeout=timeout)


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


def _confirmation_wav_path(voice_dir: Path) -> Path:
    for candidate in ("confirm.wav", "haan_confirm.wav", "haan.wav", "yes.wav"):
        wav_path = voice_dir / candidate
        if wav_path.exists():
            return wav_path
    raise FileNotFoundError("No spoken confirmation WAV found in voice dir.")


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    return psutil.pid_exists(pid)


def _running_processes(process_names: tuple[str, ...]) -> list[psutil.Process]:
    process_targets = {name.lower() for name in process_names}
    matches: list[psutil.Process] = []
    for proc in psutil.process_iter(["name"]):
        name = (proc.info.get("name") or "").lower()
        if name in process_targets:
            matches.append(proc)
    return matches


async def _wait_for_process(process_names: tuple[str, ...], *, timeout: float = 12.0) -> list[int]:
    def _snapshot() -> list[int] | None:
        matches = _running_processes(process_names)
        if not matches:
            return None
        return [int(proc.pid) for proc in matches]

    result = await _wait_for(_snapshot, timeout=timeout)
    return result or []


async def _wait_for_process_exit(pid: int, *, timeout: float = 12.0) -> bool:
    def _snapshot() -> bool:
        return not _process_exists(pid)

    return bool(await _wait_for(_snapshot, timeout=timeout))


async def _wait_for_foreground_process(
    window_controller,
    process_names: tuple[str, ...],
    *,
    timeout: float = 8.0,
) -> dict[str, object] | None:
    process_targets = {name.lower() for name in process_names}

    def _snapshot() -> dict[str, object] | None:
        info = window_controller.foreground_window_info()
        if info is None:
            return None
        process_name = str(info.get("process_name", "")).lower()
        if process_name in process_targets:
            return dict(info)
        return None

    return await _wait_for(_snapshot, timeout=timeout)


async def _execute_voice_command(
    runtime: VoiceRuntime,
    audio_gateway: QueueAudioGateway,
    *,
    journal_rows_fn,
    voice_dir: Path,
    wav_name: str,
    action_names: set[str],
    expect_confirmation: bool = False,
) -> TurnOutcome:
    before_ids = {row.id for row in journal_rows_fn()}
    await _speak_turn(runtime, audio_gateway, voice_dir / wav_name)
    clarification = await _wait_for_clarification(runtime, timeout=18.0)
    if expect_confirmation:
        if clarification is None:
            raise RuntimeError(f"{wav_name} expected confirmation but none arrived.")
        await _wait_for_generation_complete(runtime)
        await _speak_turn(
            runtime,
            audio_gateway,
            _confirmation_wav_path(voice_dir),
            pre_delay_seconds=1.0,
        )
    row = await _wait_for_new_voice_row(
        journal_rows_fn,
        before_ids=before_ids,
        action_names=action_names,
        timeout=80.0,
    )
    return TurnOutcome(
        clarification=clarification,
        journal_row=row,
        last_response=runtime._state.last_response,
        last_status=runtime._state.status.value,
    )


async def _run_verification(*, voice_dir: Path) -> dict[str, object]:
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
    window_controller = context.controller.executor.window_controller
    created_paths: list[Path] = []
    launched_pids: list[int] = []

    def journal_rows_fn():
        return context.journal.list_recent(80)

    def remember_path_from_row(outcome: TurnOutcome) -> Path | None:
        if outcome.journal_row is None:
            return None
        details = outcome.journal_row.get("details")
        if not isinstance(details, dict):
            return None
        path_value = str(details.get("path", "")).strip()
        return Path(path_value) if path_value else None

    async def verify_open_app(wav_name: str, app_name: str) -> dict[str, object]:
        outcome = await _execute_voice_command(
            runtime,
            audio_gateway,
            journal_rows_fn=journal_rows_fn,
            voice_dir=voice_dir,
            wav_name=wav_name,
            action_names={"open_app"},
        )
        if outcome.journal_row is None:
            raise RuntimeError(f"{app_name} open_app row missing.")
        details = outcome.journal_row.get("details")
        if not isinstance(details, dict):
            raise RuntimeError(f"{app_name} open_app details missing.")
        pid_value = int(str(details.get("pid", "") or 0))
        if pid_value:
            launched_pids.append(pid_value)
        running_pids = await _wait_for_process(app_process_names(app_name))
        return {
            "turn": asdict(outcome),
            "running_pids": running_pids,
            "pid_alive": _process_exists(pid_value),
        }

    async def verify_open_folder(wav_name: str, folder_key: str) -> dict[str, object]:
        outcome = await _execute_voice_command(
            runtime,
            audio_gateway,
            journal_rows_fn=journal_rows_fn,
            voice_dir=voice_dir,
            wav_name=wav_name,
            action_names={"open_folder"},
        )
        opened_path = remember_path_from_row(outcome)
        return {
            "turn": asdict(outcome),
            "opened_path": str(opened_path) if opened_path else "",
            "expected_path": str(known_folder_path(folder_key)),
            "path_matches": bool(opened_path and opened_path == known_folder_path(folder_key)),
        }

    async def verify_create_item(
        wav_name: str,
        action_name: str,
    ) -> dict[str, object]:
        outcome = await _execute_voice_command(
            runtime,
            audio_gateway,
            journal_rows_fn=journal_rows_fn,
            voice_dir=voice_dir,
            wav_name=wav_name,
            action_names={action_name},
        )
        created_path = remember_path_from_row(outcome)
        if created_path is not None:
            created_paths.append(created_path)
        return {
            "turn": asdict(outcome),
            "path": str(created_path) if created_path else "",
            "exists": bool(created_path and created_path.exists()),
        }

    async def verify_confirmed_action(
        wav_name: str,
        action_name: str,
    ) -> dict[str, object]:
        outcome = await _execute_voice_command(
            runtime,
            audio_gateway,
            journal_rows_fn=journal_rows_fn,
            voice_dir=voice_dir,
            wav_name=wav_name,
            action_names={action_name},
            expect_confirmation=True,
        )
        target_path = remember_path_from_row(outcome)
        if target_path is not None:
            created_paths.append(target_path)
        return {
            "turn": asdict(outcome),
            "path": str(target_path) if target_path else "",
            "exists": bool(target_path and target_path.exists()),
        }

    payload: dict[str, object] = {}

    try:
        payload["notepad_open"] = await verify_open_app("notepad_open.wav", "notepad")
        payload["calculator_open"] = await verify_open_app("calculator_open.wav", "calculator")
        payload["paint_open"] = await verify_open_app("paint_open.wav", "paint")

        payload["downloads_open"] = await verify_open_folder("downloads_open.wav", "downloads")
        payload["documents_open"] = await verify_open_folder("documents_open.wav", "documents")
        payload["desktop_open"] = await verify_open_folder("desktop_open.wav", "desktop")
        payload["documents_open_again"] = await verify_open_folder(
            "documents_open.wav",
            "documents",
        )

        payload["create_file_here"] = await verify_create_item(
            "create_file_here.wav",
            "create_file",
        )
        original_file_path = remember_path_from_row(
            TurnOutcome(journal_row=payload["create_file_here"]["turn"]["journal_row"])  # type: ignore[index]
        )
        payload["create_folder_here"] = await verify_create_item(
            "create_folder_here.wav",
            "create_folder",
        )
        original_folder_path = remember_path_from_row(
            TurnOutcome(journal_row=payload["create_folder_here"]["turn"]["journal_row"])  # type: ignore[index]
        )

        payload["rename_file"] = await verify_confirmed_action(
            "rename_file_context.wav",
            "rename_path",
        )
        renamed_file_path = remember_path_from_row(
            TurnOutcome(journal_row=payload["rename_file"]["turn"]["journal_row"])  # type: ignore[index]
        )
        payload["rename_file"]["original_missing"] = bool(
            original_file_path and not original_file_path.exists()
        )
        payload["rename_file"]["renamed_name"] = (
            renamed_file_path.name if renamed_file_path is not None else ""
        )

        payload["move_folder"] = await verify_confirmed_action(
            "move_folder_context.wav",
            "move_path",
        )
        moved_folder_path = remember_path_from_row(
            TurnOutcome(journal_row=payload["move_folder"]["turn"]["journal_row"])  # type: ignore[index]
        )
        payload["move_folder"]["original_missing"] = bool(
            original_folder_path and not original_folder_path.exists()
        )
        payload["move_folder"]["in_downloads"] = bool(
            moved_folder_path and known_folder_path("downloads") in moved_folder_path.parents
        )

        with contextlib.suppress(Exception):
            window_controller.focus_app_window("paint")

        payload["window_maximize"] = asdict(
            await _execute_voice_command(
                runtime,
                audio_gateway,
                journal_rows_fn=journal_rows_fn,
                voice_dir=voice_dir,
                wav_name="window_maximize.wav",
                action_names={"maximize_window"},
            )
        )
        payload["window_minimize"] = asdict(
            await _execute_voice_command(
                runtime,
                audio_gateway,
                journal_rows_fn=journal_rows_fn,
                voice_dir=voice_dir,
                wav_name="window_minimize.wav",
                action_names={"minimize_window"},
            )
        )

        with contextlib.suppress(Exception):
            window_controller.focus_app_window("paint")
        before_switch = window_controller.foreground_window_info()
        next_window_outcome = await _execute_voice_command(
            runtime,
            audio_gateway,
            journal_rows_fn=journal_rows_fn,
            voice_dir=voice_dir,
            wav_name="next_window.wav",
            action_names={"next_window"},
        )
        after_switch = window_controller.foreground_window_info()
        payload["next_window"] = {
            "turn": asdict(next_window_outcome),
            "before": before_switch,
            "after": after_switch,
            "foreground_changed": bool(
                before_switch
                and after_switch
                and before_switch.get("hwnd") != after_switch.get("hwnd")
            ),
        }

        with contextlib.suppress(Exception):
            window_controller.focus_app_window("notepad")
        focus_before = window_controller.foreground_window_info()
        focus_outcome = await _execute_voice_command(
            runtime,
            audio_gateway,
            journal_rows_fn=journal_rows_fn,
            voice_dir=voice_dir,
            wav_name="focus_current_app.wav",
            action_names={"focus_app"},
        )
        focus_after = await _wait_for_foreground_process(
            window_controller,
            app_process_names("paint"),
            timeout=10.0,
        )
        payload["focus_current_app"] = {
            "turn": asdict(focus_outcome),
            "before": focus_before,
            "after": focus_after,
        }

        notepad_pid = 0
        notepad_turn = payload["notepad_open"]["turn"]  # type: ignore[index]
        if isinstance(notepad_turn, dict):
            row = notepad_turn.get("journal_row")
            if isinstance(row, dict):
                details = row.get("details")
                if isinstance(details, dict):
                    notepad_pid = int(str(details.get("pid", "") or 0))
        close_outcome = await _execute_voice_command(
            runtime,
            audio_gateway,
            journal_rows_fn=journal_rows_fn,
            voice_dir=voice_dir,
            wav_name="notepad_close.wav",
            action_names={"close_app"},
        )
        payload["notepad_close"] = {
            "turn": asdict(close_outcome),
            "pid_closed": await _wait_for_process_exit(notepad_pid, timeout=10.0)
            if notepad_pid
            else False,
        }
    finally:
        await runtime.stop()
        for app_name in ("paint", "calculator", "notepad"):
            with contextlib.suppress(Exception):
                window_controller.close_app(app_name)
        cleanup_paths = sorted(
            {path for path in created_paths if path.exists()},
            key=lambda item: len(item.parts),
            reverse=True,
        )
        for path in cleanup_paths:
            with contextlib.suppress(Exception):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

    return {
        "results": payload,
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
        help="Directory containing spoken Windows command WAVs.",
    )
    args = parser.parse_args()
    payload = await _run_verification(voice_dir=args.voice_dir)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
