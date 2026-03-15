from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from ava.app.controller import CommandResult
from ava.app.state import AssistantState, AssistantStatus, BrowserTaskContext
from ava.config.settings import Settings
from ava.intents.models import IntentType, ParsedIntent
from ava.intents.router import IntentRouter
from ava.live.interfaces import (
    AudioChunkEvent,
    LiveSessionConfig,
    TranscriptEvent,
    TurnBoundaryEvent,
)
from ava.memory.bootstrap import initialize_database
from ava.memory.database import build_engine, build_session_factory
from ava.memory.journal import ActionJournalStore
from ava.voice.runtime import VoiceRuntime
from ava.voice.spoken_normalizer import SpokenInterpretation


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


class FakeIntentRouter:
    def parse(self, raw_text: str, source: str = "text") -> ParsedIntent:
        normalized = raw_text.lower().strip()
        if normalized in {"yes", "haan"}:
            intent_type = IntentType.CONFIRM
        else:
            intent_type = (
                IntentType.OPEN_BROWSER
                if "website kholo" in normalized or "python.org kholo" in normalized
                else IntentType.GENERAL_COMMAND
            )
        return ParsedIntent(
            intent_type=intent_type,
            raw_text=raw_text,
            normalized_text=normalized,
            source=source,
        )


class FakeVoiceCommandController:
    def __init__(self, state: AssistantState) -> None:
        self.state = state
        self.intent_router = IntentRouter()
        self.calls: list[tuple[str, str]] = []
        self.remembered_queries: list[tuple[str, str]] = []

    def handle_text_command(self, raw_text: str, *, source: str = "text") -> CommandResult:
        self.calls.append((raw_text, source))
        self.state.last_response = "Browser khol diya."
        return CommandResult(response_text=self.state.last_response)

    def remember_browser_intent(
        self,
        intent: ParsedIntent,
        *,
        raw_text: str = "",
        source: str = "voice",
    ) -> None:
        self.remembered_queries.append((intent.metadata.get("query", ""), source))

    def resolve_browser_follow_up_intent(
        self,
        raw_text: str,
        *,
        parsed_intent: ParsedIntent | None = None,
        source: str = "text",
    ) -> ParsedIntent | None:
        lowered = raw_text.lower()
        if (
            "dobara search" not in lowered
            and "search nahi hui" not in lowered
            and "sirf youtube khola hai" not in lowered
            and "playlist bhi search karo" not in lowered
            and "jo maine bola tha woh search karo" not in lowered
            and lowered.strip(" .!?") not in {"search", "search karo"}
        ):
            return None
        return ParsedIntent(
            intent_type=IntentType.SEARCH_YOUTUBE,
            raw_text=raw_text,
            normalized_text=raw_text.lower(),
            source=source,
            metadata={"query": "lofi hip hop playlist"},
        )


class FakeSpokenNormalizer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def interpret(self, raw_text: str, *, intent_router) -> SpokenInterpretation:
        self.calls.append(raw_text)
        normalized = "python.org kholo"
        intent = intent_router.parse(normalized, source="voice")
        return SpokenInterpretation(
            raw_text=raw_text,
            normalized_text=normalized,
            intent=intent,
            needs_confirmation=True,
            confirmation_prompt="Aap `python.org` bol rahe the na?",
        )

    def recover_browser_command(self, *, raw_text: str, model_text: str, intent_router):
        return None


@dataclass(slots=True)
class FakeAudioGateway:
    played_chunks: list[tuple[bytes, int]]
    started: bool = False
    flushed: bool = False

    async def start_input(self) -> None:
        self.started = True

    async def stop_input(self) -> None:
        return None

    async def input_chunks(self):
        if False:
            yield None

    async def play_output_chunk(self, data: bytes, *, sample_rate_hz: int) -> None:
        self.played_chunks.append((data, sample_rate_hz))

    async def flush_output(self) -> None:
        self.flushed = True

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
    assert audio_gateway.flushed is False
    rows = journal.list_recent()
    assert rows[0].action_name == "live_text_turn"
    assert rows[0].result_status == "planned"


def test_voice_runtime_manual_capture_starts_without_wake_model(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient()
    audio_gateway = FakeAudioGateway(played_chunks=[])
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()

    asyncio.run(scenario())

    assert runtime.availability.manual_voice_ready is True
    assert runtime.availability.wake_ready is False
    assert audio_gateway.started is True
    assert state.status is AssistantStatus.THINKING
    rows = journal.list_recent()
    assert rows[0].action_name == "manual_voice_trigger"


def test_voice_runtime_flushes_audio_on_turn_complete(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient()
    audio_gateway = FakeAudioGateway(played_chunks=[])
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
    )

    async def scenario() -> None:
        await runtime._apply_audio(
            AudioChunkEvent(data=b"\x00\x00", mime_type="audio/pcm;rate=24000")
        )
        assert state.status is AssistantStatus.SPEAKING
        assert audio_gateway.flushed is False
        await runtime._apply_turn_boundary(
            TurnBoundaryEvent(phase="generation_complete", reason="generation_done")
        )
        assert state.status is AssistantStatus.SPEAKING
        assert audio_gateway.flushed is False
        await runtime._apply_turn_boundary(TurnBoundaryEvent(phase="turn_complete", reason="stop"))

    asyncio.run(scenario())

    assert audio_gateway.flushed is True
    assert state.status is AssistantStatus.IDLE


def test_voice_runtime_routes_spoken_command_into_controller(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(text="website kholo", is_input=True, is_final=True),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == [("website kholo", "voice")]
    assert live_client.sent_text == []
    assert state.last_response == "Browser khol diya."
    assert state.status is AssistantStatus.IDLE


def test_voice_runtime_detects_partial_spoken_command_before_final_boundary(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(text="website kholo", is_input=True, is_final=False),
            TranscriptEvent(text="Ignore this late model output", is_input=False, is_final=False),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == [("website kholo", "voice")]
    assert state.last_response == "Browser khol diya."
    assert state.status is AssistantStatus.IDLE


def test_voice_runtime_waits_past_partial_no_for_fragmented_notepad_command(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(text="No", is_input=True, is_final=False),
            TranscriptEvent(text="No te pad Colo.", is_input=True, is_final=False),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == [("notepad kholo", "voice")]
    assert state.last_response == "Browser khol diya."
    assert state.status is AssistantStatus.IDLE


def test_voice_runtime_requests_spoken_clarification_before_execution(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(text="Pyt hon.org", is_input=True, is_final=False),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    normalizer = FakeSpokenNormalizer()
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
        spoken_command_normalizer=normalizer,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert "Pyt hon.org" in normalizer.calls
    assert controller.calls == []


def test_voice_runtime_preserves_spoken_clarification_across_manual_recapture(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(text="yes", is_input=True, is_final=True),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )
    runtime._pending_spoken_interpretation = SpokenInterpretation(
        raw_text="Pyt hon.org",
        normalized_text="python.org kholo",
        intent=controller.intent_router.parse("python.org kholo", source="voice"),
        needs_confirmation=True,
        confirmation_prompt="Aap `python.org` bol rahe the na?",
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        assert state.last_response == "Aap `python.org` bol rahe the na?"
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == [("python.org kholo", "voice")]


def test_voice_runtime_recovers_browser_command_from_model_output(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(text=". com", is_input=True, is_final=False),
            TranscriptEvent(text="Sure, opening GitHub for you.", is_input=False, is_final=False),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
            TranscriptEvent(text="yes", is_input=True, is_final=True),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == [("github.com kholo", "voice")]


def test_voice_runtime_waits_for_turn_end_before_query_confirmation(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(
                text="YouTu be p a r lop fy hi p hop pla ylist",
                is_input=True,
                is_final=False,
            ),
            TranscriptEvent(text="se arch", is_input=True, is_final=False),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == []
    assert controller.remembered_queries[-1][0] == "lofi hip hop playlist"
    assert state.last_response == "Ye search query `lofi hip hop playlist` sahi hai na?"


def test_voice_runtime_keeps_compound_youtube_phrase_on_search_path(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(
                text="YouTube kholo aur lofi hip hop playlist search karo",
                is_input=True,
                is_final=False,
            ),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == [("youtube par lofi hip hop playlist search karo", "voice")]
    assert state.last_response == "Browser khol diya."


def test_voice_runtime_repairs_observed_youtube_query_collapse(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(
                text="You Tube hi p hop play list sear ch.",
                is_input=True,
                is_final=False,
            ),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == []
    assert controller.remembered_queries[-1][0] == "lofi hip hop playlist"
    assert state.last_response == "Ye search query `lofi hip hop playlist` sahi hai na?"


def test_voice_runtime_intercepts_browser_followup_before_chat_fallback(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState(
        active_browser_task=BrowserTaskContext(
            task_kind="youtube_search",
            query="lofi hip hop playlist",
            page_url="https://www.youtube.com/",
        )
    )
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(text="dobara search karo", is_input=True, is_final=True),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == [("dobara search karo", "voice")]


def test_voice_runtime_intercepts_collapsed_search_followup(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState(
        active_browser_task=BrowserTaskContext(
            task_kind="youtube_search",
            query="lofi hip hop playlist",
            page_url="https://www.youtube.com/",
        )
    )
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(text="search", is_input=True, is_final=True),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == [("search", "voice")]


def test_voice_runtime_intercepts_malformed_browser_retry_phrase(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState(
        active_browser_task=BrowserTaskContext(
            task_kind="youtube_search",
            query="lofi hip hop playlist",
            page_url="https://www.youtube.com/",
        )
    )
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(
                text="YouTube khul gaya but woh hip hop playlist search nahi hui karo",
                is_input=True,
                is_final=True,
            ),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == [
        ("YouTube khul gaya but woh hip hop playlist search nahi hui karo", "voice")
    ]


def test_voice_runtime_intercepts_complaint_retry_with_stored_query_context(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState(
        active_browser_task=BrowserTaskContext(
            task_kind="youtube_search",
            intended_query="lofi hip hop playlist",
            last_action_name="open_youtube",
            page_url="https://www.youtube.com/",
        )
    )
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(text="sirf YouTube khola hai", is_input=True, is_final=True),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == [("sirf YouTube khola hai", "voice")]


def test_voice_runtime_suppresses_local_command_chat_fallback(tmp_path) -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    state = AssistantState()
    journal = _build_journal(tmp_path)
    live_client = FakeLiveClient(
        receive_events=[
            TranscriptEvent(text="is fo lder me nu file", is_input=True, is_final=False),
            TranscriptEvent(
                text="Sure, file bana di.",
                is_input=False,
                is_final=False,
            ),
            TurnBoundaryEvent(phase="turn_complete", reason="stop"),
        ]
    )
    audio_gateway = FakeAudioGateway(played_chunks=[])
    controller = FakeVoiceCommandController(state)
    runtime = VoiceRuntime(
        settings=settings,
        state=state,
        journal=journal,
        live_client=live_client,
        audio_gateway=audio_gateway,
        command_controller=controller,
    )

    async def scenario() -> None:
        await runtime.begin_manual_capture()
        await runtime.end_manual_capture()
        receive_task = runtime._receive_task
        assert receive_task is not None
        await receive_task

    asyncio.run(scenario())

    assert controller.calls == [("is folder me new file banao", "voice")]
    assert state.last_response == "Browser khol diya."
