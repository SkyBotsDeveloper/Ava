from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from ava.app.state import AssistantState, AssistantStatus
from ava.config.settings import Settings
from ava.live.interfaces import LiveSessionConfig, TranscriptEvent, TurnBoundaryEvent
from ava.memory.bootstrap import initialize_database
from ava.memory.database import build_engine, build_session_factory
from ava.memory.journal import ActionJournalStore
from ava.voice.runtime import VoiceRuntime


class FakeLiveClient:
    def __init__(self, receive_events: list[object] | None = None) -> None:
        self.receive_events = receive_events or []
        self.connected_with: LiveSessionConfig | None = None
        self.sent_text: list[str] = []
        self.disconnected = False

    async def connect(self, config: LiveSessionConfig) -> None:
        self.connected_with = config

    async def disconnect(self) -> None:
        self.disconnected = True

    async def send_text(self, text: str, *, end_of_turn: bool = True) -> None:
        self.sent_text.append(text)

    async def send_audio_chunk(self, pcm_bytes: bytes, *, mime_type: str) -> None:
        return None

    async def send_activity_start(self) -> None:
        return None

    async def send_activity_end(self) -> None:
        return None

    async def receive(self) -> AsyncIterator[object]:
        for event in self.receive_events:
            yield event


@dataclass(slots=True)
class FakeAudioGateway:
    played_chunks: list[tuple[bytes, int]]

    async def start_input(self) -> None:
        return None

    async def stop_input(self) -> None:
        return None

    async def input_chunks(self):
        if False:
            yield None

    async def play_output_chunk(self, data: bytes, *, sample_rate_hz: int) -> None:
        self.played_chunks.append((data, sample_rate_hz))

    async def mute(self) -> None:
        return None

    async def unmute(self) -> None:
        return None

    async def interrupt_output(self) -> None:
        return None


def _build_journal(tmp_path: Path) -> ActionJournalStore:
    database_path = tmp_path / "ava.db"
    engine = build_engine(database_path)
    initialize_database(engine)
    return ActionJournalStore(build_session_factory(engine))


def test_voice_runtime_reports_missing_live_config(tmp_path) -> None:
    settings = Settings(_env_file=None)
    runtime = VoiceRuntime(
        settings=settings,
        state=AssistantState(),
        journal=_build_journal(tmp_path),
        live_client=FakeLiveClient(),
    )

    availability = runtime.availability

    assert availability.live_text_ready is False
    assert "AVA_GEMINI_API_KEY" in " ".join(availability.blockers)


def test_voice_runtime_submit_text_updates_state_and_journal(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(text="Kal 4 baje remind kar dungi.", is_input=False, is_final=True),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
    )

    async def scenario() -> None:
        await runtime.submit_text("Kal 4 baje yaad dila dena")
        await asyncio.sleep(0)
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert live_client.connected_with is not None
    assert live_client.connected_with.voice_name == "Kore"
    assert live_client.sent_text == ["Kal 4 baje yaad dila dena"]
    assert state.last_response == "Kal 4 baje remind kar dungi."
    assert state.status is AssistantStatus.IDLE
    rows = journal.list_recent()
    assert rows[0].action_name == "live_text_turn"
    assert rows[0].result_status == "planned"
