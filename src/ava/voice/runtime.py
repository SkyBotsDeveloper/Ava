from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass

from ava.app.controller import AvaController
from ava.app.state import AssistantState, AssistantStatus
from ava.config.settings import Settings
from ava.intents.models import IntentType
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
from ava.voice.spoken_normalizer import SpokenCommandNormalizer, SpokenInterpretation
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
    manual_voice_ready: bool
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
        command_controller: AvaController | None = None,
        spoken_command_normalizer: SpokenCommandNormalizer | None = None,
        on_state_changed: Callable[[], None] | None = None,
        on_journal_changed: Callable[[], None] | None = None,
    ) -> None:
        self._settings = settings
        self._state = state
        self._journal = journal
        self._live_client = live_client
        self._audio_gateway = audio_gateway
        self._wake_word_engine = wake_word_engine
        self._command_controller = command_controller
        self._spoken_normalizer = spoken_command_normalizer or SpokenCommandNormalizer()
        self._on_state_changed = on_state_changed
        self._on_journal_changed = on_journal_changed
        self._availability = self.inspect_availability(settings)
        self._receive_task: asyncio.Task[None] | None = None
        self._input_task: asyncio.Task[None] | None = None
        self._audio_started = False
        self._capture_active = False
        self._speech_detected = False
        self._silence_ms = 0
        self._input_transcript = ""
        self._output_transcript = ""
        self._audio_frame_count = 0
        self._audio_byte_count = 0
        self._output_audio_chunk_count = 0
        self._vad = VoiceActivityDetector()
        self._generation_complete_received = False
        self._pending_voice_command_text: str | None = None
        self._pending_spoken_interpretation: SpokenInterpretation | None = None
        self._browser_command_priority_active = False
        self._command_feedback_in_progress = False
        self._suppress_model_output = False

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

        manual_voice_ready = bool(live_text_ready and audio_ready)
        wake_ready = bool(audio_ready and Model is not None and settings.wakeword_model_paths)
        if Model is None:
            blockers.append("Wake-word detection needs `openwakeword`.")
        elif not settings.wakeword_model_paths:
            blockers.append("Wake-word detection needs `AVA_WAKEWORD_MODEL_PATHS`.")

        return VoiceRuntimeAvailability(
            live_text_ready=live_text_ready,
            audio_ready=audio_ready,
            manual_voice_ready=manual_voice_ready,
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
            # Ava currently drives explicit start/end boundaries for manual trigger and wake flows.
            enable_server_vad=False,
            vad_prefix_padding_ms=self._settings.gemini_live_vad_prefix_padding_ms,
            vad_silence_ms=self._settings.gemini_live_vad_silence_ms,
            thinking_budget=self._settings.gemini_live_thinking_budget,
        )

    async def start(self) -> None:
        if not self._availability.wake_ready:
            return
        await self._ensure_audio_input()

    async def stop(self) -> None:
        self._capture_active = False
        if self._input_task is not None:
            self._input_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._input_task
            self._input_task = None
        if self._receive_task is not None:
            self._receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receive_task
            self._receive_task = None
        if self._audio_started and self._wake_word_engine is not None:
            await self._wake_word_engine.stop()
        if self._audio_started and self._audio_gateway is not None:
            await self._audio_gateway.stop_input()
            await self._audio_gateway.interrupt_output()
            self._audio_started = False
        await self._disconnect_live()

    async def submit_text(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return

        self._reset_turn_metrics()
        self._state.last_command = cleaned
        self._state.status = AssistantStatus.THINKING
        self._state.last_response = "Soch rahi hoon."
        self._output_transcript = ""
        self._generation_complete_received = False
        logger.info(
            "Manual text fallback submitted",
            extra={
                "event": "manual_text_submitted",
                "text_preview": cleaned[:120],
            },
        )
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
        logger.info(
            "Voice runtime mute changed",
            extra={"event": "voice_mute_changed", "muted": muted},
        )
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
        self._pending_voice_command_text = None
        self._pending_spoken_interpretation = None
        self._browser_command_priority_active = False
        self._command_feedback_in_progress = False
        self._suppress_model_output = False
        if self._audio_gateway is not None:
            await self._audio_gateway.interrupt_output()
        if self._receive_task is not None:
            self._receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receive_task
            self._receive_task = None
        await self._disconnect_live()
        self._state.last_response = "Theek hai, cancel kar diya."
        self._state.status = AssistantStatus.IDLE
        logger.info(
            "Voice runtime canceled",
            extra={
                "event": "voice_runtime_canceled",
                "audio_frames_sent": self._audio_frame_count,
                "audio_bytes_sent": self._audio_byte_count,
                "output_audio_chunks": self._output_audio_chunk_count,
            },
        )
        self._notify_state()

    async def begin_manual_capture(self) -> None:
        if self._capture_active:
            return
        if not self._availability.manual_voice_ready:
            self._state.last_response = "Manual voice abhi ready nahi hai."
            self._state.status = AssistantStatus.IDLE
            self._notify_state()
            return

        self._reset_turn_metrics()
        await self._ensure_audio_input()
        await self._ensure_live_session()
        self._ensure_receive_task()
        await self._live_client.send_activity_start()
        awaiting_spoken_clarification = self._pending_spoken_interpretation is not None

        self._capture_active = True
        self._speech_detected = False
        self._silence_ms = 0
        self._input_transcript = ""
        self._output_transcript = ""
        self._generation_complete_received = False
        self._pending_voice_command_text = None
        self._command_feedback_in_progress = False
        self._suppress_model_output = False
        self._browser_command_priority_active = False
        self._state.status = AssistantStatus.LISTENING
        self._state.last_response = (
            self._pending_spoken_interpretation.confirmation_prompt
            if awaiting_spoken_clarification
            else "Haan, boliye."
        )
        self._record_action(
            command_text="manual_trigger",
            action_name="manual_voice_trigger",
            result_status=ResultStatus.PLANNED,
            details={
                "hotkey": self._settings.push_to_talk_hotkey,
                "awaiting_spoken_clarification": awaiting_spoken_clarification,
            },
        )
        logger.info(
            "Manual voice trigger started",
            extra={
                "event": "manual_trigger_started",
                "hotkey": self._settings.push_to_talk_hotkey,
                "awaiting_spoken_clarification": awaiting_spoken_clarification,
            },
        )
        self._notify_state()

    async def end_manual_capture(self) -> None:
        if not self._capture_active:
            return
        await self._live_client.send_activity_end()
        self._capture_active = False
        self._speech_detected = False
        self._silence_ms = 0
        self._state.status = AssistantStatus.THINKING
        logger.info(
            "Manual voice trigger stopped",
            extra={
                "event": "manual_trigger_stopped",
                "audio_frames_sent": self._audio_frame_count,
                "audio_bytes_sent": self._audio_byte_count,
            },
        )
        self._notify_state()

    async def toggle_manual_capture(self) -> None:
        if self._capture_active:
            await self.end_manual_capture()
        else:
            await self.begin_manual_capture()

    async def _ensure_audio_input(self) -> None:
        if self._audio_gateway is None:
            raise RuntimeError("Audio gateway is not available.")
        if self._audio_started and self._input_task is not None and not self._input_task.done():
            return

        await self._audio_gateway.start_input()
        self._audio_started = True
        if self._availability.wake_ready and self._wake_word_engine is not None:
            await self._wake_word_engine.start()
        self._input_task = asyncio.create_task(self._input_loop(), name="ava-audio-input")

    async def _input_loop(self) -> None:
        if self._audio_gateway is None:
            return

        async for chunk in self._audio_gateway.input_chunks():
            try:
                if self._capture_active:
                    await self._forward_voice_chunk(chunk.data, chunk.sample_rate_hz)
                    continue

                if not self._availability.wake_ready or self._wake_word_engine is None:
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
                logger.exception("Audio input loop failed")
                self._state.status = AssistantStatus.IDLE
                self._state.last_response = "Voice pipeline me issue aa gaya."
                self._notify_state()

    async def _forward_voice_chunk(self, pcm_bytes: bytes, sample_rate_hz: int) -> None:
        self._audio_frame_count += 1
        self._audio_byte_count += len(pcm_bytes)
        if self._audio_frame_count == 1 or self._audio_frame_count % 25 == 0:
            logger.info(
                "Audio frames streamed to Gemini Live",
                extra={
                    "event": "audio_frames_streamed",
                    "audio_frames_sent": self._audio_frame_count,
                    "audio_bytes_sent": self._audio_byte_count,
                    "sample_rate_hz": sample_rate_hz,
                },
            )
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
                    await self._apply_turn_boundary(event)
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
                self._input_transcript = self._merge_transcript(self._input_transcript, event.text)
                self._state.last_command = self._input_transcript
                logger.info(
                    "Input transcript received",
                    extra={
                        "event": "input_transcript_received",
                        "is_final": event.is_final,
                        "transcript": self._input_transcript,
                    },
                )
                self._detect_voice_command_candidate(final_chunk=event.is_final)
        else:
            if event.text:
                self._output_transcript = self._merge_transcript(
                    self._output_transcript,
                    event.text,
                )
                if self._browser_command_priority_active and not self._command_feedback_in_progress:
                    if self._try_recover_browser_command_from_model_output():
                        self._notify_state()
                        return
                    logger.info(
                        "Suppressed conversational model output during browser-priority turn",
                        extra={
                            "event": "browser_priority_model_output_suppressed",
                            "transcript": self._output_transcript,
                        },
                    )
                    return
                if self._suppress_model_output and not self._command_feedback_in_progress:
                    return
                if self._try_recover_browser_command_from_model_output():
                    self._notify_state()
                    return
                self._state.last_response = self._output_transcript
                self._state.status = AssistantStatus.SPEAKING
                logger.info(
                    "Model response transcript received",
                    extra={
                        "event": "model_transcript_received",
                        "is_final": event.is_final,
                        "transcript": self._output_transcript,
                    },
                )
        self._notify_state()

    async def _apply_audio(self, event: AudioChunkEvent) -> None:
        if self._suppress_model_output and not self._command_feedback_in_progress:
            return
        self._state.status = AssistantStatus.SPEAKING
        self._output_audio_chunk_count += 1
        logger.info(
            "Model audio chunk received",
            extra={
                "event": "model_audio_received",
                "output_audio_chunks": self._output_audio_chunk_count,
                "mime_type": event.mime_type,
                "byte_count": len(event.data),
            },
        )
        self._notify_state()
        if self._audio_gateway is None or self._state.muted:
            return
        await self._audio_gateway.play_output_chunk(
            event.data,
            sample_rate_hz=self._extract_sample_rate(event.mime_type),
        )

    async def _apply_turn_boundary(self, event: TurnBoundaryEvent) -> None:
        logger.info(
            "Gemini Live turn boundary received",
            extra={
                "event": "turn_boundary_received",
                "phase": event.phase,
                "reason": event.reason,
            },
        )
        if (
            event.phase in {"turn_complete", "waiting_for_input"}
            and not self._pending_voice_command_text
        ):
            self._detect_voice_command_candidate(final_chunk=True)
        if (
            event.phase in {"turn_complete", "waiting_for_input"}
            and self._pending_voice_command_text
            and not self._command_feedback_in_progress
        ):
            await self._execute_voice_command()
            return
        if (
            event.phase in {"turn_complete", "waiting_for_input"}
            and self._pending_spoken_interpretation is not None
            and not self._pending_voice_command_text
        ):
            self._state.status = AssistantStatus.IDLE
            self._notify_state()
            return
        if (
            event.phase in {"turn_complete", "waiting_for_input"}
            and self._browser_command_priority_active
            and not self._pending_voice_command_text
            and self._pending_spoken_interpretation is None
        ):
            self._state.last_response = "Browser command clear nahi tha. Dobara short me bolo."
            logger.info(
                "Browser command needs clarification after turn end",
                extra={
                    "event": "browser_command_clarification_required",
                    "input_transcript": self._input_transcript,
                    "output_transcript": self._output_transcript,
                },
            )
            await self._finish_model_turn()
            return
        if event.phase == "generation_complete":
            self._generation_complete_received = True
            if self._state.status is not AssistantStatus.SPEAKING:
                self._state.status = AssistantStatus.THINKING
                self._notify_state()
            return
        if event.phase in {"turn_complete", "waiting_for_input"}:
            await self._finish_model_turn()
        elif event.phase == "interrupted":
            if self._audio_gateway is not None:
                await self._audio_gateway.interrupt_output()
            self._state.status = AssistantStatus.THINKING
            self._notify_state()

    def _apply_voice_activity(self, event: VoiceActivityEvent) -> None:
        normalized = event.phase.lower()
        logger.info(
            "Voice activity event received",
            extra={"event": "voice_activity_received", "phase": normalized},
        )
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

    def _reset_turn_metrics(self) -> None:
        self._audio_frame_count = 0
        self._audio_byte_count = 0
        self._output_audio_chunk_count = 0
        self._generation_complete_received = False

    async def _finish_model_turn(self) -> None:
        if (
            self._audio_gateway is not None
            and self._output_audio_chunk_count > 0
            and not self._state.muted
        ):
            await self._audio_gateway.flush_output()
        self._state.status = AssistantStatus.IDLE
        self._input_transcript = ""
        self._output_transcript = ""
        self._generation_complete_received = False
        self._pending_voice_command_text = None
        self._pending_spoken_interpretation = None
        self._browser_command_priority_active = False
        self._command_feedback_in_progress = False
        self._suppress_model_output = False
        self._notify_state()

    def _extract_sample_rate(self, mime_type: str) -> int:
        default_rate = self._settings.voice_output_sample_rate_hz
        if "rate=" not in mime_type:
            return default_rate
        try:
            return int(mime_type.split("rate=", maxsplit=1)[1])
        except ValueError:
            return default_rate

    @staticmethod
    def _merge_transcript(current: str, incoming: str) -> str:
        chunk = incoming.strip()
        if not chunk:
            return current
        if not current:
            return chunk
        if chunk.startswith(current):
            return chunk
        if current.startswith(chunk) or chunk in current:
            return current
        separator = (
            "" if current.endswith((" ", "\n")) or chunk.startswith((".", ",", "!", "?")) else " "
        )
        return f"{current}{separator}{chunk}"

    def _detect_voice_command_candidate(self, *, final_chunk: bool = False) -> None:
        if self._command_controller is None:
            return
        transcript = self._input_transcript.strip()
        if not transcript:
            return
        intent_router = self._command_controller.intent_router
        if self._pending_spoken_interpretation is not None:
            confirmation_intent = intent_router.parse(transcript, source="voice")
            if confirmation_intent.intent_type is IntentType.CONFIRM:
                interpretation = self._pending_spoken_interpretation
                self._pending_spoken_interpretation = None
                self._pending_voice_command_text = interpretation.normalized_text
                self._input_transcript = ""
                self._suppress_model_output = True
                logger.info(
                    "Spoken clarification confirmed",
                    extra={
                        "event": "spoken_clarification_confirmed",
                        "normalized_command": interpretation.normalized_text,
                    },
                )
                return
            if confirmation_intent.intent_type in {IntentType.DENY, IntentType.CANCEL}:
                self._pending_spoken_interpretation = None
                self._pending_voice_command_text = None
                self._input_transcript = ""
                self._suppress_model_output = True
                self._state.last_response = "Theek hai, dobara bolo."
                self._state.status = AssistantStatus.IDLE
                logger.info(
                    "Spoken clarification denied",
                    extra={"event": "spoken_clarification_denied"},
                )
                self._notify_state()
                return
            self._suppress_model_output = True
            self._state.last_response = (
                self._pending_spoken_interpretation.confirmation_prompt or "Confirm karo."
            )
            self._state.status = AssistantStatus.IDLE
            self._notify_state()
            return
        interpretation = self._spoken_normalizer.interpret(transcript, intent_router=intent_router)
        self._remember_browser_intent_candidate(
            interpretation,
            raw_text=transcript,
            source="voice_partial" if not final_chunk else "voice_final",
        )
        follow_up_candidate = self._command_controller.resolve_browser_follow_up_intent(
            transcript,
            parsed_intent=interpretation.intent,
            source="voice",
        )
        self._browser_command_priority_active = interpretation.browser_like or (
            follow_up_candidate is not None
        )
        if follow_up_candidate is not None:
            self._pending_voice_command_text = transcript
            self._suppress_model_output = True
            logger.info(
                "Voice browser follow-up intercepted before chat fallback",
                extra={
                    "event": "voice_browser_followup_detected",
                    "transcript": transcript,
                    "intent_type": follow_up_candidate.intent_type.value,
                    "query": follow_up_candidate.metadata.get("query", ""),
                },
            )
            return
        if (
            interpretation.intent.intent_type
            in {
                IntentType.SEARCH_PAGE,
                IntentType.SEARCH_YOUTUBE,
                IntentType.PLAY_YOUTUBE_PLAYLIST,
            }
            and not final_chunk
        ):
            return
        if interpretation.intent.intent_type is IntentType.GENERAL_COMMAND:
            return
        if interpretation.needs_confirmation and interpretation.browser_like and not final_chunk:
            return
        if interpretation.needs_confirmation:
            self._pending_spoken_interpretation = interpretation
            self._pending_voice_command_text = None
            self._input_transcript = ""
            self._suppress_model_output = True
            self._state.last_response = interpretation.confirmation_prompt or "Confirm karo."
            self._state.status = AssistantStatus.IDLE
            logger.info(
                "Spoken clarification requested",
                extra={
                    "event": "spoken_clarification_requested",
                    "raw_transcript": transcript,
                    "normalized_command": interpretation.normalized_text,
                    "intent_type": interpretation.intent.intent_type.value,
                },
            )
            self._notify_state()
            return
        self._pending_voice_command_text = interpretation.normalized_text
        self._suppress_model_output = True
        logger.info(
            "Voice command transcript detected",
            extra={
                "event": "voice_command_detected",
                "transcript": transcript,
                "normalized_command": interpretation.normalized_text,
                "intent_type": interpretation.intent.intent_type.value,
            },
        )

    def _try_recover_browser_command_from_model_output(self) -> bool:
        if not self._browser_command_priority_active or self._command_controller is None:
            return False
        if self._pending_voice_command_text or self._pending_spoken_interpretation is not None:
            return False
        interpretation = self._spoken_normalizer.recover_browser_command(
            raw_text=self._input_transcript,
            model_text=self._output_transcript,
            intent_router=self._command_controller.intent_router,
        )
        if interpretation is None:
            return False

        self._remember_browser_intent_candidate(
            interpretation,
            raw_text=interpretation.raw_text,
            source="voice_model_recovery",
        )
        self._suppress_model_output = True
        self._output_transcript = ""
        self._state.status = AssistantStatus.IDLE
        if interpretation.needs_confirmation:
            self._pending_spoken_interpretation = interpretation
            self._pending_voice_command_text = None
            self._input_transcript = ""
            self._state.last_response = interpretation.confirmation_prompt or "Confirm karo."
            logger.info(
                "Browser command recovered from model output with confirmation",
                extra={
                    "event": "browser_command_recovered_with_confirmation",
                    "raw_transcript": interpretation.raw_text,
                    "normalized_command": interpretation.normalized_text,
                    "intent_type": interpretation.intent.intent_type.value,
                },
            )
            return True

        self._pending_voice_command_text = interpretation.normalized_text
        logger.info(
            "Browser command recovered from model output",
            extra={
                "event": "browser_command_recovered_from_model_output",
                "raw_transcript": interpretation.raw_text,
                "normalized_command": interpretation.normalized_text,
                "intent_type": interpretation.intent.intent_type.value,
            },
        )
        return True

    async def _execute_voice_command(self) -> None:
        transcript = (self._pending_voice_command_text or "").strip()
        self._pending_voice_command_text = None
        if not transcript or self._command_controller is None:
            await self._finish_model_turn()
            return
        if self._audio_gateway is not None:
            await self._audio_gateway.interrupt_output()
        self._state.status = AssistantStatus.THINKING
        self._notify_state()
        result = self._command_controller.handle_text_command(transcript, source="voice")
        if self._audio_gateway is not None:
            if self._state.muted:
                await self._audio_gateway.mute()
            else:
                await self._audio_gateway.unmute()
        logger.info(
            "Voice command executed through controller",
            extra={
                "event": "voice_command_executed",
                "transcript": transcript,
                "confirmation_required": result.confirmation_required,
                "response_text": result.response_text,
            },
        )
        self._input_transcript = ""
        self._output_transcript = ""
        self._generation_complete_received = False
        self._pending_spoken_interpretation = None
        self._browser_command_priority_active = False
        self._command_feedback_in_progress = False
        self._state.status = AssistantStatus.IDLE
        self._notify_state()

    def _remember_browser_intent_candidate(
        self,
        interpretation: SpokenInterpretation,
        *,
        raw_text: str,
        source: str,
    ) -> None:
        if self._command_controller is None:
            return
        if interpretation.intent.intent_type not in {
            IntentType.SEARCH_YOUTUBE,
            IntentType.PLAY_YOUTUBE_PLAYLIST,
        }:
            return
        self._command_controller.remember_browser_intent(
            interpretation.intent,
            raw_text=raw_text,
            source=source,
        )
