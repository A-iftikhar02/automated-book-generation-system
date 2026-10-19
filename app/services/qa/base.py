import hashlib
import re
from dataclasses import dataclass, field

SEVERITY_WEIGHTS = {"critical": 15.0, "major": 4.0, "minor": 1.0, "info": 0.0}
SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2, "info": 3}


@dataclass
class Issue:
    category: str
    check: str
    severity: str
    message: str
    source: str = "rule"
    excerpt: str | None = None
    suggestion: str | None = None
    offset: int | None = None
    length: int | None = None
    matched: str | None = None
    replacements: list[str] = field(default_factory=list)
    chapter_number: int | None = None

    def fingerprint(self) -> str:
        """Stable identity across QA runs, used to keep ignored issues ignored.

        AI issues anchor on the model's quoted excerpt (the located span can drift after edits);
        rule/LanguageTool issues anchor on the exact matched text."""
        anchor = (self.excerpt if self.source == "ai" else self.matched) or self.excerpt or self.message or ""
        anchor = re.sub(r"\W+", " ", anchor.lower()).strip()
        raw = f"{self.chapter_number}|{self.check}|{anchor}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def excerpt_around(text: str, start: int, end: int, radius: int = 45) -> str:
    a = max(0, start - radius)
    b = min(len(text), end + radius)
    snippet = text[a:b].replace("\n", " ")
    return ("…" if a > 0 else "") + snippet.strip() + ("…" if b < len(text) else "")


def span_issue(text: str, start: int, end: int, **kwargs) -> Issue:
    """Issue anchored to an exact span of the chapter text."""
    return Issue(
        offset=start,
        length=end - start,
        matched=text[start:end],
        excerpt=excerpt_around(text, start, end),
        **kwargs,
    )
