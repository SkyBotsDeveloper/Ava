from __future__ import annotations

from dataclasses import dataclass

from ava.app.state import AssistantState, AssistantStatus
from ava.automation.executor import ActionExecutor
from ava.config.settings import Settings
from ava.intents.models import IntentType, ParsedIntent
from ava.intents.router import IntentRouter
from ava.memory.journal import ActionJournalStore
from ava.safety.policy import ConfirmationStatus, ResultStatus, SafetyDecision, SafetyPolicy


@dataclass(slots=True)
class CommandResult:
    response_text: str
    confirmation_required: bool = False


@dataclass(slots=True)
class PendingAction:
    command_text: str
    intent: ParsedIntent


class AvaController:
    def __init__(
        self,
        settings: Settings,
        state: AssistantState,
        intent_router: IntentRouter,
        safety_policy: SafetyPolicy,
        journal: ActionJournalStore,
        executor: ActionExecutor,
    ) -> None:
        self.settings = settings
        self.state = state
        self.intent_router = intent_router
        self.safety_policy = safety_policy
        self.journal = journal
        self.executor = executor
        self._pending_action: PendingAction | None = None

    def handle_text_command(self, raw_text: str) -> CommandResult:
        cleaned = raw_text.strip()
        if not cleaned:
            self.state.last_response = "Command khaali hai."
            return CommandResult(self.state.last_response)

        self.state.last_command = cleaned
        intent = self.intent_router.parse(cleaned)

        if intent.intent_type is IntentType.CONFIRM:
            return self._handle_confirmation(True)
        if intent.intent_type is IntentType.DENY:
            return self._handle_confirmation(False)

        if intent.intent_type is IntentType.CANCEL:
            self._pending_action = None
            self.state.status = AssistantStatus.IDLE
            self.state.last_response = "Theek hai, cancel kar diya."
            self._record_journal(
                command_text=cleaned,
                action_name="cancel",
                confirmation_status=ConfirmationStatus.NOT_NEEDED,
                result_status=ResultStatus.CANCELED,
                source=intent.source,
                details={"reason": "emergency_stop"},
            )
            return CommandResult(self.state.last_response)

        if intent.intent_type is IntentType.MUTE:
            self.state.muted = True
            self.state.last_response = "Mute on."
            self._record_journal(
                command_text=cleaned,
                action_name="mute",
                confirmation_status=ConfirmationStatus.NOT_NEEDED,
                result_status=ResultStatus.SUCCESS,
                source=intent.source,
            )
            return CommandResult(self.state.last_response)

        if intent.intent_type is IntentType.UNMUTE:
            self.state.muted = False
            self.state.last_response = "Mute off."
            self._record_journal(
                command_text=cleaned,
                action_name="unmute",
                confirmation_status=ConfirmationStatus.NOT_NEEDED,
                result_status=ResultStatus.SUCCESS,
                source=intent.source,
            )
            return CommandResult(self.state.last_response)

        if intent.intent_type is IntentType.GENERAL_COMMAND:
            decision = self.safety_policy.evaluate(cleaned)
            if decision is SafetyDecision.CONFIRM:
                self.state.last_response = "Is action ke liye confirmation chahiye."
                self._record_journal(
                    command_text=cleaned,
                    action_name="command_received",
                    confirmation_status=ConfirmationStatus.REQUESTED,
                    result_status=ResultStatus.PLANNED,
                    source=intent.source,
                    details={"intent_type": intent.intent_type.value},
                )
                return CommandResult(self.state.last_response, confirmation_required=True)
            self.state.last_response = "Command note kar liya."
            self._record_journal(
                command_text=cleaned,
                action_name="command_received",
                confirmation_status=ConfirmationStatus.NOT_NEEDED,
                result_status=ResultStatus.SUCCESS,
                source=intent.source,
                details={"intent_type": intent.intent_type.value},
            )
            return CommandResult(self.state.last_response)

        if intent.intent_type in {IntentType.MOVE_PATH, IntentType.RENAME_PATH}:
            self._pending_action = PendingAction(command_text=cleaned, intent=intent)
            preview = self.executor.preview(intent)
            self.state.last_response = f"Confirm karo, phir {preview.detail.lower()}"
            self._record_journal(
                command_text=cleaned,
                action_name=preview.action_name,
                confirmation_status=ConfirmationStatus.REQUESTED,
                result_status=ResultStatus.PLANNED,
                source=intent.source,
                details={"intent_type": intent.intent_type.value},
            )
            return CommandResult(self.state.last_response, confirmation_required=True)

        decision = self.safety_policy.evaluate(cleaned)
        if decision is SafetyDecision.SUGGEST_ONLY:
            self.state.last_response = (
                "Ye sensitive action hai. Main bas guide karungi, khud execute nahi."
            )
            self._record_journal(
                command_text=cleaned,
                action_name="sensitive_action_blocked",
                confirmation_status=ConfirmationStatus.NOT_NEEDED,
                result_status=ResultStatus.FAILURE,
                source=intent.source,
                details={"intent_type": intent.intent_type.value},
            )
            return CommandResult(self.state.last_response)

        if decision is SafetyDecision.CONFIRM:
            self._pending_action = PendingAction(command_text=cleaned, intent=intent)
            preview = self.executor.preview(intent)
            self.state.last_response = f"Confirm karo, phir {preview.detail.lower()}"
            self._record_journal(
                command_text=cleaned,
                action_name=preview.action_name,
                confirmation_status=ConfirmationStatus.REQUESTED,
                result_status=ResultStatus.PLANNED,
                source=intent.source,
                details={"intent_type": intent.intent_type.value},
            )
            return CommandResult(self.state.last_response, confirmation_required=True)

        return self._execute_intent(cleaned, intent, ConfirmationStatus.NOT_NEEDED)

    def _handle_confirmation(self, approved: bool) -> CommandResult:
        if self._pending_action is None:
            self.state.last_response = "Abhi koi pending confirmation nahi hai."
            return CommandResult(self.state.last_response)

        pending = self._pending_action
        self._pending_action = None
        if not approved:
            self.state.last_response = "Theek hai, main is action ko nahi kar rahi."
            self._record_journal(
                command_text=pending.command_text,
                action_name="confirmation_denied",
                confirmation_status=ConfirmationStatus.DENIED,
                result_status=ResultStatus.CANCELED,
                source=pending.intent.source,
                details={"intent_type": pending.intent.intent_type.value},
            )
            return CommandResult(self.state.last_response)

        return self._execute_intent(
            pending.command_text,
            pending.intent,
            ConfirmationStatus.CONFIRMED,
        )

    def _execute_intent(
        self,
        command_text: str,
        intent: ParsedIntent,
        confirmation_status: ConfirmationStatus,
    ) -> CommandResult:
        self.state.status = AssistantStatus.THINKING
        try:
            result = self.executor.execute(intent)
        except Exception as exc:
            self.state.status = AssistantStatus.IDLE
            self.state.last_response = f"Execution fail ho gaya: {exc}"
            self._record_journal(
                command_text=command_text,
                action_name=intent.intent_type.value,
                confirmation_status=confirmation_status,
                result_status=ResultStatus.FAILURE,
                source=intent.source,
                details={"error": str(exc), "intent_type": intent.intent_type.value},
            )
            return CommandResult(self.state.last_response)

        self.state.status = AssistantStatus.IDLE
        self.state.last_response = result.detail
        self._record_journal(
            command_text=command_text,
            action_name=result.action_name,
            confirmation_status=confirmation_status,
            result_status=ResultStatus.SUCCESS if result.success else ResultStatus.FAILURE,
            source=intent.source,
            details=(result.data or {}) | {"intent_type": intent.intent_type.value},
        )
        return CommandResult(self.state.last_response)

    def _record_journal(
        self,
        *,
        command_text: str,
        action_name: str,
        confirmation_status: ConfirmationStatus,
        result_status: ResultStatus,
        source: str,
        details: dict[str, str | bool] | None = None,
    ) -> None:
        self.journal.record_action(
            command_text=command_text,
            action_name=action_name,
            confirmation_status=confirmation_status,
            result_status=result_status,
            source=source,
            details=details,
        )
