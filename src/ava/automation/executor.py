from __future__ import annotations

from dataclasses import dataclass

from ava.automation.browser import BrowserController
from ava.automation.windows import WindowController
from ava.intents.models import IntentType, ParsedIntent


@dataclass(slots=True)
class ExecutionResult:
    action_name: str
    success: bool
    detail: str
    data: dict[str, str | bool] | None = None


@dataclass(slots=True)
class ExecutionPreview:
    action_name: str
    detail: str


class ActionExecutor:
    def __init__(
        self,
        browser_controller: BrowserController,
        window_controller: WindowController,
    ) -> None:
        self.browser_controller = browser_controller
        self.window_controller = window_controller

    def preview(self, intent: ParsedIntent) -> ExecutionPreview:
        if intent.intent_type in {
            IntentType.OPEN_BROWSER,
            IntentType.OPEN_WEBSITE,
            IntentType.CLOSE_TAB,
        }:
            plan = self.browser_controller.resolve_browser_plan()
            return ExecutionPreview("browser_plan", plan.describe())
        if intent.intent_type in {IntentType.OPEN_APP, IntentType.CLOSE_APP}:
            app_name = intent.metadata.get("app_name", "unknown app")
            return ExecutionPreview(
                intent.intent_type.value,
                f"{app_name.title()} par action hoga.",
            )
        if intent.intent_type in {IntentType.CREATE_FOLDER, IntentType.CREATE_FILE}:
            target_name = intent.metadata.get("target_name", "new item")
            return ExecutionPreview(intent.intent_type.value, f"`{target_name}` create hoga.")
        return ExecutionPreview("unimplemented", "Execution path scaffolded for a later phase.")

    def execute(self, intent: ParsedIntent) -> ExecutionResult:
        if intent.intent_type is IntentType.OPEN_BROWSER:
            plan = self.browser_controller.resolve_browser_plan()
            self.browser_controller.open_url("https://www.google.com")
            return ExecutionResult(
                action_name="open_browser",
                success=True,
                detail=plan.describe(),
                data=plan.as_dict(),
            )

        if intent.intent_type is IntentType.OPEN_WEBSITE:
            url = intent.metadata["url"]
            plan = self.browser_controller.open_url(url)
            return ExecutionResult(
                action_name="open_website",
                success=True,
                detail=f"{url} khol diya.",
                data={"url": url, **plan.as_dict()},
            )

        if intent.intent_type is IntentType.CLOSE_TAB:
            plan = self.browser_controller.close_current_tab()
            return ExecutionResult(
                action_name="close_tab",
                success=True,
                detail="Current browser tab band kar diya.",
                data=plan.as_dict(),
            )

        if intent.intent_type is IntentType.OPEN_APP:
            app_name = intent.metadata["app_name"]
            self.window_controller.launch_app(app_name)
            return ExecutionResult(
                action_name="open_app",
                success=True,
                detail=f"{app_name.title()} khol diya.",
                data={"app_name": app_name},
            )

        if intent.intent_type is IntentType.CLOSE_APP:
            app_name = intent.metadata["app_name"]
            terminated = self.window_controller.close_app(app_name)
            success = terminated > 0
            detail = (
                f"{app_name.title()} band kar diya."
                if success
                else f"{app_name.title()} ka running window nahi mila."
            )
            return ExecutionResult(
                action_name="close_app",
                success=success,
                detail=detail,
                data={"app_name": app_name, "terminated": str(terminated)},
            )

        if intent.intent_type is IntentType.CREATE_FOLDER:
            target = self.window_controller.create_folder(intent.metadata["target_name"])
            return ExecutionResult(
                action_name="create_folder",
                success=True,
                detail=f"Folder bana diya: {target.name}",
                data={"path": str(target)},
            )

        if intent.intent_type is IntentType.CREATE_FILE:
            target = self.window_controller.create_file(intent.metadata["target_name"])
            return ExecutionResult(
                action_name="create_file",
                success=True,
                detail=f"File bana di: {target.name}",
                data={"path": str(target)},
            )

        return ExecutionResult(
            action_name="unimplemented",
            success=False,
            detail="Is command ka execution Phase 4 MVP me abhi wired nahi hai.",
        )
