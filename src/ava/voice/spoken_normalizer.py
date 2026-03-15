from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import urlparse

from ava.intents.models import IntentType, ParsedIntent
from ava.intents.router import IntentRouter


@dataclass(slots=True, frozen=True)
class SpokenInterpretation:
    raw_text: str
    normalized_text: str
    intent: ParsedIntent
    needs_confirmation: bool = False
    confirmation_prompt: str | None = None
    browser_like: bool = False


class SpokenCommandNormalizer:
    DOMAIN_ALIASES: ClassVar[dict[str, str]] = {
        "youtube": "youtube.com",
        "instagram": "instagram.com",
        "insta": "instagram.com",
        "github": "github.com",
        "openai": "openai.com",
        "python": "python.org",
        "whatsapp": "whatsapp.com",
        "google": "google.com",
        "gmail": "gmail.com",
    }
    WORD_REPLACEMENTS: tuple[tuple[str, str], ...] = (
        (r"\bo\s*pen\b", "open"),
        (r"\bpyt\s*hon\b", "python"),
        (r"\bpy\s*tho\s*n\b", "python"),
        (r"\bp\s*y\s*t\s*h\s*o\s*n\b", "python"),
        (r"\byou\s*tu\s*be\b", "youtube"),
        (r"\by\s*o\s*u\s*t\s*u\s*b\s*e\b", "youtube"),
        (r"\bin\s*sta\s*gram\b", "instagram"),
        (r"\bi\s*n\s*s\s*t\s*a\s*g\s*r\s*a\s*m\b", "instagram"),
        (r"\bwha\s*tsapp\b", "whatsapp"),
        (r"\bhu\s*b\b", "hub"),
        (r"\bgit\s*hub\b", "github"),
        (r"\bgi\s*t\s*hub\b", "github"),
        (r"\bgi\s*th\s*hub\b", "github"),
        (r"\bg\s*i\s*t\s*h\s*u\s*b\b", "github"),
        (r"\bopen\s*ai\b", "openai"),
        (r"\bopen\s*a\s*i\b", "openai"),
        (r"\bo\s*p\s*e\s*n\s*a\s*i\b", "openai"),
        (r"\blo\s*fi\b", "lofi"),
        (r"\blo\s*f[yi]\b", "lofi"),
        (r"\blop\s*f[yi]\b", "lofi"),
        (r"(?<!lofi\s)\bhi\s*p\s*hop\s+pla\s*y\s*list\b", "lofi hip hop playlist"),
        (r"\bhip\s*hop\b", "hip hop"),
        (r"\bhi\s*p\s*hop\b", "hip hop"),
        (r"\bp\s*a\s*r\b", "par"),
        (r"\bne\s*xt\b", "next"),
        (r"\bplay\s*list\b", "playlist"),
        (r"\bpla\s*y\s*list\b", "playlist"),
        (r"\bsho\s*w\b", "show"),
        (r"\bcur\s*rent\b", "current"),
        (r"\bti\s*tle\b", "title"),
        (r"\bsear\s*ch\b", "search"),
        (r"\bse\s*arch\b", "search"),
        (r"\bnote\s*pad\b", "notepad"),
        (r"\bno\s*te\s*pad\b", "notepad"),
        (r"\bno\s*te\s*pa\s*d\b", "notepad"),
        (r"\bcalcu\s*lator\b", "calculator"),
        (r"\bcal\s*cu\s*la\s*tor\b", "calculator"),
        (r"\bcal\s*cu\s*lator\b", "calculator"),
        (r"\bpa\s*int\b", "paint"),
        (r"\bdown\s*loads\b", "downloads"),
        (r"\bdown\s*load\s*s\b", "downloads"),
        (r"\bdocu\s*ments\b", "documents"),
        (r"\bdo\s*cu\s*ment\s*s\b", "documents"),
        (r"\bdesk\s*top\b", "desktop"),
        (r"\bdes\s*ktop\b", "desktop"),
        (r"\bfo\s*lder\b", "folder"),
        (r"\bfi\s*le\b", "file"),
        (r"\bis\s*up\b", "is app"),
        (r"\bmini\s*mize\b", "minimize"),
        (r"\bmin\s*imi\s*ze\b", "minimize"),
        (r"\bmaxi\s*mize\b", "maximize"),
        (r"\bmax\s*imi\s*ze\b", "maximize"),
        (r"\bwin\s*dow\b", "window"),
        (r"\bwi\s*ndow\b", "window"),
        (r"\bfo\s*cus\b", "focus"),
        (r"\bca\s*ro\b", "karo"),
        (r"\bco\s*ro\b", "karo"),
        (r"\bcolo\b", "kholo"),
        (r"\bholo\b", "kholo"),
    )
    DOT_TLDS: tuple[str, ...] = ("com", "org", "in", "net", "io", "ai", "app", "dev")
    TRUSTED_DOMAINS: frozenset[str] = frozenset(
        {
            "python.org",
            "youtube.com",
            "instagram.com",
            "github.com",
            "openai.com",
            "google.com",
            "gmail.com",
            "whatsapp.com",
        }
    )
    QUERY_INTENTS: frozenset[IntentType] = frozenset(
        {
            IntentType.SEARCH_PAGE,
            IntentType.SEARCH_YOUTUBE,
            IntentType.PLAY_YOUTUBE_PLAYLIST,
        }
    )
    QUERY_STOP_WORDS: frozenset[str] = frozenset(
        {
            "search",
            "find",
            "dhundo",
            "youtube",
            "page",
            "playlist",
            "play",
            "karo",
            "karo.",
            "par",
            "on",
            "open",
            "kholo",
        }
    )
    BROWSER_HINT_PATTERNS: ClassVar[tuple[str, ...]] = (
        r"\b(?:youtube|instagram|github|openai|python|google|gmail|whatsapp|browser)\b",
        r"\b(?:website|page|tab|title|url|address bar|search|playlist|kholo|open)\b",
        r"\.(?:com|org|in|net|io|ai|app|dev)\b",
        r"\bdot\s+(?:com|org|in|net|io|ai|app|dev)\b",
    )
    MODEL_DOMAIN_HINTS: ClassVar[dict[str, str]] = {
        "github": "github.com kholo",
        "youtube": "youtube kholo",
        "instagram": "instagram.com kholo",
        "openai": "openai.com kholo",
        "python": "python.org kholo",
        "google": "google.com kholo",
        "whatsapp web": "whatsapp web kholo",
    }

    def interpret(self, raw_text: str, *, intent_router: IntentRouter) -> SpokenInterpretation:
        normalized_text = self._normalize_text(raw_text)
        normalized_text = self._promote_compound_browser_command(
            raw_text,
            normalized_text,
        )
        normalized_text = self._promote_bare_open_target(normalized_text)
        browser_like = self.looks_browser_like(raw_text) or self.looks_browser_like(normalized_text)
        intent = intent_router.parse(normalized_text, source="voice")
        normalized_text, intent, domain_was_corrected = self._canonicalize_website_intent(
            normalized_text,
            intent,
            intent_router=intent_router,
        )
        if intent.intent_type is IntentType.GENERAL_COMMAND:
            return SpokenInterpretation(
                raw_text=raw_text,
                normalized_text=normalized_text,
                intent=intent,
                browser_like=browser_like,
            )

        confirmation_prompt = self._build_confirmation_prompt(
            raw_text,
            normalized_text,
            intent,
            domain_was_corrected=domain_was_corrected,
        )
        return SpokenInterpretation(
            raw_text=raw_text,
            normalized_text=normalized_text,
            intent=intent,
            needs_confirmation=confirmation_prompt is not None,
            confirmation_prompt=confirmation_prompt,
            browser_like=browser_like,
        )

    def recover_browser_command(
        self,
        *,
        raw_text: str,
        model_text: str,
        intent_router: IntentRouter,
    ) -> SpokenInterpretation | None:
        normalized_raw = self._normalize_text(raw_text)
        normalized_model = self._normalize_text(model_text)
        browser_like = self.looks_browser_like(raw_text) or self.looks_browser_like(
            normalized_model
        )
        if not browser_like:
            return None

        raw_intent = intent_router.parse(normalized_raw, source="voice")
        if self._looks_like_youtube_search(normalized_raw, normalized_model):
            youtube_query = (
                raw_intent.metadata.get("query")
                if raw_intent.intent_type
                in {IntentType.SEARCH_YOUTUBE, IntentType.PLAY_YOUTUBE_PLAYLIST}
                else None
            ) or self._extract_model_youtube_query(model_text)
            if not youtube_query:
                return None
            normalized_command = (
                f"youtube par {youtube_query} search karo"
                if "search" in normalized_raw or "search" in normalized_model
                else f"youtube par {youtube_query} playlist chalao"
            )
            intent = intent_router.parse(normalized_command, source="voice")
            prompt = (
                f"Ye search query `{youtube_query}` sahi hai na?"
                if self._query_needs_confirmation(raw_text, normalized_command, youtube_query)
                else None
            )
            return SpokenInterpretation(
                raw_text=raw_text,
                normalized_text=normalized_command,
                intent=intent,
                needs_confirmation=prompt is not None,
                confirmation_prompt=prompt,
                browser_like=True,
            )

        for hint, normalized_command in self.MODEL_DOMAIN_HINTS.items():
            if hint not in normalized_model:
                continue
            intent = intent_router.parse(normalized_command, source="voice")
            domain = self._extract_domain(intent.metadata.get("url", ""))
            prompt = None
            if domain and domain not in re.findall(r"[a-z0-9.]+", self._normalize_text(raw_text)):
                prompt = f"Aap `{domain}` bol rahe the na?"
            return SpokenInterpretation(
                raw_text=raw_text,
                normalized_text=normalized_command,
                intent=intent,
                needs_confirmation=prompt is not None,
                confirmation_prompt=prompt,
                browser_like=True,
            )
        return None

    @staticmethod
    def _promote_bare_open_target(normalized_text: str) -> str:
        bare_target = normalized_text.strip(" .!?")
        if not bare_target:
            return normalized_text
        open_targets = (
            set(IntentRouter.APP_ALIASES)
            | set(IntentRouter.KNOWN_FOLDER_ALIASES)
            | set(IntentRouter.WEBSITE_ALIASES)
        )
        if bare_target in open_targets:
            return f"{bare_target} kholo"
        return normalized_text

    def looks_browser_like(self, text: str) -> bool:
        lowered = " ".join(text.lower().split())
        if re.search(rf"(^|\s)\.\s*(?:{'|'.join(self.DOT_TLDS)})\b", lowered):
            return True
        if re.search(rf"\bdot\s+(?:{'|'.join(self.DOT_TLDS)})\b", lowered):
            return True
        normalized = self._normalize_text(text)
        return any(re.search(pattern, normalized) for pattern in self.BROWSER_HINT_PATTERNS)

    @staticmethod
    def _looks_like_youtube_search(normalized_raw: str, normalized_model: str) -> bool:
        combined = f"{normalized_raw} {normalized_model}"
        return "youtube" in combined and any(
            token in combined for token in ("search", "playlist", "find", "dhundo")
        )

    def _canonicalize_website_intent(
        self,
        normalized_text: str,
        intent: ParsedIntent,
        *,
        intent_router: IntentRouter,
    ) -> tuple[str, ParsedIntent, bool]:
        if intent.intent_type is not IntentType.OPEN_WEBSITE:
            return normalized_text, intent, False
        domain = self._extract_domain(intent.metadata.get("url", ""))
        suggested_domain = self._resolve_domain_suggestion(domain)
        if not suggested_domain or suggested_domain == domain:
            return normalized_text, intent, False
        canonical_text = re.sub(
            rf"\b{re.escape(domain)}\b",
            suggested_domain,
            normalized_text,
            count=1,
        )
        return canonical_text, intent_router.parse(canonical_text, source="voice"), True

    def _normalize_text(self, raw_text: str) -> str:
        normalized = " ".join(raw_text.lower().split())
        for pattern, replacement in self.WORD_REPLACEMENTS:
            normalized = re.sub(pattern, replacement, normalized)
        normalized = re.sub(
            rf"\b([a-z0-9-]+)\s+dot\s+({'|'.join(self.DOT_TLDS)})(?=\b)",
            r"\1.\2",
            normalized,
        )
        normalized = re.sub(
            rf"\b([a-z0-9-]+)\.\s+({'|'.join(self.DOT_TLDS)})(?=\b)",
            r"\1.\2",
            normalized,
        )
        normalized = re.sub(r"\.(?=\s|$)", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        domain_match = re.fullmatch(
            r"(?:open\s+)?([a-z0-9-]+\.[a-z]{2,})(?:\s+website)?",
            normalized,
        )
        if domain_match:
            return f"{domain_match.group(1)} kholo"

        if "whatsapp web" in normalized and not any(
            token in normalized for token in ("open", "khol", "launch")
        ):
            return "whatsapp web kholo"

        return normalized

    @staticmethod
    def _promote_compound_browser_command(raw_text: str, normalized_text: str) -> str:
        if "youtube" not in normalized_text:
            return normalized_text

        if any(token in normalized_text for token in ("search", "find", "dhundo")):
            query = IntentRouter._extract_youtube_search_query(  # type: ignore[attr-defined]
                normalized_text
            ) or IntentRouter._extract_youtube_search_query(raw_text)
            if query:
                return f"youtube par {query} search karo"

        if any(token in normalized_text for token in ("playlist", "play", "chalao", "chala")):
            query = IntentRouter._extract_playlist_query(  # type: ignore[attr-defined]
                normalized_text
            ) or IntentRouter._extract_playlist_query(raw_text)
            if query:
                return f"youtube par {query} playlist chalao"

        return normalized_text

    def _build_confirmation_prompt(
        self,
        raw_text: str,
        normalized_text: str,
        intent: ParsedIntent,
        *,
        domain_was_corrected: bool = False,
    ) -> str | None:
        if intent.intent_type is IntentType.OPEN_WEBSITE:
            domain = self._extract_domain(intent.metadata.get("url", ""))
            if domain_was_corrected and domain:
                return f"Aap `{domain}` bol rahe the na?"
            if domain and domain not in self.TRUSTED_DOMAINS:
                return f"Aap `{domain}` bol rahe the na?"
            return None

        if intent.intent_type not in self.QUERY_INTENTS:
            return None

        query = (intent.metadata.get("query") or "").strip()
        if not query:
            return None
        if self._query_needs_confirmation(raw_text, normalized_text, query):
            return f"Ye search query `{query}` sahi hai na?"
        return None

    def _query_needs_confirmation(
        self,
        raw_text: str,
        normalized_text: str,
        query: str,
    ) -> bool:
        query_terms = [term for term in re.findall(r"[a-z0-9]+", query.lower()) if term]
        if len(query_terms) <= 1:
            return False
        raw_terms = set(re.findall(r"[a-z0-9]+", raw_text.lower()))
        normalized_terms = set(re.findall(r"[a-z0-9]+", normalized_text.lower()))
        meaningful_terms = [
            term for term in query_terms if term not in self.QUERY_STOP_WORDS and len(term) > 1
        ]
        if len(meaningful_terms) <= 1:
            return False
        missing_terms = [term for term in meaningful_terms if term not in raw_terms]
        if missing_terms:
            return True
        return any(term not in raw_terms and term in normalized_terms for term in meaningful_terms)

    @staticmethod
    def _extract_domain(url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return parsed.netloc.lower()

    def _resolve_domain_suggestion(self, domain: str) -> str:
        if not domain or domain in self.TRUSTED_DOMAINS:
            return domain

        label, dot, tld = domain.partition(".")
        if not dot:
            return domain
        alias_target = self.DOMAIN_ALIASES.get(label)
        if alias_target and alias_target.endswith(f".{tld}"):
            return alias_target

        candidates = [trusted for trusted in self.TRUSTED_DOMAINS if trusted.endswith(f".{tld}")]
        if not candidates:
            return domain
        trusted_labels = {candidate.split(".", 1)[0]: candidate for candidate in candidates}
        direct_substring = next(
            (
                candidate
                for trusted_label, candidate in trusted_labels.items()
                if label in trusted_label or trusted_label in label
            ),
            None,
        )
        if direct_substring is not None:
            return direct_substring
        closest = difflib.get_close_matches(label, trusted_labels.keys(), n=1, cutoff=0.6)
        if closest:
            return trusted_labels[closest[0]]
        return domain

    @staticmethod
    def _extract_model_youtube_query(model_text: str) -> str | None:
        quoted_match = re.search(
            r'(?i)search(?:ing)?\s+["`]?(.+?)["`]?\s+(?:on|in)\s+youtube\b',
            model_text,
        )
        if quoted_match:
            return quoted_match.group(1).strip(" .")
        plain_match = re.search(
            r"(?i)youtube\s+search(?:ing)?\s+for\s+(.+?)(?:[.!?]|$)",
            model_text,
        )
        if plain_match:
            return plain_match.group(1).strip(" .")
        return None
