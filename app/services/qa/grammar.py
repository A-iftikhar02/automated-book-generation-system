"""Spelling, grammar, punctuation and style checks via a self-hosted LanguageTool server (see docker-compose.yml)."""

import logging
import re

import httpx

from ...config import settings
from .base import Issue, excerpt_around
from .rules import US_UK

logger = logging.getLogger(__name__)

CHUNK_CHARS = 12_000

# LanguageTool category id -> our category
CATEGORY_MAP = {
    "TYPOS": "spelling",
    "COMPOUNDING": "spelling",
    "GRAMMAR": "grammar",
    "MISC": "grammar",
    "PUNCTUATION": "punctuation",
    "TYPOGRAPHY": "typography",
    "CASING": "capitalization",
    "CONFUSED_WORDS": "word_choice",
    "COLLOCATIONS": "word_choice",
    "NONSTANDARD_PHRASES": "word_choice",
    "SEMANTICS": "logic",
    "REDUNDANCY": "redundancy",
    "STYLE": "style",
    "PLAIN_ENGLISH": "style",
    "REPETITIONS_STYLE": "repetition",
    "GENDER_NEUTRALITY": "style",
    "AMERICAN_ENGLISH_STYLE": "style",
    "BRITISH_ENGLISH": "spelling",
}

SEVERITY_BY_ISSUE_TYPE = {
    "misspelling": "major",
    "grammar": "major",
    "duplication": "major",
    "locale-violation": "minor",
    "typographical": "minor",
    "whitespace": "minor",
    "inconsistency": "minor",
    "style": "minor",
    "register": "info",
    "uncategorized": "minor",
}

# Rules that are noisy for fiction or duplicated by our own typography/style checks.
DISABLED_RULES = [
    "EN_QUOTES",
    "DASH_RULE",
    "EN_UNPAIRED_QUOTES",
    "EN_UNPAIRED_BRACKETS",
    "TOO_LONG_SENTENCE",
    "TOO_LONG_PARAGRAPH",
    "WHITESPACE_RULE",
    "ELLIPSIS",
    "THREE_NN",
    "SENTENCE_FRAGMENT",
    "EN_REPEATEDWORDS_SAY",
]
POETRY_DISABLED_RULES = ["UPPERCASE_SENTENCE_START", "PUNCTUATION_PARAGRAPH_END", "SENT_START_CONJUNCTIVE_LINKING_ADVERB_COMMA"]


class LanguageToolUnavailable(RuntimeError):
    pass


_LOCALE_PATTERNS = [
    (r"our(?=s?$|ed$|ing$|ite|able|ful)", "or"), (r"is(?=e$|es$|ed$|ing$|ation)", "iz"), (r"ys(?=e$|es$|ed$|ing$)", "yz"),
    (r"tre(?=s?$)", "ter"), (r"bre(?=s?$)", "ber"), (r"ll(?=ed$|ing$|er$|ers$|ery$)", "l"), (r"ence(?=s?$)", "ense"),
    (r"ogue(?=s?$)", "og"), (r"ae", "e"), (r"oe(?=[a-z])", "e"), (r"grey", "gray"), (r"mme(?=s?$)", "m"),
    (r"ement(?=s?$)", "ment"),
]


def _locale_key(word: str) -> str:
    w = word.lower()
    for pattern, repl in _LOCALE_PATTERNS:
        w = re.sub(pattern, repl, w)
    return w


def _is_locale_variant(word: str, replacements: list[str]) -> bool:
    """True when the flagged word is a correct spelling in another English locale (harbour vs harbor)."""
    w = word.lower()
    for us, uk in US_UK:
        for a in (us, uk):
            if w.startswith(a) and w[len(a):] in ("", "s", "ed", "ing", "ite", "ites", "able"):
                return True
    key = _locale_key(w)
    return any(r.lower() != w and _locale_key(r) == key for r in replacements)


def is_available() -> bool:
    try:
        r = httpx.get(f"{settings.LANGUAGETOOL_URL.rstrip('/')}/v2/languages", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _chunks(text: str) -> list[tuple[int, str]]:
    """Split text at paragraph boundaries into chunks of at most CHUNK_CHARS, keeping absolute offsets."""
    chunks: list[tuple[int, str]] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_CHARS)
        if end < len(text):
            cut = text.rfind("\n\n", start, end)
            if cut > start:
                end = cut
        chunks.append((start, text[start:end]))
        start = end
    return chunks


def check(text: str, *, language: str, ignore_words: set[str], poetry: bool = False) -> list[Issue]:
    url = f"{settings.LANGUAGETOOL_URL.rstrip('/')}/v2/check"
    disabled = DISABLED_RULES + (POETRY_DISABLED_RULES if poetry else [])
    issues: list[Issue] = []
    with httpx.Client(timeout=90) as client:
        for base, chunk in _chunks(text):
            try:
                resp = client.post(
                    url,
                    data={"text": chunk, "language": language, "level": "picky", "disabledRules": ",".join(disabled)},
                )
                resp.raise_for_status()
            except Exception as e:
                raise LanguageToolUnavailable(f"LanguageTool request failed: {e}") from e
            for m in resp.json().get("matches", []):
                start = base + m["offset"]
                end = start + m["length"]
                matched = text[start:end]
                rule = m.get("rule", {})
                issue_type = rule.get("issueType", "uncategorized")
                category = CATEGORY_MAP.get(rule.get("category", {}).get("id", ""), "grammar")
                severity = SEVERITY_BY_ISSUE_TYPE.get(issue_type, "minor")
                if issue_type == "misspelling":
                    category = "spelling"
                    # Invented names and world terms are not typos.
                    if matched.lower() in ignore_words or matched.strip("'’").lower() in ignore_words:
                        continue
                    # A valid spelling in another English locale (colour vs color) is a consistency issue, not a typo.
                    if _is_locale_variant(matched, [r["value"] for r in m.get("replacements", [])[:5]]):
                        category, severity = "consistency", "minor"
                replacements = [r["value"] for r in m.get("replacements", [])[:5]]
                issues.append(
                    Issue(
                        category=category,
                        check=f"lt:{rule.get('id', 'UNKNOWN')}",
                        severity=severity,
                        source="languagetool",
                        message=m.get("message") or rule.get("description", "Possible problem"),
                        excerpt=excerpt_around(text, start, end),
                        suggestion=f"Replace with: {', '.join(replacements)}" if replacements else None,
                        offset=start,
                        length=end - start,
                        matched=matched,
                        replacements=replacements,
                    )
                )
    return issues
