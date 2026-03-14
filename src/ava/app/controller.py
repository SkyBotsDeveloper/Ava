from __future__ import annotations

from dataclasses import dataclass

from ava.app.state import AssistantState, AssistantStatus
from ava.automation.browser import BrowserController
from ava.config.settings import Settings
from ava.intents.models import IntentType
from ava.intents.router import IntentRouter
from ava.memory.journal import ActionJournalStore
from ava.safety.policy import ConfirmationStatus, ResultStatus, SafetyDecision, SafetyPolicy


@dataclass(slots=True)
class CommandResult:
    response_text: str
    confirmation_required: bool = False


class AvaController:
    def __init__(
        self,
        settings: Settings,
        state: AssistantState,
        intent_router: IntentRouter,
        safety_policy: SafetyPolicy,
        journal: ActionJournalStore,
        browser_controller: BrowserController,
    ) -> None:
        self.settings = settings
        self.state = state
        self.intent_router = intent_router
        self.safety_policy = safety_policy
        self.journal = journal
        self.browser_controller = browser_controller

    def handle_text_command(self, raw_text: str) -> CommandResult:
        cleaned = raw_text.strip()
        if not cleaned:
            return CommandResult("Command khaali hai.")

        self.state.last_command = cleaned
        intent = self.intent_router.parse(cleaned)

        if intent.intent_type is IntentType.CANCEL:
            self.state.status = AssistantStatus.IDLE
            self.state.last_response = "Theek hai, cancel kar diya."
            self.journal.record_action(
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
            self.journal.record_action(
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
            self.journal.record_action(
                command_text=cleaned,
                action_name="unmute",
                confirmation_status=ConfirmationStatus.NOT_NEEDED,
                result_status=ResultStatus.SUCCESS,
                source=intent.source,
            )
            return CommandResult(self.state.last_response)

        if intent.intent_type is IntentType.OPEN_BROWSER:
            plan = self.browser_controller.resolve_browser_plan()
            self.state.last_response = plan.describe()
            self.journal.record_action(
                command_text=cleaned,
                action_name="browser_plan",
                confirmation_status=ConfirmationStatus.NOT_NEEDED,
                result_status=ResultStatus.PLANNED,
                source=intent.source,
                details=plan.as_dict(),
            )
            return CommandResult(self.state.last_response)

        decision = self.safety_policy.evaluate(cleaned)
        confirmation_required = decision is SafetyDecision.CONFIRM
        result_status = ResultStatus.PLANNED if confirmation_required else ResultStatus.SUCCESS
        confirmation_status = (
            ConfirmationStatus.REQUESTED if confirmation_required else ConfirmationStatus.NOT_NEEDED
        )

        self.state.status = AssistantStatus.THINKING
        self.state.last_response = (
            "Is action ke liye confirmation chahiye."
            if confirmation_required
            else "Command note kar liya. Detailed execution next phase mein wire hoga."
        )
        self.journal.record_action(
            command_text=cleaned,
            action_name="command_received",
            confirmation_status=confirmation_status,
            result_status=result_status,
            source=intent.source,
            details={"intent_type": intent.intent_type.value},
        )
        self.state.status = AssistantStatus.IDLE
        return CommandResult(self.state.last_response, confirmation_required=confirmation_required)
