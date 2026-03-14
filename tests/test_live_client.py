from types import SimpleNamespace

from ava.live.gemini import GeminiLiveSessionClient
from ava.live.interfaces import (
    AudioChunkEvent,
    TranscriptEvent,
    TurnBoundaryEvent,
    VoiceActivityEvent,
)


def test_gemini_client_normalizes_server_messages() -> None:
    client = GeminiLiveSessionClient(api_key="test-key")
    message = SimpleNamespace(
        voice_activity=SimpleNamespace(voice_activity_type=SimpleNamespace(value="START")),
        voice_activity_detection_signal=SimpleNamespace(
            vad_signal_type=SimpleNamespace(value="END")
        ),
        server_content=SimpleNamespace(
            input_transcription=SimpleNamespace(text="Ava sun rahi ho?", finished=True),
            output_transcription=SimpleNamespace(text="Haan, bolo.", finished=True),
            model_turn=SimpleNamespace(
                parts=[
                    SimpleNamespace(text="Haan, bolo.", inline_data=None),
                    SimpleNamespace(
                        text=None,
                        inline_data=SimpleNamespace(
                            data=b"\x01\x02",
                            mime_type="audio/pcm;rate=24000",
                        ),
                    ),
                ]
            ),
            turn_complete=True,
            turn_complete_reason=SimpleNamespace(value="STOP"),
            generation_complete=True,
            interrupted=False,
            waiting_for_input=False,
        ),
    )

    events = client._normalize_server_message(message)

    assert any(isinstance(event, VoiceActivityEvent) and event.phase == "start" for event in events)
    assert any(isinstance(event, VoiceActivityEvent) and event.phase == "end" for event in events)
    assert any(
        isinstance(event, TranscriptEvent)
        and event.is_input is True
        and event.text == "Ava sun rahi ho?"
        for event in events
    )
    assert any(
        isinstance(event, TranscriptEvent)
        and event.is_input is False
        and event.text == "Haan, bolo."
        for event in events
    )
    assert any(isinstance(event, AudioChunkEvent) and event.data == b"\x01\x02" for event in events)
    assert any(
        isinstance(event, TurnBoundaryEvent)
        and event.phase == "turn_complete"
        and event.reason == "stop"
        for event in events
    )
