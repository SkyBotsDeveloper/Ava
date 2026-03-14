from __future__ import annotations

import re
from typing import Final

from ava.intents.models import IntentType, ParsedIntent


class IntentRouter:
    CANCEL_TOKENS: Final = ("stop ava", "cancel", "bas", "ruk ja", "stop")
    CONFIRM_TOKENS: Final = ("haan", "yes", "confirm", "kar do", "theek hai")
    DENY_TOKENS: Final = ("nahi", "no", "mat karo", "cancel it")
    MUTE_TOKENS: Final = ("mute", "chup", "be quiet")
    UNMUTE_TOKENS: Final = ("unmute", "speak", "bol")
    WEBSITE_ALIASES: Final[dict[str, str]] = {
        "youtube": "https://www.youtube.com",
        "insta": "https://www.instagram.com",
        "instagram": "https://www.instagram.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "whatsapp": "https://web.whatsapp.com",
    }
    APP_ALIASES: Final[dict[str, str]] = {
        "notepad": "notepad",
        "calculator": "calculator",
        "calc": "calculator",
        "paint": "paint",
        "explorer": "explorer",
        "file explorer": "explorer",
        "cmd": "command prompt",
        "command prompt": "command prompt",
    }

    def parse(self, raw_text: str, source: str = "text") -> ParsedIntent:
        normalized = " ".join(raw_text.lower().split())

        if any(token == normalized or token in normalized for token in self.CANCEL_TOKENS):
            return ParsedIntent(
                intent_type=IntentType.CANCEL,
                raw_text=raw_text,
                normalized_text=normalized,
                source=source,
                immediate=True,
            )
        if normalized in self.CONFIRM_TOKENS:
            return ParsedIntent(IntentType.CONFIRM, raw_text, normalized, source=source)
        if normalized in self.DENY_TOKENS:
            return ParsedIntent(IntentType.DENY, raw_text, normalized, source=source)
        if any(token in normalized for token in self.UNMUTE_TOKENS):
            return ParsedIntent(IntentType.UNMUTE, raw_text, normalized, source=source)
        if any(token in normalized for token in self.MUTE_TOKENS):
            return ParsedIntent(IntentType.MUTE, raw_text, normalized, source=source)

        close_tab = self._parse_close_tab(raw_text, normalized, source)
        if close_tab is not None:
            return close_tab

        create_folder = self._parse_create_folder(raw_text, normalized, source)
        if create_folder is not None:
            return create_folder

        create_file = self._parse_create_file(raw_text, normalized, source)
        if create_file is not None:
            return create_file

        close_app = self._parse_app_intent(raw_text, normalized, source, close=True)
        if close_app is not None:
            return close_app

        open_website = self._parse_website_intent(raw_text, normalized, source)
        if open_website is not None:
            return open_website

        open_app = self._parse_app_intent(raw_text, normalized, source, close=False)
        if open_app is not None:
            return open_app

        if any(token in normalized for token in ("browser", "chrome", "edge")):
            return ParsedIntent(IntentType.OPEN_BROWSER, raw_text, normalized, source=source)
        return ParsedIntent(IntentType.GENERAL_COMMAND, raw_text, normalized, source=source)

    def _parse_close_tab(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "tab" not in normalized:
            return None
        if any(token in normalized for token in ("band", "close", "remove")):
            return ParsedIntent(IntentType.CLOSE_TAB, raw_text, normalized, source=source)
        return None

    def _parse_create_folder(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "folder" not in normalized and "directory" not in normalized:
            return None
        if not any(token in normalized for token in ("create", "banao", "bana do", "new")):
            return None
        name = self._extract_named_target(raw_text, ("folder", "directory"))
        if name is None:
            return None
        return ParsedIntent(
            IntentType.CREATE_FOLDER,
            raw_text,
            normalized,
            source=source,
            metadata={"target_name": name},
        )

    def _parse_create_file(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "file" not in normalized:
            return None
        if not any(token in normalized for token in ("create", "banao", "bana do", "new")):
            return None
        name = self._extract_named_target(raw_text, ("file",))
        if name is None:
            return None
        return ParsedIntent(
            IntentType.CREATE_FILE,
            raw_text,
            normalized,
            source=source,
            metadata={"target_name": name},
        )

    def _parse_app_intent(
        self,
        raw_text: str,
        normalized: str,
        source: str,
        *,
        close: bool,
    ) -> ParsedIntent | None:
        action_tokens = ("band", "close") if close else ("khol", "open", "launch", "start")
        if not any(token in normalized for token in action_tokens):
            return None

        for alias, app_name in self.APP_ALIASES.items():
            if alias in normalized:
                return ParsedIntent(
                    IntentType.CLOSE_APP if close else IntentType.OPEN_APP,
                    raw_text,
                    normalized,
                    source=source,
                    metadata={"app_name": app_name},
                )
        return None

    def _parse_website_intent(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        for alias, url in self.WEBSITE_ALIASES.items():
            if alias in normalized and any(
                token in normalized for token in ("khol", "open", "launch")
            ):
                return ParsedIntent(
                    IntentType.OPEN_WEBSITE,
                    raw_text,
                    normalized,
                    source=source,
                    metadata={"url": url, "label": alias},
                )

        url_match = re.search(
            r"(https?://\S+|file:///\S+|www\.\S+\.\S+)",
            raw_text,
            flags=re.IGNORECASE,
        )
        if url_match and any(token in normalized for token in ("khol", "open", "launch")):
            url = url_match.group(1)
            if url.lower().startswith("www."):
                url = f"https://{url}"
            return ParsedIntent(
                IntentType.OPEN_WEBSITE,
                raw_text,
                normalized,
                source=source,
                metadata={"url": url, "label": url},
            )
        return None

    @staticmethod
    def _extract_named_target(raw_text: str, keywords: tuple[str, ...]) -> str | None:
        text = raw_text.strip()
        quoted = re.search(r"['\"]([^'\"]+)['\"]", text)
        if quoted:
            return quoted.group(1).strip()

        lowered = text.lower()
        for keyword in keywords:
            if keyword not in lowered:
                continue
            index = lowered.find(keyword)
            before = text[:index].strip(" -:")
            after = text[index + len(keyword) :].strip(" -:")

            before = re.sub(r"(?i)\b(create|new|please|ava|banao|bana do)\b", "", before).strip()
            after = re.sub(r"(?i)\b(create|new|please|ava|banao|bana do|ke andar)\b", "", after)
            after = after.strip(" -:")

            candidate = before or after
            candidate = candidate.strip()
            if candidate:
                return candidate
        return None
