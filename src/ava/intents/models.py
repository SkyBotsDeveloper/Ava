from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class IntentType(StrEnum):
    CANCEL = "cancel"
    MUTE = "mute"
    UNMUTE = "unmute"
    OPEN_BROWSER = "open_browser"
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    OPEN_WEBSITE = "open_website"
    CLOSE_TAB = "close_tab"
    CREATE_FOLDER = "create_folder"
    CREATE_FILE = "create_file"
    CONFIRM = "confirm"
    DENY = "deny"
    GENERAL_COMMAND = "general_command"


@dataclass(slots=True)
class ParsedIntent:
    intent_type: IntentType
    raw_text: str
    normalized_text: str
    source: str = "text"
    immediate: bool = False
    metadata: dict[str, str] = field(default_factory=dict)
