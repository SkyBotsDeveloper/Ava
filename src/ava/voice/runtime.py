from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass

from ava.app.state import AssistantState, AssistantStatus
from ava.config.settings import Settings
from ava.live.interfaces import (
    AudioChunkEvent,
    LiveSessionClient,
    LiveSessionConfig,
    ResponseModality,
    TranscriptEvent,
    TurnBoundaryEvent,
    VoiceActivityEvent,
)
from ava.live.prompting import AVA_SYSTEM_INSTRUCTION
from ava.memory.journal import ActionJournalStore
from ava.safety.policy import ConfirmationStatus, ResultStatus
from ava.voice.interfaces import AudioGateway, WakeWordEngine
from ava.voice.vad import VoiceActivityDetector

try:
    from google import genai
except ImportError:  # pragma: no cover - optional dependency guard
    genai = None

try:
    import numpy as np
    import sounddevice as sd
except ImportError:  # pragma: no cover - optional dependency guard
    np = None
    sd = None

try:
    from openwakeword.model import Model
except ImportError:  # pragma: no cover - optional dependency guard
    Model = None


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class VoiceRuntimeAvailability:
    live_text_ready: bool
    audio_ready: bool
    wake_ready: bool
    blockers: tuple[str, ...]


class VoiceRuntime:
    def __init__(
        self,
        *,
        settings: Settings,
        state: AssistantState,
        journal: ActionJournalStore,
        live_client: LiveSessionClient,
        audio_gateway: AudioGateway | None = None,
        wake_word_engine: WakeWordEngine | None = None,
        on_state_changed: Callable[[], None] | None = None,
        on_journal_changed: Callable[[], None] | None = None,
    ) -> None:
        self._settings = settings
        self._state = state
        self._journal = journal
        self._live_client = live_client
        self._audio_gateway = audio_gateway
        self._wake_word_engine = wake_word_engine
        self._on_state_changed = on_state_changed
        self._on_journal_changed = on_journal_changed
        self._availability = self.inspect_availability(settings)
        self._receive_task: asyncio.Task[None] | None = None
        self._wake_task: asyncio.Task[None] | None = None
        self._capture_active = False
        self._speech_detected = False
        self._silence_ms = 0
        self._vad = VoiceActivityDetector()

    @property
    def availability(self) -> VoiceRuntimeAvailability:
        return self._availability

    @staticmethod
    def inspect_availability(settings: Settings) -> VoiceRuntimeAvailability:
        blockers: list[str] = []

        live_text_ready = bool(settings.gemini_api_key and genai is not None)
        if not settings.gemini_api_key:
            blockers.append("Gemini Live needs `AVA_GEMINI_API_KEY`.")
        elif genai is None:
            blockers.append("`google-genai` is not installed.")

        audio_ready = bool(sd is not None and np is not None)
        if not audio_ready:
            blockers.append("Audio pipeline needs `sounddevice` and `numpy`.")

        wake_ready = bool(audio_ready and Model is not None and settings.wakeword_model_paths)
        if Model is None:
            blockers.append("Wake-word detection needs `openwakeword`.")
        elif not settings.wakeword_model_paths:
            blockers.append("Wake-word detection needs `AVA_WAKEWORD_MODEL_PATHS`.")

        return VoiceRuntimeAvailability(
            live_text_ready=live_text_ready,
            audio_ready=audio_ready,
            wake_ready=wake_ready,
            blockers=tuple(dict.fromkeys(blockers)),
        )

    def build_live_config(self) -> LiveSessionConfig:
        return LiveSessionConfig(
            model_name=self._settings.gemini_live_model,
            locale=self._settings.gemini_live_locale,
            voice_name=self._settings.gemini_live_voice_name,
            response_modalities=(ResponseModality.AUDIO,),
            system_instruction=AVA_SYSTEM_INSTRUCTION,
            input_sample_rate_hz=self._settings.voice_input_sample_rate_hz,
            output_sample_rate_hz=self._settings.voice_output_sample_rate_hz,
            enable_input_transcription=self._settings.gemini_live_enable_input_transcription,
            enable_output_transcription=self._settings.gemini_live_enable_output_transcription,
            enable_server_vad=self._settings.gemini_live_enable_server_vad,
            vad_prefix_padding_ms=self._settings.gemini_live_vad_prefix_padding_ms,
            vad_silence_ms=self._settings.gemini_live_vad_silence_ms,
            thinking_budget=self._settings.gemini_live_thinking_budget,
        )

    async def start(self) -> None:
        if (
            not self._availability.wake_ready
            or self._audio_gateway is None
            or self._wake_word_engine is None
        ):
            return
        await self._audio_gateway.start_input()
        await self._wake_word_engine.start()
        self._wake_task = asyncio.create_task(self._wake_loop(), name="ava-wake-loop")

    async def stop(self) -> None:
        self._capture_active = False
        if self._wake_task is not None:
            self._wake_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._wake_task
            self._wake_task = None
        if self._receive_task is not None:
            self._receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receive_task
            self._receive_task = None
        if self._wake_word_engine is not None:
            await self._wake_word_engine.stop()
        if self._audio_gateway is not None:
            await self._audio_gateway.stop_input()
            await self._audio_gateway.interrupt_output()
        await self._disconnect_live()

    async def submit_text(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return

        self._state.last_command = cleaned
        self._state.status = AssistantStatus.THINKING
        self._state.last_response = "Soch rahi hoon."
        self._notify_state()

        if not self._availability.live_text_ready:
            self._state.status = AssistantStatus.IDLE
            self._state.last_response = "Gemini Live abhi configured nahi hai. API key chahiye."
            self._record_action(
                command_text=cleaned,
                action_name="live_text_turn",
                result_status=ResultStatus.FAILURE,
                details={"reason": "gemini_live_unavailable"},
            )
            self._notify_state()
            return

        try:
            await self._ensure_live_session()
            self._ensure_receive_task()
            await self._live_client.send_text(cleaned, end_of_turn=True)
            self._record_action(
                command_text=cleaned,
                action_name="live_text_turn",
                result_status=ResultStatus.PLANNED,
                details={"model": self._settings.gemini_live_model},
            )
        except Exception as exc:  # pragma: no cover - network / device dependent
            logger.exception("Gemini Live text submit failed")
            self._state.status = AssistantStatus.IDLE
            self._state.last_response = f"Gemini Live connect nahi hua: {exc}"
            self._record_action(
                command_text=cleaned,
                action_name="live_text_turn",
                result_status=ResultStatus.FAILURE,
                details={"error": str(exc)},
            )
            self._notify_state()

    async def set_muted(self, muted: bool) -> None:
        self._state.muted = muted
        if self._audio_gateway is None:
            self._notify_state()
            return
        if muted:
            await self._audio_gateway.mute()
        else:
            await self._audio_gateway.unmute()
        self._notify_state()

    async def cancel(self) -> None:
        self._capture_active = False
        self._speech_detected = False
        self._silence_ms = 0
        if self._audio_gateway is not None:
            await self._audio_gateway.interrupt_output()
        await self._disconnect_live()
        self._state.status = AssistantStatus.IDLE
        self._notify_state()

    async def _wake_loop(self) -> None:
        if self._audio_gateway is None or self._wake_word_engine is None:
            return

        async for chunk in self._audio_gateway.input_chunks():
            try:
                if self._capture_active:
                    await self._forward_voice_chunk(chunk.data, chunk.sample_rate_hz)
                    continue

                event = await self._wake_word_engine.process_chunk(chunk)
                if event is None:
                    continue

                if not self._availability.live_text_ready:
                    self._state.status = AssistantStatus.IDLE
                    self._state.last_response = "Wake suna, but Gemini Live key abhi missing hai."
                    self._notify_state()
                    continue

                self._state.last_command = event.phrase
                self._state.last_response = "Haan, boliye."
                self._state.status = AssistantStatus.LISTENING
                self._notify_state()

                await self._ensure_live_session()
                self._ensure_receive_task()
                await self._live_client.send_activity_start()
                self._capture_active = True
                self._speech_detected = True
                self._silence_ms = 0
                await self._forward_voice_chunk(chunk.data, chunk.sample_rate_hz)
            except asyncio.CancelledError:
                raise
            except Exception:  # pragma: no cover - device / live runtime dependent
                logger.exception("Wake loop failed")
                self._state.status = AssistantStatus.IDLE
                self._state.last_response = "Voice pipeline me issue aa gaya."
                self._notify_state()

    async def _forward_voice_chunk(self, pcm_bytes: bytes, sample_rate_hz: int) -> None:
        await self._live_client.send_audio_chunk(
            pcm_bytes,
            mime_type=f"audio/pcm;rate={sample_rate_hz}",
        )

        if self._vad.available and self._vad.contains_speech(pcm_bytes, sample_rate_hz):
            self._speech_detected = True
            self._silence_ms = 0
            self._state.status = AssistantStatus.LISTENING
            self._notify_state()
            return

        if not self._speech_detected:
            return

        self._silence_ms += self._settings.voice_input_chunk_ms
        if self._silence_ms < self._settings.gemini_live_vad_silence_ms:
            return

        await self._live_client.send_activity_end()
        self._capture_active = False
        self._speech_detected = False
        self._silence_ms = 0
        self._state.status = AssistantStatus.THINKING
        self._notify_state()

    async def _ensure_live_session(self) -> None:
        await self._live_client.connect(self.build_live_config())

    def _ensure_receive_task(self) -> None:
        if self._receive_task is None or self._receive_task.done():
            self._receive_task = asyncio.create_task(
                self._receive_loop(),
                name="ava-live-receive",
            )

    async def _disconnect_live(self) -> None:
        await self._live_client.disconnect()

    async def _receive_loop(self) -> None:
        try:
            async for event in self._live_client.receive():
                if isinstance(event, TranscriptEvent):
                    self._apply_transcript(event)
                elif isinstance(event, AudioChunkEvent):
                    await self._apply_audio(event)
                elif isinstance(event, TurnBoundaryEvent):
                    self._apply_turn_boundary(event)
                elif isinstance(event, VoiceActivityEvent):
                    self._apply_voice_activity(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - network / device dependent
            logger.exception("Gemini Live receive loop failed")
            self._state.status = AssistantStatus.IDLE
            self._state.last_response = f"Live session ruk gaya: {exc}"
            self._notify_state()

    def _apply_transcript(self, event: TranscriptEvent) -> None:
        if event.is_input:
            if event.text:
                self._state.last_command = event.text
        else:
            if event.text:
                self._state.last_response = event.text
                self._state.status = AssistantStatus.SPEAKING
        self._notify_state()

    async def _apply_audio(self, event: AudioChunkEvent) -> None:
        self._state.status = AssistantStatus.SPEAKING
        self._notify_state()
        if self._audio_gateway is None or self._state.muted:
            return
        await self._audio_gateway.play_output_chunk(
            event.data,
            sample_rate_hz=self._extract_sample_rate(event.mime_type),
        )

    def _apply_turn_boundary(self, event: TurnBoundaryEvent) -> None:
        if event.phase in {"generation_complete", "turn_complete", "waiting_for_input"}:
            self._state.status = AssistantStatus.IDLE
            self._notify_state()
        elif event.phase == "interrupted":
            self._state.status = AssistantStatus.THINKING
            self._notify_state()

    def _apply_voice_activity(self, event: VoiceActivityEvent) -> None:
        normalized = event.phase.lower()
        if "start" in normalized:
            self._state.status = AssistantStatus.LISTENING
        elif "end" in normalized:
            self._state.status = AssistantStatus.THINKING
        self._notify_state()

    def _record_action(
        self,
        *,
        command_text: str,
        action_name: str,
        result_status: ResultStatus,
        details: dict[str, str] | None = None,
    ) -> None:
        self._journal.record_action(
            command_text=command_text,
            action_name=action_name,
            confirmation_status=ConfirmationStatus.NOT_NEEDED,
            result_status=result_status,
            source="voice_runtime",
            details=details,
        )
        if self._on_journal_changed is not None:
            self._on_journal_changed()

    def _notify_state(self) -> None:
        if self._on_state_changed is not None:
            self._on_state_changed()

    def _extract_sample_rate(self, mime_type: str) -> int:
        default_rate = self._settings.voice_output_sample_rate_hz
        if "rate=" not in mime_type:
            return default_rate
        try:
            return int(mime_type.split("rate=", maxsplit=1)[1])
        except ValueError:
            return default_rate
