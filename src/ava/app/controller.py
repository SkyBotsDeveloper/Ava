from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ava.app.state import AssistantState, AssistantStatus, BrowserTaskContext
from ava.automation.executor import ActionExecutor
from ava.config.settings import Settings
from ava.intents.models import IntentType, ParsedIntent
from ava.intents.router import IntentRouter
from ava.memory.journal import ActionJournalStore
from ava.safety.policy import ConfirmationStatus, ResultStatus, SafetyDecision, SafetyPolicy

logger = logging.getLogger(__name__)


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

    def remember_browser_intent(
        self,
        intent: ParsedIntent,
        *,
        raw_text: str = "",
        source: str = "voice",
    ) -> None:
        if intent.intent_type not in {
            IntentType.SEARCH_YOUTUBE,
            IntentType.PLAY_YOUTUBE_PLAYLIST,
        }:
            return

        query = (intent.metadata.get("query") or "").strip()
        if not query:
            return

        existing = self.state.active_browser_task
        existing_intended = (existing.intended_query if existing is not None else "").strip()
        chosen_query = self._prefer_richer_query(existing_intended, query)
        task_kind = (
            "youtube_playlist"
            if intent.intent_type is IntentType.PLAY_YOUTUBE_PLAYLIST
            else "youtube_search"
        )
        self.state.active_browser_task = BrowserTaskContext(
            task_kind=task_kind,
            query=(existing.query if existing is not None else "").strip(),
            intended_query=chosen_query,
            url=(existing.url if existing is not None else "https://www.youtube.com"),
            page_title=existing.page_title if existing is not None else "",
            page_url=existing.page_url if existing is not None else "",
            browser_name=existing.browser_name if existing is not None else "edge",
            last_action_name=existing.last_action_name if existing is not None else "",
            turns_remaining=max(existing.turns_remaining, 4) if existing is not None else 4,
        )
        logger.info(
            "Stored intended browser query for active task",
            extra={
                "event": "browser_intended_query_remembered",
                "raw_command": raw_text,
                "query": chosen_query,
                "intent_type": intent.intent_type.value,
                "source": source,
            },
        )

    def handle_text_command(self, raw_text: str, *, source: str = "text") -> CommandResult:
        cleaned = raw_text.strip()
        if not cleaned:
            self.state.last_response = "Command khaali hai."
            return CommandResult(self.state.last_response)

        self.state.last_command = cleaned
        intent = self._apply_execution_context(self.intent_router.parse(cleaned, source=source))
        follow_up_intent = self.resolve_browser_follow_up_intent(
            cleaned,
            parsed_intent=intent,
            source=intent.source,
        )

        missing_context_message = self._missing_context_message(intent)
        if missing_context_message is not None:
            self.state.last_response = missing_context_message
            self.state.status = AssistantStatus.IDLE
            self._record_journal(
                command_text=cleaned,
                action_name="missing_execution_context",
                confirmation_status=ConfirmationStatus.NOT_NEEDED,
                result_status=ResultStatus.FAILURE,
                source=intent.source,
                details={"intent_type": intent.intent_type.value},
            )
            return CommandResult(self.state.last_response)

        if intent.intent_type is IntentType.CONFIRM:
            return self._handle_confirmation(True)
        if intent.intent_type is IntentType.DENY:
            return self._handle_confirmation(False)

        if intent.intent_type is IntentType.CANCEL:
            self._pending_action = None
            self._clear_browser_task_context(reason="cancel")
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

        if follow_up_intent is not None:
            logger.info(
                "Browser follow-up corrective action chosen",
                extra={
                    "event": "browser_followup_action_chosen",
                    "raw_command": cleaned,
                    "intent_type": follow_up_intent.intent_type.value,
                    "query": follow_up_intent.metadata.get("query", ""),
                    "url": follow_up_intent.metadata.get("url", ""),
                },
            )
            return self._execute_intent(cleaned, follow_up_intent, ConfirmationStatus.NOT_NEEDED)

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
            self._clear_browser_task_context(reason="general_command")
            self._record_journal(
                command_text=cleaned,
                action_name="command_received",
                confirmation_status=ConfirmationStatus.NOT_NEEDED,
                result_status=ResultStatus.SUCCESS,
                source=intent.source,
                details={"intent_type": intent.intent_type.value},
            )
            return CommandResult(self.state.last_response)

        confirmation_required_intents = {
            IntentType.MOVE_PATH,
            IntentType.RENAME_PATH,
            IntentType.CLOSE_TAB,
            IntentType.OPEN_INSTAGRAM_LOGIN,
            IntentType.OPEN_WHATSAPP_WEB,
        }
        if intent.intent_type in confirmation_required_intents:
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
        if (
            intent.intent_type is IntentType.SEARCH_YOUTUBE
            and intent.metadata.get("compound_open_first", "").lower() == "true"
        ):
            logger.info(
                "Compound browser intent detected",
                extra={
                    "event": "compound_browser_intent_detected",
                    "raw_command": command_text,
                    "normalized_command": intent.normalized_text,
                    "intent_type": intent.intent_type.value,
                },
            )
            logger.info(
                "Extracted YouTube search query",
                extra={
                    "event": "youtube_search_query_extracted",
                    "raw_command": command_text,
                    "query": intent.metadata.get("query", ""),
                },
            )
        self.state.status = AssistantStatus.THINKING
        try:
            result = self.executor.execute(
                intent,
                confirmed=confirmation_status is ConfirmationStatus.CONFIRMED,
            )
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
        self._sync_browser_task_context(intent=intent, result=result)
        self._sync_filesystem_context(intent=intent, result=result)
        self._sync_app_context(intent=intent, result=result)
        if result.success and bool((result.data or {}).get("action_verified")):
            logger.info(
                "Generated verified action acknowledgment",
                extra={
                    "event": "action_verified_ack_generated",
                    "action_name": result.action_name,
                    "response_text": result.detail,
                    "verified_via": (result.data or {}).get("verified_via", ""),
                },
            )
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

    def resolve_browser_follow_up_intent(
        self,
        raw_text: str,
        *,
        parsed_intent: ParsedIntent | None = None,
        source: str = "text",
    ) -> ParsedIntent | None:
        context = self.state.active_browser_task
        if context is None or context.turns_remaining <= 0:
            return None

        intent = parsed_intent or self.intent_router.parse(raw_text, source=source)
        normalized = intent.normalized_text
        lowered = normalized.lower()
        stored_query = self._stored_browser_query(context)

        if stored_query and self._looks_like_youtube_correction(lowered, context):
            logger.info(
                "Follow-up browser task detected",
                extra={
                    "event": "browser_followup_detected",
                    "raw_command": raw_text,
                    "task_kind": context.task_kind,
                    "query": stored_query,
                    "page_url": context.page_url,
                },
            )
            logger.info(
                "Loaded stored browser query for retry",
                extra={
                    "event": "stored_browser_query_loaded",
                    "raw_command": raw_text,
                    "stored_query": stored_query,
                    "task_kind": context.task_kind,
                    "last_action_name": context.last_action_name,
                },
            )
            logger.info(
                "Retrying browser action from stored query",
                extra={
                    "event": "browser_retry_from_stored_query",
                    "raw_command": raw_text,
                    "stored_query": stored_query,
                    "task_kind": context.task_kind,
                    "last_action_name": context.last_action_name,
                },
            )
            return ParsedIntent(
                intent_type=IntentType.SEARCH_YOUTUBE,
                raw_text=raw_text,
                normalized_text=normalized,
                source=source,
                metadata={
                    "query": stored_query,
                    "follow_up_reason": "retry_youtube_search_from_stored_query",
                    "context_task_kind": context.task_kind,
                    "compound_open_first": "true",
                    "compound_action": "open_youtube_then_search",
                    "stored_query_retry": "true",
                },
            )

        if stored_query and self._looks_like_youtube_retry(lowered, context):
            logger.info(
                "Follow-up browser task detected",
                extra={
                    "event": "browser_followup_detected",
                    "raw_command": raw_text,
                    "task_kind": context.task_kind,
                    "query": stored_query,
                    "page_url": context.page_url,
                },
            )
            logger.info(
                "Loaded stored browser query for retry",
                extra={
                    "event": "stored_browser_query_loaded",
                    "raw_command": raw_text,
                    "stored_query": stored_query,
                    "task_kind": context.task_kind,
                    "last_action_name": context.last_action_name,
                },
            )
            logger.info(
                "Retrying browser action from stored query",
                extra={
                    "event": "browser_retry_from_stored_query",
                    "raw_command": raw_text,
                    "task_kind": context.task_kind,
                    "stored_query": stored_query,
                    "last_action_name": context.last_action_name,
                },
            )
            return ParsedIntent(
                intent_type=IntentType.SEARCH_YOUTUBE,
                raw_text=raw_text,
                normalized_text=normalized,
                source=source,
                metadata={
                    "query": stored_query,
                    "follow_up_reason": "retry_youtube_search",
                    "context_task_kind": context.task_kind,
                    "compound_open_first": "true",
                    "compound_action": "open_youtube_then_search",
                    "stored_query_retry": "true",
                },
            )

        if stored_query and self._looks_like_youtube_play_request(lowered, context):
            logger.info(
                "Follow-up browser task detected",
                extra={
                    "event": "browser_followup_detected",
                    "raw_command": raw_text,
                    "task_kind": context.task_kind,
                    "query": stored_query,
                    "page_url": context.page_url,
                },
            )
            logger.info(
                "Loaded stored browser query for retry",
                extra={
                    "event": "stored_browser_query_loaded",
                    "raw_command": raw_text,
                    "stored_query": stored_query,
                    "task_kind": context.task_kind,
                    "last_action_name": context.last_action_name,
                },
            )
            return ParsedIntent(
                intent_type=IntentType.PLAY_YOUTUBE_PLAYLIST,
                raw_text=raw_text,
                normalized_text=normalized,
                source=source,
                metadata={
                    "query": stored_query,
                    "follow_up_reason": "retry_youtube_playlist",
                    "context_task_kind": context.task_kind,
                    "compound_open_first": "true",
                    "compound_action": "open_youtube_then_play_playlist",
                    "stored_query_retry": "true",
                },
            )

        if context.url and self._looks_like_browser_reopen(lowered):
            logger.info(
                "Follow-up browser task detected",
                extra={
                    "event": "browser_followup_detected",
                    "raw_command": raw_text,
                    "task_kind": context.task_kind,
                    "query": context.query,
                    "page_url": context.page_url,
                },
            )
            return ParsedIntent(
                intent_type=IntentType.OPEN_WEBSITE,
                raw_text=raw_text,
                normalized_text=normalized,
                source=source,
                metadata={
                    "url": context.url,
                    "label": context.url,
                    "follow_up_reason": "reopen_browser_target",
                    "context_task_kind": context.task_kind,
                },
            )

        return None

    def has_browser_follow_up_candidate(self, raw_text: str, *, source: str = "voice") -> bool:
        return self.resolve_browser_follow_up_intent(raw_text, source=source) is not None

    def _sync_browser_task_context(self, *, intent: ParsedIntent, result) -> None:
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
        if intent.intent_type not in browser_intents or not result.success:
            if intent.intent_type not in browser_intents:
                self._clear_browser_task_context(reason="non_browser_action")
            return

        data = result.data or {}
        if intent.intent_type is IntentType.SEARCH_YOUTUBE:
            task_kind = "youtube_search"
        elif intent.intent_type is IntentType.PLAY_YOUTUBE_PLAYLIST:
            task_kind = "youtube_playlist"
        elif intent.intent_type is IntentType.OPEN_YOUTUBE:
            task_kind = (
                self.state.active_browser_task.task_kind
                if self.state.active_browser_task is not None
                and self.state.active_browser_task.intended_query
                else "youtube_open"
            )
        else:
            task_kind = "browser_navigation"

        existing = self.state.active_browser_task
        intended_query = (intent.metadata.get("query") or "").strip() or (
            existing.intended_query if existing is not None else ""
        ).strip()
        last_query = (intent.metadata.get("query") or "").strip() or (
            existing.query if existing is not None else ""
        ).strip()
        self.state.active_browser_task = BrowserTaskContext(
            task_kind=task_kind,
            query=last_query,
            intended_query=intended_query,
            url=intent.metadata.get(
                "url",
                data.get("url", existing.url if existing is not None else ""),
            ),
            page_title=str(data.get("title", existing.page_title if existing is not None else "")),
            page_url=str(data.get("url", existing.page_url if existing is not None else "")),
            browser_name=str(
                data.get("browser_name", existing.browser_name if existing is not None else "")
            ),
            last_action_name=result.action_name,
            turns_remaining=3,
        )

    def _clear_browser_task_context(self, *, reason: str) -> None:
        if self.state.active_browser_task is None:
            return
        logger.info(
            "Browser task context cleared",
            extra={
                "event": "browser_task_context_cleared",
                "reason": reason,
                "task_kind": self.state.active_browser_task.task_kind,
                "query": self.state.active_browser_task.query,
            },
        )
        self.state.active_browser_task = None

    def _apply_execution_context(self, intent: ParsedIntent) -> ParsedIntent:
        metadata = dict(intent.metadata)
        filesystem = self.state.filesystem_context
        app_context = self.state.app_context

        if intent.intent_type in {IntentType.CREATE_FILE, IntentType.CREATE_FOLDER} and (
            metadata.get("use_active_folder_context") == "true"
        ):
            base_dir = filesystem.current_folder_path or str(Path.cwd())
            metadata["base_dir"] = base_dir
            if not metadata.get("target_name"):
                metadata["target_name"] = self._default_item_name(
                    intent.intent_type,
                    base_dir=base_dir,
                )

        if intent.intent_type is IntentType.RENAME_PATH:
            if metadata.get("use_active_file_context") == "true":
                source_path = filesystem.last_file_path
                if source_path:
                    metadata["source_name"] = source_path
                    metadata["path_kind"] = "file"
                    metadata["new_name"] = self._normalize_renamed_file_name(
                        source_path,
                        metadata.get("new_name", ""),
                    )
            elif metadata.get("use_active_folder_context") == "true":
                source_path = filesystem.last_folder_path
                if source_path:
                    metadata["source_name"] = source_path
                    metadata["path_kind"] = "folder"

        if intent.intent_type is IntentType.MOVE_PATH:
            if metadata.get("use_active_file_context") == "true" and filesystem.last_file_path:
                metadata["source_name"] = filesystem.last_file_path
                metadata["path_kind"] = "file"
            elif (
                metadata.get("use_active_folder_context") == "true" and filesystem.last_folder_path
            ):
                metadata["source_name"] = filesystem.last_folder_path
                metadata["path_kind"] = "folder"

        if intent.intent_type in {IntentType.CLOSE_APP, IntentType.FOCUS_APP}:
            if metadata.get("use_active_app_context") == "true" and app_context.app_name:
                metadata["app_name"] = app_context.app_name
            if (
                intent.intent_type is IntentType.CLOSE_APP
                and metadata.get("app_name") == app_context.app_name
                and app_context.pid
            ):
                metadata["preferred_pid"] = str(app_context.pid)

        if metadata == intent.metadata:
            return intent
        return ParsedIntent(
            intent_type=intent.intent_type,
            raw_text=intent.raw_text,
            normalized_text=intent.normalized_text,
            source=intent.source,
            immediate=intent.immediate,
            metadata=metadata,
        )

    def _missing_context_message(self, intent: ParsedIntent) -> str | None:
        metadata = intent.metadata
        filesystem = self.state.filesystem_context
        app_context = self.state.app_context

        if intent.intent_type in {IntentType.CREATE_FILE, IntentType.CREATE_FOLDER} and (
            metadata.get("use_active_folder_context") == "true"
        ):
            if not filesystem.current_folder_path:
                return "Pehle folder kholo, phir is folder me item banao."

        if intent.intent_type is IntentType.RENAME_PATH:
            if metadata.get("use_active_file_context") == "true" and not filesystem.last_file_path:
                return "Pehle file create ya select karo, phir naam badalungi."
            if (
                metadata.get("use_active_folder_context") == "true"
                and not filesystem.last_folder_path
            ):
                return "Pehle folder create ya open karo, phir naam badalungi."

        if intent.intent_type is IntentType.MOVE_PATH:
            if metadata.get("use_active_file_context") == "true" and not filesystem.last_file_path:
                return "Pehle file create ya select karo, phir move karungi."
            if (
                metadata.get("use_active_folder_context") == "true"
                and not filesystem.last_folder_path
            ):
                return "Pehle folder create ya select karo, phir move karungi."

        if intent.intent_type is IntentType.FOCUS_APP and not metadata.get("app_name"):
            if not app_context.app_name:
                return "Pehle app kholo ya uska naam bolo, phir focus karungi."

        return None

    def _sync_filesystem_context(self, *, intent: ParsedIntent, result) -> None:
        if not result.success:
            return
        data = result.data or {}
        filesystem = self.state.filesystem_context
        path = str(data.get("path", ""))
        if intent.intent_type is IntentType.OPEN_FOLDER and path:
            filesystem.current_folder_path = path
            filesystem.last_folder_path = path
            return
        if intent.intent_type is IntentType.CREATE_FILE and path:
            filesystem.last_file_path = path
            filesystem.current_folder_path = str(Path(path).parent)
            return
        if intent.intent_type is IntentType.CREATE_FOLDER and path:
            filesystem.last_folder_path = path
            base_dir = intent.metadata.get("base_dir")
            if base_dir:
                filesystem.current_folder_path = base_dir
            return
        if intent.intent_type in {IntentType.RENAME_PATH, IntentType.MOVE_PATH} and path:
            path_kind = intent.metadata.get("path_kind", "")
            if path_kind == "file":
                filesystem.last_file_path = path
                filesystem.current_folder_path = str(Path(path).parent)
            elif path_kind == "folder":
                filesystem.last_folder_path = path

    def _sync_app_context(self, *, intent: ParsedIntent, result) -> None:
        if not result.success:
            return
        app_context = self.state.app_context
        data = result.data or {}
        if intent.intent_type is IntentType.OPEN_APP:
            app_context.app_name = str(data.get("app_name", ""))
            app_context.pid = int(data.get("pid", "0") or 0)
            return
        if intent.intent_type is IntentType.FOCUS_APP:
            app_context.app_name = str(data.get("app_name", app_context.app_name))
            pid_value = str(data.get("pid", "")) or str(app_context.pid)
            app_context.pid = int(pid_value or 0)
            return
        if (
            intent.intent_type is IntentType.CLOSE_APP
            and str(data.get("app_name", "")) == app_context.app_name
        ):
            app_context.app_name = ""
            app_context.pid = 0

    @staticmethod
    def _default_item_name(intent_type: IntentType, *, base_dir: str) -> str:
        existing_names = {path.name.lower() for path in Path(base_dir).glob("*")}
        stem = "ava-note" if intent_type is IntentType.CREATE_FILE else "ava-folder"
        suffix = ".txt" if intent_type is IntentType.CREATE_FILE else ""
        candidate = f"{stem}{suffix}"
        counter = 1
        while candidate.lower() in existing_names:
            counter += 1
            candidate = f"{stem}-{counter}{suffix}"
        return candidate

    @staticmethod
    def _normalize_renamed_file_name(source_path: str, new_name: str) -> str:
        cleaned = " ".join(new_name.split()).strip(" .")
        if not cleaned:
            return cleaned
        source_suffix = Path(source_path).suffix
        if "." not in Path(cleaned).name and source_suffix:
            return f"{cleaned}{source_suffix}"
        return cleaned

    @staticmethod
    def _looks_like_youtube_retry(normalized_text: str, context: BrowserTaskContext) -> bool:
        if not AvaController._is_youtube_context(context):
            return False
        collapsed_search_forms = {"search", "search karo", "search karo na", "search please"}
        if normalized_text.strip(" .!?") in collapsed_search_forms:
            return True
        retry_markers = (
            "search nahi hui",
            "search nahi hua",
            "search nahi ho",
            "dobara search",
            "phir se search",
            "playlist search",
            "retry search",
        )
        return any(marker in normalized_text for marker in retry_markers)

    @staticmethod
    def _looks_like_youtube_correction(normalized_text: str, context: BrowserTaskContext) -> bool:
        if not AvaController._is_youtube_context(context):
            return False
        collapsed_corrections = {
            "sirf youtube khola hai",
            "sirf youtube nahi kholna",
            "playlist bhi search karo",
            "jo maine bola tha woh search karo",
            "jo maine bola tha wo search karo",
            "woh search karo",
        }
        stripped = normalized_text.strip(" .!?")
        if stripped in collapsed_corrections:
            return True
        if "playlist" in normalized_text and "search" in normalized_text:
            return True
        correction_markers = (
            "sirf youtube khola",
            "sirf youtube nahi kholna",
            "playlist bhi search",
            "jo maine bola tha",
            "woh bhi search karo",
            "sirf youtube",
        )
        return any(marker in normalized_text for marker in correction_markers)

    @staticmethod
    def _looks_like_youtube_play_request(normalized_text: str, context: BrowserTaskContext) -> bool:
        if not AvaController._is_youtube_context(context):
            return False
        play_markers = (
            "playlist chalao",
            "playlist chala do",
            "play karo",
            "play kar do",
            "woh wala khol do",
        )
        return any(marker in normalized_text for marker in play_markers)

    @staticmethod
    def _looks_like_browser_reopen(normalized_text: str) -> bool:
        return any(
            marker in normalized_text
            for marker in ("dobara kholo", "phir se kholo", "reopen", "again kholo")
        )

    @staticmethod
    def _stored_browser_query(context: BrowserTaskContext) -> str:
        return (context.intended_query or context.query).strip()

    @staticmethod
    def _is_youtube_context(context: BrowserTaskContext) -> bool:
        searchable = " ".join(
            value.lower()
            for value in (
                context.task_kind,
                context.url,
                context.page_url,
                context.last_action_name,
            )
            if value
        )
        return "youtube" in searchable

    @staticmethod
    def _prefer_richer_query(existing_query: str, new_query: str) -> str:
        existing = " ".join(existing_query.split()).strip()
        new = " ".join(new_query.split()).strip()
        if not existing:
            return new
        if not new:
            return existing
        existing_terms = len(existing.split())
        new_terms = len(new.split())
        if new_terms > existing_terms:
            return new
        if new_terms == existing_terms and len(new) > len(existing):
            return new
        return existing
