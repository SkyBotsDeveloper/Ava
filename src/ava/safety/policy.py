from __future__ import annotations

from enum import StrEnum


class SafetyDecision(StrEnum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    SUGGEST_ONLY = "suggest_only"


class ConfirmationStatus(StrEnum):
    NOT_NEEDED = "not_needed"
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    DENIED = "denied"


class ResultStatus(StrEnum):
    PLANNED = "planned"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELED = "canceled"


class SafetyPolicy:
    CONFIRMATION_TERMS = (
        "message",
        "send",
        "delete",
        "remove",
        "install",
        "login",
        "payment",
        "bank",
        "transfer",
        "whatsapp",
    )
    PRIVATE_TERMS = ("bank", "password", "wallet", "otp", "credential")

    def evaluate(self, raw_text: str) -> SafetyDecision:
        normalized = raw_text.lower()
        if any(token in normalized for token in self.PRIVATE_TERMS):
            return SafetyDecision.SUGGEST_ONLY
        if any(token in normalized for token in self.CONFIRMATION_TERMS):
            return SafetyDecision.CONFIRM
        return SafetyDecision.ALLOW
