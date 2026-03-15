from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ava.automation.browser import BrowserController
from ava.automation.windows import WindowController
from ava.intents.models import IntentType, ParsedIntent


@dataclass(slots=True)
class ExecutionResult:
    action_name: str
    success: bool
    detail: str
    data: dict[str, Any] | None = None


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
        browser_intents = {
            IntentType.OPEN_BROWSER,
            IntentType.OPEN_WEBSITE,
            IntentType.FOCUS_ADDRESS_BAR,
            IntentType.OPEN_NEW_TAB,
            IntentType.SWITCH_TAB,
            IntentType.SEARCH_PAGE,
            IntentType.GET_CURRENT_PAGE,
            IntentType.OPEN_YOUTUBE,
            IntentType.SEARCH_YOUTUBE,
            IntentType.PLAY_YOUTUBE_PLAYLIST,
            IntentType.OPEN_INSTAGRAM_LOGIN,
            IntentType.OPEN_WHATSAPP_WEB,
            IntentType.CLOSE_TAB,
        }
        if intent.intent_type in {
            IntentType.OPEN_FOLDER,
        }:
            if intent.intent_type is IntentType.OPEN_FOLDER:
                target_name = intent.metadata.get("target_name", "folder")
                return ExecutionPreview("open_folder", f"`{target_name}` Explorer me khulega.")
        if intent.intent_type in browser_intents:
            plan = self.browser_controller.resolve_browser_plan()
            if intent.intent_type is IntentType.SEARCH_PAGE:
                query = intent.metadata.get("query", "query")
                return ExecutionPreview(
                    "search_page",
                    f"Current page par `{query}` search karenge.",
                )
            if intent.intent_type is IntentType.GET_CURRENT_PAGE:
                return ExecutionPreview(
                    "get_current_page",
                    "Current page ka title aur URL dekhenge.",
                )
            if intent.intent_type is IntentType.OPEN_NEW_TAB:
                return ExecutionPreview("open_new_tab", "Browser me naya tab khulega.")
            if intent.intent_type is IntentType.SWITCH_TAB:
                return ExecutionPreview("switch_tab", "Browser me next tab par switch karenge.")
            if intent.intent_type is IntentType.FOCUS_ADDRESS_BAR:
                return ExecutionPreview(
                    "focus_address_bar",
                    "Browser ka address bar focus karenge.",
                )
            if intent.intent_type is IntentType.CLOSE_TAB:
                return ExecutionPreview(
                    "close_tab",
                    "Current browser tab band karenge.",
                )
            if intent.intent_type is IntentType.PLAY_YOUTUBE_PLAYLIST:
                query = intent.metadata.get("query", "playlist")
                return ExecutionPreview(
                    "play_youtube_playlist",
                    f"YouTube par `{query}` playlist search karke play karenge.",
                )
            if intent.intent_type is IntentType.SEARCH_YOUTUBE:
                query = intent.metadata.get("query", "search")
                return ExecutionPreview(
                    "search_youtube",
                    f"YouTube par `{query}` search karenge.",
                )
            if intent.intent_type is IntentType.OPEN_INSTAGRAM_LOGIN:
                detail = (
                    "Instagram login page isolated browser me khulega."
                    if plan.uses_isolated_session
                    else "Instagram login page Edge me khulega."
                )
                return ExecutionPreview(
                    "open_instagram_login",
                    detail,
                )
            if intent.intent_type is IntentType.OPEN_WHATSAPP_WEB:
                detail = (
                    "WhatsApp Web isolated browser me khulega."
                    if plan.uses_isolated_session
                    else "WhatsApp Web Edge me khulega."
                )
                return ExecutionPreview(
                    "open_whatsapp_web",
                    detail,
                )
            return ExecutionPreview("browser_plan", plan.describe())
        if intent.intent_type in {IntentType.OPEN_APP, IntentType.CLOSE_APP}:
            app_name = intent.metadata.get("app_name", "unknown app")
            return ExecutionPreview(
                intent.intent_type.value,
                f"{app_name.title()} par action hoga.",
            )
        if intent.intent_type is IntentType.FOCUS_APP:
            app_name = intent.metadata.get("app_name", "current app")
            return ExecutionPreview("focus_app", f"{app_name.title()} par focus karenge.")
        if intent.intent_type is IntentType.MINIMIZE_WINDOW:
            return ExecutionPreview("minimize_window", "Current window minimize karenge.")
        if intent.intent_type is IntentType.MAXIMIZE_WINDOW:
            return ExecutionPreview("maximize_window", "Current window maximize karenge.")
        if intent.intent_type is IntentType.NEXT_WINDOW:
            return ExecutionPreview("next_window", "Agli window par switch karenge.")
        if intent.intent_type in {IntentType.CREATE_FOLDER, IntentType.CREATE_FILE}:
            target_name = intent.metadata.get("target_name", "new item")
            return ExecutionPreview(intent.intent_type.value, f"`{target_name}` create hoga.")
        if intent.intent_type is IntentType.MOVE_PATH:
            source_name = intent.metadata.get("source_name", "item")
            destination_name = intent.metadata.get("destination_name", "destination")
            return ExecutionPreview(
                "move_path",
                f"`{source_name}` ko `{destination_name}` me move karenge.",
            )
        if intent.intent_type is IntentType.RENAME_PATH:
            source_name = intent.metadata.get("source_name", "item")
            new_name = intent.metadata.get("new_name", "new-name")
            return ExecutionPreview(
                "rename_path",
                f"`{source_name}` ka naam `{new_name}` rakhenge.",
            )
        return ExecutionPreview("unimplemented", "Execution path scaffolded for a later phase.")

    def execute(self, intent: ParsedIntent, *, confirmed: bool = False) -> ExecutionResult:
        if intent.intent_type is IntentType.OPEN_BROWSER:
            page = self.browser_controller.open_url("https://www.google.com", confirmed=confirmed)
            return ExecutionResult(
                action_name="open_browser",
                success=True,
                detail="Browser khol diya.",
                data=page.as_dict(),
            )

        if intent.intent_type is IntentType.OPEN_WEBSITE:
            url = intent.metadata["url"]
            page = self.browser_controller.open_url(url, confirmed=confirmed)
            return ExecutionResult(
                action_name="open_website",
                success=True,
                detail=f"{url} khol diya.",
                data=page.as_dict(),
            )

        if intent.intent_type is IntentType.FOCUS_ADDRESS_BAR:
            page = self.browser_controller.focus_address_bar()
            return ExecutionResult(
                action_name="focus_address_bar",
                success=True,
                detail="Address bar focus kar diya.",
                data=page.as_dict(),
            )

        if intent.intent_type is IntentType.OPEN_NEW_TAB:
            page = self.browser_controller.open_new_tab(intent.metadata.get("url", "about:blank"))
            return ExecutionResult(
                action_name="open_new_tab",
                success=True,
                detail="Naya tab khol diya.",
                data=page.as_dict(),
            )

        if intent.intent_type is IntentType.SWITCH_TAB:
            page = self.browser_controller.switch_tab(
                direction=intent.metadata.get("direction", "next")
            )
            return ExecutionResult(
                action_name="switch_tab",
                success=True,
                detail="Tab switch kar diya.",
                data=page.as_dict(),
            )

        if intent.intent_type is IntentType.SEARCH_PAGE:
            result = self.browser_controller.search_on_page(intent.metadata["query"])
            return ExecutionResult(
                action_name="search_page",
                success=True,
                detail=f"Current page par `{intent.metadata['query']}` search kar diya.",
                data=result.as_dict(),
            )

        if intent.intent_type is IntentType.GET_CURRENT_PAGE:
            page = self.browser_controller.current_page_state()
            return ExecutionResult(
                action_name="get_current_page",
                success=True,
                detail=f"Current page: {page.title or 'Untitled'} | {page.url}",
                data=page.as_dict(),
            )

        if intent.intent_type is IntentType.OPEN_YOUTUBE:
            page = self.browser_controller.open_youtube()
            return ExecutionResult(
                action_name="open_youtube",
                success=True,
                detail="YouTube khol diya.",
                data=page.as_dict(),
            )

        if intent.intent_type is IntentType.SEARCH_YOUTUBE:
            open_first = intent.metadata.get("compound_open_first", "").lower() == "true"
            page, verification = self.browser_controller.search_youtube(
                intent.metadata["query"],
                open_first=open_first,
            )
            result_data = page.as_dict() | {"query": intent.metadata["query"]} | verification
            if not bool(verification.get("action_verified")):
                return ExecutionResult(
                    action_name="search_youtube",
                    success=False,
                    detail=(
                        "YouTube khul gaya, lekin "
                        f"`{intent.metadata['query']}` search verify nahi hua."
                    ),
                    data=result_data,
                )
            return ExecutionResult(
                action_name="search_youtube",
                success=True,
                detail=f"YouTube par `{intent.metadata['query']}` search kar diya.",
                data=result_data,
            )

        if intent.intent_type is IntentType.PLAY_YOUTUBE_PLAYLIST:
            playback = self.browser_controller.play_youtube_playlist(intent.metadata["query"])
            detail = (
                f"YouTube par `{intent.metadata['query']}` playlist chala di."
                if playback.playing
                else f"YouTube par `{intent.metadata['query']}` result khol diya."
            )
            return ExecutionResult(
                action_name="play_youtube_playlist",
                success=True,
                detail=detail,
                data=playback.as_dict(),
            )

        if intent.intent_type is IntentType.OPEN_INSTAGRAM_LOGIN:
            page = self.browser_controller.open_instagram_login(confirmed=confirmed)
            return ExecutionResult(
                action_name="open_instagram_login",
                success=True,
                detail="Instagram login page khol diya.",
                data=page.as_dict(),
            )

        if intent.intent_type is IntentType.OPEN_WHATSAPP_WEB:
            page = self.browser_controller.open_whatsapp_web(confirmed=confirmed)
            return ExecutionResult(
                action_name="open_whatsapp_web",
                success=True,
                detail="WhatsApp Web khol diya.",
                data=page.as_dict(),
            )

        if intent.intent_type is IntentType.OPEN_FOLDER:
            target = self.window_controller.open_folder(intent.metadata["target_name"])
            return ExecutionResult(
                action_name="open_folder",
                success=True,
                detail=f"{target.name or target.drive} Explorer me khol diya.",
                data={"path": str(target)},
            )

        if intent.intent_type is IntentType.CLOSE_TAB:
            page = self.browser_controller.close_current_tab(confirmed=confirmed)
            return ExecutionResult(
                action_name="close_tab",
                success=True,
                detail="Current browser tab band kar diya.",
                data=page.as_dict(),
            )

        if intent.intent_type is IntentType.OPEN_APP:
            app_name = intent.metadata["app_name"]
            process = self.window_controller.launch_app(app_name)
            return ExecutionResult(
                action_name="open_app",
                success=True,
                detail=f"{app_name.title()} khol diya.",
                data={"app_name": app_name, "pid": str(process.pid) if process is not None else ""},
            )

        if intent.intent_type is IntentType.CLOSE_APP:
            app_name = intent.metadata["app_name"]
            preferred_pid = (
                int(intent.metadata["preferred_pid"])
                if intent.metadata.get("preferred_pid")
                else None
            )
            terminated = self.window_controller.close_app(app_name, preferred_pid=preferred_pid)
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
                data={
                    "app_name": app_name,
                    "terminated": str(terminated),
                    "preferred_pid": str(preferred_pid or ""),
                },
            )

        if intent.intent_type is IntentType.CREATE_FOLDER:
            base_dir = (
                Path(intent.metadata["base_dir"]) if intent.metadata.get("base_dir") else None
            )
            target = self.window_controller.create_folder(
                intent.metadata["target_name"],
                base_dir=base_dir,
            )
            return ExecutionResult(
                action_name="create_folder",
                success=True,
                detail=f"Folder bana diya: {target.name}",
                data={"path": str(target)},
            )

        if intent.intent_type is IntentType.CREATE_FILE:
            base_dir = (
                Path(intent.metadata["base_dir"]) if intent.metadata.get("base_dir") else None
            )
            target = self.window_controller.create_file(
                intent.metadata["target_name"],
                base_dir=base_dir,
            )
            return ExecutionResult(
                action_name="create_file",
                success=True,
                detail=f"File bana di: {target.name}",
                data={"path": str(target)},
            )

        if intent.intent_type is IntentType.RENAME_PATH:
            target = self.window_controller.rename_path(
                intent.metadata["source_name"],
                intent.metadata["new_name"],
            )
            return ExecutionResult(
                action_name="rename_path",
                success=True,
                detail=f"Rename kar diya: {target.name}",
                data={"path": str(target)},
            )

        if intent.intent_type is IntentType.MOVE_PATH:
            target = self.window_controller.move_path(
                intent.metadata["source_name"],
                intent.metadata["destination_name"],
            )
            return ExecutionResult(
                action_name="move_path",
                success=True,
                detail=f"Move kar diya: {target.name}",
                data={"path": str(target)},
            )

        if intent.intent_type is IntentType.FOCUS_APP:
            app_name = intent.metadata["app_name"]
            info = self.window_controller.focus_app_window(app_name)
            return ExecutionResult(
                action_name="focus_app",
                success=True,
                detail=f"{app_name.title()} par focus kar diya.",
                data={"app_name": app_name} | info,
            )

        if intent.intent_type is IntentType.MINIMIZE_WINDOW:
            info = self.window_controller.minimize_foreground_window()
            return ExecutionResult(
                action_name="minimize_window",
                success=True,
                detail="Current window minimize kar diya.",
                data=info,
            )

        if intent.intent_type is IntentType.MAXIMIZE_WINDOW:
            info = self.window_controller.maximize_foreground_window()
            return ExecutionResult(
                action_name="maximize_window",
                success=True,
                detail="Current window maximize kar diya.",
                data=info,
            )

        if intent.intent_type is IntentType.NEXT_WINDOW:
            info = self.window_controller.activate_next_window()
            return ExecutionResult(
                action_name="next_window",
                success=True,
                detail="Next window par aa gayi.",
                data=info,
            )

        return ExecutionResult(
            action_name="unimplemented",
            success=False,
            detail="Is command ka execution Phase 4 MVP me abhi wired nahi hai.",
        )
