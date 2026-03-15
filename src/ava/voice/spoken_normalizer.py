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
        (r"\bhip\s*hop\b", "hip hop"),
        (r"\bhi\s*p\s*hop\b", "hip hop"),
        (r"\bplay\s*list\b", "playlist"),
        (r"\bsho\s*w\b", "show"),
        (r"\bcur\s*rent\b", "current"),
        (r"\bti\s*tle\b", "title"),
        (r"\bsear\s*ch\b", "search"),
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

    def interpret(self, raw_text: str, *, intent_router: IntentRouter) -> SpokenInterpretation:
        normalized_text = self._normalize_text(raw_text)
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
