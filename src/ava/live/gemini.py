from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from ava.live.interfaces import (
    AudioChunkEvent,
    LiveSessionClient,
    LiveSessionConfig,
    TranscriptEvent,
    TurnBoundaryEvent,
    VoiceActivityEvent,
)

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - optional dependency guard
    genai = None
    types = None


logger = logging.getLogger(__name__)


class GeminiLiveSessionClient(LiveSessionClient):
    def __init__(self, *, api_key: str | None, api_version: str = "v1beta") -> None:
        self._api_key = api_key
        self._api_version = api_version
        self._client: Any | None = None
        self._session_manager: Any | None = None
        self._session: Any | None = None

    async def connect(self, config: LiveSessionConfig) -> None:
        if self._session is not None:
            return
        if not self._api_key:
            raise RuntimeError("AVA_GEMINI_API_KEY is required for Gemini Live.")
        if genai is None or types is None:
            raise RuntimeError("google-genai is not installed. Install the voice extras first.")

        self._client = genai.Client(
            api_key=self._api_key,
            http_options={"api_version": self._api_version},
        )
        live_config = types.LiveConnectConfig(
            response_modalities=[modality.value for modality in config.response_modalities],
            system_instruction=config.system_instruction,
            speech_config=types.SpeechConfig(
                language_code=config.locale,
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=config.voice_name)
                ),
            ),
            thinking_config=types.ThinkingConfig(thinking_budget=config.thinking_budget),
            input_audio_transcription=types.AudioTranscriptionConfig(language_codes=[config.locale])
            if config.enable_input_transcription
            else None,
            output_audio_transcription=types.AudioTranscriptionConfig(
                language_codes=[config.locale]
            )
            if config.enable_output_transcription
            else None,
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=not config.enable_server_vad,
                    prefix_padding_ms=config.vad_prefix_padding_ms,
                    silence_duration_ms=config.vad_silence_ms,
                )
            ),
        )
        self._session_manager = self._client.aio.live.connect(
            model=config.model_name,
            config=live_config,
        )
        self._session = await self._session_manager.__aenter__()
        logger.info("Gemini Live session connected", extra={"model": config.model_name})

    async def disconnect(self) -> None:
        if self._session_manager is None:
            return
        await self._session_manager.__aexit__(None, None, None)
        self._session_manager = None
        self._session = None
        logger.info("Gemini Live session disconnected")

    async def send_text(self, text: str, *, end_of_turn: bool = True) -> None:
        session = self._require_session()
        await session.send(input=text, end_of_turn=end_of_turn)

    async def send_audio_chunk(self, pcm_bytes: bytes, *, mime_type: str) -> None:
        if not pcm_bytes:
            return
        session = self._require_session()
        await session.send_realtime_input(audio=types.Blob(data=pcm_bytes, mime_type=mime_type))

    async def send_activity_start(self) -> None:
        session = self._require_session()
        await session.send_realtime_input(activity_start=types.ActivityStart())

    async def send_activity_end(self) -> None:
        session = self._require_session()
        await session.send_realtime_input(activity_end=types.ActivityEnd())

    async def receive(
        self,
    ) -> AsyncIterator[TranscriptEvent | AudioChunkEvent | TurnBoundaryEvent | VoiceActivityEvent]:
        session = self._require_session()
        async for message in session.receive():
            for event in self._normalize_server_message(message):
                yield event

    def _require_session(self) -> Any:
        if self._session is None:
            raise RuntimeError("Gemini Live session is not connected.")
        return self._session

    def _normalize_server_message(
        self, message: Any
    ) -> list[TranscriptEvent | AudioChunkEvent | TurnBoundaryEvent | VoiceActivityEvent]:
        events: list[
            TranscriptEvent | AudioChunkEvent | TurnBoundaryEvent | VoiceActivityEvent
        ] = []
        if getattr(message, "voice_activity", None) is not None:
            activity = message.voice_activity.voice_activity_type
            events.append(VoiceActivityEvent(phase=self._enum_value(activity)))
        if getattr(message, "voice_activity_detection_signal", None) is not None:
            signal = message.voice_activity_detection_signal.vad_signal_type
            events.append(VoiceActivityEvent(phase=self._enum_value(signal)))

        server_content = getattr(message, "server_content", None)
        if server_content is None:
            return events

        if getattr(server_content, "input_transcription", None) is not None:
            transcription = server_content.input_transcription
            if transcription.text:
                events.append(
                    TranscriptEvent(
                        text=transcription.text,
                        is_input=True,
                        is_final=bool(transcription.finished),
                    )
                )

        if getattr(server_content, "output_transcription", None) is not None:
            transcription = server_content.output_transcription
            if transcription.text:
                events.append(
                    TranscriptEvent(
                        text=transcription.text,
                        is_input=False,
                        is_final=bool(transcription.finished),
                    )
                )

        model_turn = getattr(server_content, "model_turn", None)
        if model_turn is not None:
            for part in model_turn.parts or []:
                if getattr(part, "text", None):
                    events.append(TranscriptEvent(text=part.text, is_input=False, is_final=False))
                inline_data = getattr(part, "inline_data", None)
                if inline_data is not None and inline_data.data:
                    events.append(
                        AudioChunkEvent(
                            data=bytes(inline_data.data),
                            mime_type=inline_data.mime_type or "audio/pcm;rate=24000",
                        )
                    )

        if getattr(server_content, "turn_complete", False):
            events.append(
                TurnBoundaryEvent(
                    phase="turn_complete",
                    reason=self._enum_value(getattr(server_content, "turn_complete_reason", None)),
                )
            )
        if getattr(server_content, "generation_complete", False):
            events.append(TurnBoundaryEvent(phase="generation_complete"))
        if getattr(server_content, "interrupted", False):
            events.append(TurnBoundaryEvent(phase="interrupted"))
        if getattr(server_content, "waiting_for_input", False):
            events.append(TurnBoundaryEvent(phase="waiting_for_input"))
        return events

    @staticmethod
    def _enum_value(value: Any) -> str:
        if value is None:
            return ""
        return str(getattr(value, "value", value)).lower()
