from __future__ import annotations

import asyncio
import contextlib
import threading
from concurrent.futures import Future

from PySide6.QtCore import QObject, Signal

from ava.app.controller import AvaController
from ava.app.state import AssistantState
from ava.config.settings import Settings
from ava.live.gemini import GeminiLiveSessionClient
from ava.memory.journal import ActionJournalStore
from ava.voice.audio import SoundDeviceAudioGateway
from ava.voice.openwakeword_engine import OpenWakeWordEngine
from ava.voice.runtime import VoiceRuntime


class VoiceRuntimeSignals(QObject):
    stateChanged = Signal()
    journalChanged = Signal()


class VoiceRuntimeService:
    def __init__(
        self,
        *,
        settings: Settings,
        state: AssistantState,
        journal: ActionJournalStore,
        controller: AvaController | None = None,
    ) -> None:
        self.settings = settings
        self.state = state
        self.journal = journal
        self.controller = controller
        self.signals = VoiceRuntimeSignals()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._runtime: VoiceRuntime | None = None
        self._availability = VoiceRuntime.inspect_availability(settings)

    @property
    def blockers(self) -> tuple[str, ...]:
        return self._availability.blockers

    @property
    def live_ready(self) -> bool:
        return self._availability.live_text_ready

    @property
    def wake_ready(self) -> bool:
        return self._availability.wake_ready

    @property
    def manual_voice_ready(self) -> bool:
        return self._availability.manual_voice_ready

    def start(self) -> None:
        if self._thread is not None:
            return

        self._thread = threading.Thread(
            target=self._run_loop,
            name="ava-voice-runtime",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=5)
        if self._loop is None:
            raise RuntimeError("Voice runtime loop did not start.")
        self._submit(self._runtime.start()).result(timeout=10)

    def shutdown(self) -> None:
        if self._loop is None:
            return

        runtime = self._runtime
        if runtime is not None:
            with contextlib.suppress(Exception):
                self._submit(runtime.stop()).result(timeout=10)

        loop = self._loop
        thread = self._thread
        self._loop = None
        self._runtime = None
        self._thread = None
        self._ready.clear()
        loop.call_soon_threadsafe(loop.stop)
        if thread is not None:
            thread.join(timeout=10)

    def submit_text(self, text: str) -> None:
        if self._runtime is None:
            raise RuntimeError("Voice runtime is not started.")
        self._submit(self._runtime.submit_text(text))

    def set_muted(self, muted: bool) -> None:
        if self._runtime is None:
            return
        self._submit(self._runtime.set_muted(muted))

    def cancel(self) -> None:
        if self._runtime is None:
            return
        self._submit(self._runtime.cancel())

    def toggle_manual_capture(self) -> None:
        if self._runtime is None:
            return
        self._submit(self._runtime.toggle_manual_capture())

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._runtime = VoiceRuntime(
            settings=self.settings,
            state=self.state,
            journal=self.journal,
            live_client=GeminiLiveSessionClient(
                api_key=self.settings.gemini_api_key,
                api_version=self.settings.gemini_live_api_version,
            ),
            audio_gateway=SoundDeviceAudioGateway(
                input_sample_rate_hz=self.settings.voice_input_sample_rate_hz,
                input_chunk_ms=self.settings.voice_input_chunk_ms,
            )
            if self._availability.audio_ready
            else None,
            wake_word_engine=OpenWakeWordEngine(
                model_paths=self.settings.wakeword_model_paths,
                trigger_phrase=self.settings.wakeword_trigger_phrase,
                threshold=self.settings.wakeword_threshold,
                patience_frames=self.settings.wakeword_patience_frames,
            )
            if self._availability.wake_ready
            else None,
            command_controller=self.controller,
            on_state_changed=self.signals.stateChanged.emit,
            on_journal_changed=self.signals.journalChanged.emit,
        )
        self._ready.set()
        try:
            loop.run_forever()
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            with contextlib.suppress(Exception):
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()

    def _submit(self, coroutine) -> Future:
        if self._loop is None:
            raise RuntimeError("Voice runtime loop is not available.")
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)
