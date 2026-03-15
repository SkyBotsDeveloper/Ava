from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AssistantStatus(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


@dataclass(slots=True)
class BrowserTaskContext:
    task_kind: str
    query: str = ""
    url: str = ""
    page_title: str = ""
    page_url: str = ""
    browser_name: str = ""
    turns_remaining: int = 2


@dataclass(slots=True)
class AssistantState:
    status: AssistantStatus = AssistantStatus.IDLE
    muted: bool = False
    observation_enabled: bool = False
    last_command: str = ""
    last_response: str = ""
    active_browser_task: BrowserTaskContext | None = None
