from __future__ import annotations

from dataclasses import dataclass

from ava.automation.browser import BrowserController
from ava.intents.models import IntentType, ParsedIntent


@dataclass(slots=True)
class ExecutionPreview:
    action_name: str
    detail: str


class ActionExecutor:
    def __init__(self, browser_controller: BrowserController) -> None:
        self.browser_controller = browser_controller

    def preview(self, intent: ParsedIntent) -> ExecutionPreview:
        if intent.intent_type is IntentType.OPEN_BROWSER:
            plan = self.browser_controller.resolve_browser_plan()
            return ExecutionPreview("browser_plan", plan.describe())
        return ExecutionPreview("unimplemented", "Execution path scaffolded for a later phase.")
