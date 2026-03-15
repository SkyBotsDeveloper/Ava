from __future__ import annotations

import logging
import re
from typing import Final

from ava.intents.models import IntentType, ParsedIntent

logger = logging.getLogger(__name__)


class IntentRouter:
    NORMALIZATION_REPLACEMENTS: Final[tuple[tuple[str, str], ...]] = (
        (r"\bo\s*pen\b", "open"),
        (r"\bwe\s*b\s*site\b", "website"),
        (r"\bwe\s+bsite\b", "website"),
        (r"\bbsite\b", "website"),
        (r"\bnote\s*pad\b", "notepad"),
        (r"\bno\s*te\s*pad\b", "notepad"),
        (r"\bno\s*te\s*pa\s*d\b", "notepad"),
        (r"\bnote\s*book\b", "notepad"),
        (r"\bcalcu\s*lator\b", "calculator"),
        (r"\bcal\s*cu\s*la\s*tor\b", "calculator"),
        (r"\bdocu\s*ments\b", "documents"),
        (r"\bdo\s*cu\s*ment\s*s\b", "documents"),
        (r"\bdown\s*loads\b", "downloads"),
        (r"\bdown\s*load\s*s\b", "downloads"),
        (r"\bava[\s-]*test\b", "ava-test"),
        (r"\bdesk\s*top\b", "desktop"),
        (r"\bdes\s*ktop\b", "desktop"),
        (r"\bpa\s*int\b", "paint"),
        (r"\bfo\s*lder\b", "folder"),
        (r"\bfo\s*ld(?:er)?\b", "folder"),
        (r"\bfi\s*le\b", "file"),
        (r"\bpha\s*se\b", "phase"),
        (r"\ban\s+while\b", "new file"),
        (r"\bnew\s+while\b", "new file"),
        (r"\bnew\s+fall\b", "new file"),
        (r"\bis\s*up\b", "is app"),
        (r"\byou\s*tu\s*be\b", "youtube"),
        (r"\bne\s*xt\b", "next"),
        (r"\bta\s*p\b", "tab"),
        (r"\bsear\s*ch\b", "search"),
        (r"\bsho\s*w\b", "show"),
        (r"\bcur\s*rent\b", "current"),
        (r"\bti\s*tle\b", "title"),
        (r"\bpyt\s*hon\b", "python"),
        (r"\bplay\s*list\b", "playlist"),
        (r"\bin\s*sta\s*gram\b", "instagram"),
        (r"\blo\s*gin\b", "login"),
        (r"\bwha\s*tsapp\b", "whatsapp"),
        (r"\bad\s*dre\s*ss\s*(?:bar|ball)\b", "address bar"),
        (r"\bmini\s*mize\b", "minimize"),
        (r"\bmin\s*imi\s*ze\b", "minimize"),
        (r"\bmaxi\s*mize\b", "maximize"),
        (r"\bmax\s*imi\s*ze\b", "maximize"),
        (r"\bwin\s*dow\b", "window"),
        (r"\bwi\s*ndow\b", "window"),
        (r"\bfo\s*cus\b", "focus"),
        (r"\bmo\s*ve\b", "move"),
        (r"\bbad\s*lo\b", "badlo"),
        (r"\bbad\s*low\b", "badlo"),
        (r"\bar\s*chi\s*ve\b", "archive"),
        (r"\bhaan\s*ji\b", "haan"),
        (r"\bhan\b", "haan"),
        (r"\bca\s*ro\b", "karo"),
        (r"\bco\s*ro\b", "karo"),
        (r"\bpar\s+jo\b", "par jao"),
        (r"\bcolo\b", "kholo"),
        (r"\bholo\b", "kholo"),
    )
    CANCEL_TOKENS: Final = ("stop ava", "cancel", "bas", "ruk ja", "stop")
    CONFIRM_TOKENS: Final = ("haan", "haan ji", "yes", "confirm", "kar do", "theek hai")
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
    KNOWN_FOLDER_ALIASES: Final[dict[str, str]] = {
        "desktop": "desktop",
        "downloads": "downloads",
        "download": "downloads",
        "documents": "documents",
        "document": "documents",
        "docs": "documents",
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
        "powershell": "powershell",
        "task manager": "task manager",
        "settings": "settings",
        "snipping tool": "snipping tool",
        "edge": "edge",
        "chrome": "chrome",
        "vscode": "visual studio code",
        "vs code": "visual studio code",
        "code": "visual studio code",
        "telegram": "telegram",
        "whatsapp": "whatsapp",
        "spotify": "spotify",
        "discord": "discord",
    }

    def parse(self, raw_text: str, source: str = "text") -> ParsedIntent:
        normalized = self._normalize_text(raw_text)

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

        for parser in (
            self._parse_page_info,
            self._parse_page_search,
            self._parse_focus_address_bar,
            self._parse_new_tab,
            self._parse_switch_tab,
            self._parse_window_state,
            self._parse_next_window,
            self._parse_focus_app,
            self._parse_youtube_search,
            self._parse_youtube_playlist,
            self._parse_instagram_login,
            self._parse_whatsapp_web,
            self._parse_close_tab,
            self._parse_move_path,
            self._parse_rename_path,
            self._parse_create_file,
            self._parse_create_folder,
            self._parse_open_folder,
            self._parse_app_intent_close,
            self._parse_website_intent,
            self._parse_app_intent_open,
        ):
            intent = parser(raw_text, normalized, source)
            if intent is not None:
                return intent

        if "website" in normalized and any(
            token in normalized for token in ("khol", "open", "launch")
        ):
            return ParsedIntent(IntentType.OPEN_BROWSER, raw_text, normalized, source=source)
        if any(token in normalized for token in ("browser", "chrome", "edge")):
            return ParsedIntent(IntentType.OPEN_BROWSER, raw_text, normalized, source=source)
        return ParsedIntent(IntentType.GENERAL_COMMAND, raw_text, normalized, source=source)

    def _parse_page_info(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "page" not in normalized:
            return None
        if not any(token in normalized for token in ("title", "url", "batao", "kya hai", "show")):
            return None
        return ParsedIntent(IntentType.GET_CURRENT_PAGE, raw_text, normalized, source=source)

    def _parse_page_search(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "page" not in normalized:
            return None
        if not any(token in normalized for token in ("search", "dhundo", "find")):
            return None
        query = self._extract_search_query(raw_text) or self._extract_search_query(normalized)
        if query is None:
            return None
        return ParsedIntent(
            IntentType.SEARCH_PAGE,
            raw_text,
            normalized,
            source=source,
            metadata={"query": query},
        )

    def _parse_focus_address_bar(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "address bar" not in normalized:
            return None
        if not any(token in normalized for token in ("jao", "focus", "par ja", "open")):
            return None
        return ParsedIntent(IntentType.FOCUS_ADDRESS_BAR, raw_text, normalized, source=source)

    def _parse_new_tab(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "tab" not in normalized:
            return None
        if not any(token in normalized for token in ("new", "naya", "nayi")):
            return None
        if not any(token in normalized for token in ("khol", "open", "launch", "bana")):
            return None
        url_match = re.search(
            r"(https?://\S+|file:///\S+|www\.\S+\.\S+)",
            raw_text,
            flags=re.IGNORECASE,
        )
        metadata: dict[str, str] = {}
        if url_match:
            url = url_match.group(1)
            if url.lower().startswith("www."):
                url = f"https://{url}"
            metadata["url"] = url
        return ParsedIntent(
            IntentType.OPEN_NEW_TAB,
            raw_text,
            normalized,
            source=source,
            metadata=metadata,
        )

    def _parse_switch_tab(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "tab" not in normalized:
            return None
        if not any(
            token in normalized for token in ("switch", "next", "previous", "agla", "peeche")
        ):
            return None
        direction = (
            "previous"
            if any(token in normalized for token in ("previous", "back", "peeche"))
            else "next"
        )
        return ParsedIntent(
            IntentType.SWITCH_TAB,
            raw_text,
            normalized,
            source=source,
            metadata={"direction": direction},
        )

    def _parse_youtube_playlist(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "youtube" not in normalized:
            return None
        if any(token in normalized for token in ("playlist", "play")):
            query = self._extract_playlist_query(raw_text) or self._extract_playlist_query(
                normalized
            )
            if query:
                return ParsedIntent(
                    IntentType.PLAY_YOUTUBE_PLAYLIST,
                    raw_text,
                    normalized,
                    source=source,
                    metadata={
                        "query": query,
                        "compound_open_first": "true",
                        "compound_action": "open_youtube_then_play_playlist",
                    },
                )
        if any(token in normalized for token in ("khol", "open", "launch")):
            return ParsedIntent(IntentType.OPEN_YOUTUBE, raw_text, normalized, source=source)
        return None

    def _parse_youtube_search(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "youtube" not in normalized:
            return None
        if not any(token in normalized for token in ("search", "find", "dhundo")):
            return None
        query = self._extract_youtube_search_query(raw_text) or self._extract_youtube_search_query(
            normalized
        )
        if not query:
            return None
        logger.info(
            "Compound browser intent detected",
            extra={
                "event": "compound_browser_intent_detected",
                "raw_command": raw_text,
                "normalized_command": normalized,
                "intent_type": IntentType.SEARCH_YOUTUBE.value,
            },
        )
        logger.info(
            "Extracted YouTube search query",
            extra={
                "event": "youtube_search_query_extracted",
                "raw_command": raw_text,
                "query": query,
            },
        )
        return ParsedIntent(
            IntentType.SEARCH_YOUTUBE,
            raw_text,
            normalized,
            source=source,
            metadata={
                "query": query,
                "compound_open_first": "true",
                "compound_action": "open_youtube_then_search",
            },
        )

    def _parse_instagram_login(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if not any(token in normalized for token in ("instagram", "insta")):
            return None
        if "login" not in normalized:
            return None
        if not any(token in normalized for token in ("khol", "open", "launch")):
            return None
        return ParsedIntent(IntentType.OPEN_INSTAGRAM_LOGIN, raw_text, normalized, source=source)

    def _parse_whatsapp_web(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "whatsapp" not in normalized:
            return None
        if "web" not in normalized:
            return None
        if not any(token in normalized for token in ("khol", "open", "launch")):
            return None
        return ParsedIntent(IntentType.OPEN_WHATSAPP_WEB, raw_text, normalized, source=source)

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

    def _parse_window_state(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "window" not in normalized:
            return None
        if "minimize" in normalized:
            return ParsedIntent(IntentType.MINIMIZE_WINDOW, raw_text, normalized, source=source)
        if "maximize" in normalized:
            return ParsedIntent(IntentType.MAXIMIZE_WINDOW, raw_text, normalized, source=source)
        return None

    def _parse_next_window(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "window" not in normalized:
            return None
        if any(token in normalized for token in ("next", "agla", "next window", "next par ja")):
            return ParsedIntent(IntentType.NEXT_WINDOW, raw_text, normalized, source=source)
        return None

    def _parse_focus_app(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if "focus" not in normalized and "par jao" not in normalized:
            return None

        if "is app" in normalized:
            return ParsedIntent(
                IntentType.FOCUS_APP,
                raw_text,
                normalized,
                source=source,
                metadata={"use_active_app_context": "true"},
            )

        for alias, app_name in self.APP_ALIASES.items():
            if alias in normalized and ("focus" in normalized or f"{alias} par jao" in normalized):
                return ParsedIntent(
                    IntentType.FOCUS_APP,
                    raw_text,
                    normalized,
                    source=source,
                    metadata={"app_name": app_name},
                )
        return None

    def _parse_move_path(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        contextual_intent = self._parse_contextual_move(raw_text, normalized, source)
        if contextual_intent is not None:
            return contextual_intent
        if not (
            normalized.startswith("move ")
            or any(token in normalized for token in (" move ", " shift", "le ja", "bhej"))
        ):
            return None
        names = self._extract_quoted_names(raw_text)
        if len(names) < 2:
            return None
        return ParsedIntent(
            IntentType.MOVE_PATH,
            raw_text,
            normalized,
            source=source,
            metadata={"source_name": names[0], "destination_name": names[1]},
        )

    def _parse_rename_path(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        contextual_intent = self._parse_contextual_rename(raw_text, normalized, source)
        if contextual_intent is not None:
            return contextual_intent
        if not any(token in normalized for token in ("rename", "naam badal", "naam change")):
            return None
        names = self._extract_quoted_names(raw_text)
        if len(names) < 2:
            return None
        return ParsedIntent(
            IntentType.RENAME_PATH,
            raw_text,
            normalized,
            source=source,
            metadata={"source_name": names[0], "new_name": names[1]},
        )

    def _parse_create_folder(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if (
            "is folder" in normalized
            and "folder" in normalized
            and any(token in normalized for token in ("create", "banao", "bana do", "new"))
        ):
            return ParsedIntent(
                IntentType.CREATE_FOLDER,
                raw_text,
                normalized,
                source=source,
                metadata={"use_active_folder_context": "true"},
            )
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
        if (
            "is folder" in normalized
            and "file" in normalized
            and any(token in normalized for token in ("create", "banao", "bana do", "new"))
        ):
            return ParsedIntent(
                IntentType.CREATE_FILE,
                raw_text,
                normalized,
                source=source,
                metadata={"use_active_folder_context": "true"},
            )
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

    def _parse_open_folder(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if not any(token in normalized for token in ("khol", "open", "show", "go to")):
            return None
        folder_name = self._extract_named_target(raw_text, ("folder", "directory"))
        if folder_name:
            return ParsedIntent(
                IntentType.OPEN_FOLDER,
                raw_text,
                normalized,
                source=source,
                metadata={"target_name": folder_name},
            )

        path_match = re.search(r"([a-zA-Z]:\\[^\"']+)", raw_text)
        if path_match:
            return ParsedIntent(
                IntentType.OPEN_FOLDER,
                raw_text,
                normalized,
                source=source,
                metadata={"target_name": path_match.group(1)},
            )

        for alias, folder_key in self.KNOWN_FOLDER_ALIASES.items():
            if alias in normalized:
                return ParsedIntent(
                    IntentType.OPEN_FOLDER,
                    raw_text,
                    normalized,
                    source=source,
                    metadata={"target_name": folder_key},
                )

        generic_target = self._extract_bare_open_target(raw_text, normalized)
        if generic_target is not None:
            return ParsedIntent(
                IntentType.OPEN_FOLDER,
                raw_text,
                normalized,
                source=source,
                metadata={"target_name": generic_target},
            )

        return None

    def _parse_app_intent_open(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        return self._parse_app_intent(raw_text, normalized, source, close=False)

    def _parse_app_intent_close(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        return self._parse_app_intent(raw_text, normalized, source, close=True)

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
                    IntentType.OPEN_YOUTUBE if alias == "youtube" else IntentType.OPEN_WEBSITE,
                    raw_text,
                    normalized,
                    source=source,
                    metadata={"url": url, "label": alias},
                )

        url_match = re.search(
            r"(https?://\S+|file:///\S+|www\.\S+\.\S+|\b[a-z0-9-]+\.[a-z]{2,}(?:/\S*)?\b)",
            raw_text,
            flags=re.IGNORECASE,
        )
        if url_match is None:
            url_match = re.search(
                r"(https?://\S+|file:///\S+|www\.\S+\.\S+|\b[a-z0-9-]+\.[a-z]{2,}(?:/\S*)?\b)",
                normalized,
                flags=re.IGNORECASE,
            )
        normalized_url_candidate = ""
        if url_match:
            normalized_url_candidate = re.sub(
                r"(?i)^(https?://|file:///|www\.)",
                "",
                url_match.group(1).lower(),
            )
        if url_match and (
            any(token in normalized for token in ("khol", "open", "launch"))
            or (source == "voice" and normalized == normalized_url_candidate)
        ):
            url = url_match.group(1)
            if url.lower().startswith("www."):
                url = f"https://{url}"
            elif not re.match(r"(?i)^(https?://|file:///)", url):
                url = f"https://{url}"
            return ParsedIntent(
                IntentType.OPEN_WEBSITE,
                raw_text,
                normalized,
                source=source,
                metadata={"url": url, "label": url},
            )
        return None

    def _parse_contextual_rename(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if not any(
            token in normalized for token in ("naam badal", "naam change", "rename", "badlo")
        ):
            return None
        target_kind = ""
        if "is file" in normalized:
            target_kind = "file"
        elif "is folder" in normalized:
            target_kind = "folder"
        if not target_kind:
            return None
        new_name = self._extract_contextual_new_name(raw_text, normalized)
        if not new_name:
            return None
        metadata = {
            "new_name": new_name,
            "path_kind": target_kind,
            f"use_active_{target_kind}_context": "true",
        }
        return ParsedIntent(
            IntentType.RENAME_PATH,
            raw_text,
            normalized,
            source=source,
            metadata=metadata,
        )

    def _parse_contextual_move(
        self,
        raw_text: str,
        normalized: str,
        source: str,
    ) -> ParsedIntent | None:
        if re.search(r"(?i)\b(?:move|shift|le ja|bhej)\b", normalized) is None:
            return None
        target_kind = ""
        if "is file" in normalized:
            target_kind = "file"
        elif "is folder" in normalized:
            target_kind = "folder"
        if not target_kind:
            return None
        destination_name = self._extract_contextual_destination(raw_text, normalized)
        if not destination_name:
            return None
        metadata = {
            "destination_name": destination_name,
            "path_kind": target_kind,
            f"use_active_{target_kind}_context": "true",
        }
        return ParsedIntent(
            IntentType.MOVE_PATH,
            raw_text,
            normalized,
            source=source,
            metadata=metadata,
        )

    @classmethod
    def _extract_search_query(cls, raw_text: str) -> str | None:
        quoted = cls._extract_quoted_names(raw_text)
        if quoted:
            return quoted[0]
        reverse_match = re.search(
            r"(?i)page\s+par\s+(.+?)\s+(?:search|find|dhundo)\b",
            raw_text,
        )
        if reverse_match:
            return reverse_match.group(1).strip(" .")
        match = re.search(r"(?i)(?:search|find|dhundo)\s+(.+?)(?:\s+on|\s+par|\s*$)", raw_text)
        if match:
            candidate = match.group(1).strip(" .")
            if candidate.lower() not in {"karo", "karo na", "please"}:
                return candidate
        return None

    @classmethod
    def _extract_playlist_query(cls, raw_text: str) -> str | None:
        quoted = cls._extract_quoted_names(raw_text)
        if quoted:
            return quoted[0]
        cleaned = re.sub(
            r"(?i)\b(ava|youtube|playlist|play|chalao|chala|par|pa|on|please|open|launch|kholo|aur|and)\b",
            "",
            raw_text,
        )
        cleaned = " ".join(cleaned.split()).strip(" -:")
        return cleaned or None

    @classmethod
    def _extract_youtube_search_query(cls, raw_text: str) -> str | None:
        quoted = cls._extract_quoted_names(raw_text)
        if quoted:
            return quoted[0]
        reverse_match = re.search(
            r"(?i)youtube(?:\s+(?:par|pa|pe|mein|me|kholo|open|launch))?(?:\s+(?:aur|and))?\s+(.+?)\s+(?:search|find|dhundo)\b",
            raw_text,
        )
        if reverse_match:
            candidate = reverse_match.group(1).strip(" .")
            candidate = re.sub(r"(?i)\b(kholo|open|launch|aur|and)\b", "", candidate)
            candidate = " ".join(candidate.split()).strip(" -:")
            if candidate:
                return candidate
        cleaned = re.sub(
            (
                r"(?i)\b("
                r"ava|youtube|search|find|dhundo|karo|please|par|pa|on|open|launch|"
                r"kholo|aur|and|khul|gaya|hui|hua|nahi|but|woh|wala"
                r")\b"
            ),
            "",
            raw_text,
        )
        cleaned = " ".join(cleaned.split()).strip(" -:")
        return cleaned or None

    @staticmethod
    def _extract_quoted_names(raw_text: str) -> list[str]:
        return [match.strip() for match in re.findall(r"['\"]([^'\"]+)['\"]", raw_text)]

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

            before = re.sub(
                r"(?i)\b(create|new|please|ava|banao|bana do|open|khol)\b",
                "",
                before,
            ).strip()
            after = re.sub(
                r"(?i)\b(create|new|please|ava|banao|bana do|ke andar|open|khol)\b",
                "",
                after,
            )
            after = after.strip(" -:")

            candidate = before or after
            candidate = candidate.strip()
            if candidate:
                return candidate
        return None

    @classmethod
    def _extract_bare_open_target(cls, raw_text: str, normalized: str) -> str | None:
        patterns = (
            r"(?i)^\s*(.+?)\s+(?:khol(?:o)?|open|show|go to)\s*$",
            r"(?i)^(?:open|show|go to)\s+(.+?)\s*$",
        )
        for text in (raw_text, normalized):
            for pattern in patterns:
                match = re.search(pattern, text)
                if match is None:
                    continue
                candidate = cls._clean_spoken_target(match.group(1))
                if not candidate:
                    continue
                lowered = candidate.lower()
                if "://" in lowered or re.search(r"\b[a-z0-9-]+\.[a-z]{2,}(?:/\S*)?\b", lowered):
                    return None
                if lowered in {"browser", "website", "tab", "page", "address bar"}:
                    return None
                if lowered in cls.APP_ALIASES or lowered in cls.WEBSITE_ALIASES:
                    return None
                if lowered in cls.KNOWN_FOLDER_ALIASES:
                    return lowered
                if any(
                    alias in lowered
                    for alias in (
                        *cls.APP_ALIASES.keys(),
                        *cls.WEBSITE_ALIASES.keys(),
                    )
                ):
                    return None
                return candidate
        return None

    @classmethod
    def _extract_contextual_new_name(cls, raw_text: str, normalized: str) -> str | None:
        patterns = (
            (
                r"(?i)is\s+(?:file|folder)\s+ka\s+naam\s+"
                r"(?:badlo|badal do|change karo|rename karo)\s+(.+)$"
            ),
            r"(?i)is\s+(?:file|folder)\s+(?:badlo|badal do|change karo|rename karo)\s+(.+)$",
            r"(?i)rename\s+(?:this|is)\s+(?:file|folder)\s+to\s+(.+)$",
        )
        for text in (raw_text, normalized):
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    candidate = cls._clean_spoken_name(match.group(1))
                    if candidate:
                        return candidate
        return None

    @classmethod
    def _extract_contextual_destination(cls, raw_text: str, normalized: str) -> str | None:
        quoted = cls._extract_quoted_names(raw_text)
        if quoted:
            return quoted[0]

        path_match = re.search(r"([a-zA-Z]:\\[^\"']+)", raw_text)
        if path_match:
            return path_match.group(1)

        for alias, folder_key in cls.KNOWN_FOLDER_ALIASES.items():
            if alias in normalized:
                return folder_key

        for text in (raw_text, normalized):
            match = re.search(
                (
                    r"(?i)is\s+(?:file|folder)\s+ko\s+(.+?)\s+"
                    r"m(?:e|ein)\s+(?:move|shift|bhej|le ja)\w*"
                ),
                text,
            )
            if match:
                candidate = cls._clean_spoken_target(match.group(1))
                if candidate:
                    return candidate
        return None

    @staticmethod
    def _clean_spoken_target(text: str) -> str:
        cleaned = re.sub(
            r"(?i)\b(please|abhi|yahan|folder|file|ka|ko|me|mein|into)\b",
            "",
            text,
        )
        cleaned = " ".join(cleaned.split()).strip(" .-:")
        return cleaned

    @staticmethod
    def _clean_spoken_name(text: str) -> str:
        cleaned = re.sub(r"(?i)\b(please|abhi|yahan)\b", "", text)
        cleaned = " ".join(cleaned.split()).strip(" .-:")
        return cleaned

    @classmethod
    def _normalize_text(cls, raw_text: str) -> str:
        normalized = " ".join(raw_text.lower().split())
        normalized = re.sub(r"<[^>]+>", " ", normalized)
        normalized = re.sub(r"\[[^\]]+\]", " ", normalized)
        normalized = " ".join(normalized.split())
        for pattern, replacement in cls.NORMALIZATION_REPLACEMENTS:
            normalized = re.sub(pattern, replacement, normalized)
        normalized = re.sub(r"\b([a-z0-9-]+)\s+dot\s+([a-z]{2,})(?=\b)", r"\1.\2", normalized)
        normalized = re.sub(r"\b([a-z0-9-]+)\.\s+([a-z]{2,})(?=\b)", r"\1.\2", normalized)
        normalized = re.sub(r"\.(?=\s|$)", "", normalized)
        return normalized
