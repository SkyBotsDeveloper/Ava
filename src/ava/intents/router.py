from __future__ import annotations

from ava.intents.models import IntentType, ParsedIntent


class IntentRouter:
    CANCEL_TOKENS = ("stop ava", "cancel", "bas", "ruk ja")
    MUTE_TOKENS = ("mute", "chup", "be quiet")
    UNMUTE_TOKENS = ("unmute", "speak", "bol")
    BROWSER_TOKENS = ("chrome", "edge", "browser", "youtube", "insta", "instagram", "website")

    def parse(self, raw_text: str, source: str = "text") -> ParsedIntent:
        normalized = " ".join(raw_text.lower().split())

        if any(token in normalized for token in self.CANCEL_TOKENS):
            return ParsedIntent(
                intent_type=IntentType.CANCEL,
                raw_text=raw_text,
                normalized_text=normalized,
                source=source,
                immediate=True,
            )
        if any(token in normalized for token in self.UNMUTE_TOKENS):
            return ParsedIntent(IntentType.UNMUTE, raw_text, normalized, source=source)
        if any(token in normalized for token in self.MUTE_TOKENS):
            return ParsedIntent(IntentType.MUTE, raw_text, normalized, source=source)
        if any(token in normalized for token in self.BROWSER_TOKENS):
            return ParsedIntent(IntentType.OPEN_BROWSER, raw_text, normalized, source=source)
        return ParsedIntent(IntentType.GENERAL_COMMAND, raw_text, normalized, source=source)
