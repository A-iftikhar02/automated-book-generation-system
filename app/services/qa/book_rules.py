"""Cross-chapter checks: length vs. format, balance, duplicated passages, name/spelling/hyphenation consistency,
repeated chapter openings, and title/metadata problems that stores reject."""

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass

from rapidfuzz import fuzz

from ...catalog import Category
from ...db.models import Book
from ..text import paragraphs, sentences, word_count, words
from .base import Issue, excerpt_around
from .rules import STOPWORDS, US_UK, spelling_variants_in


@dataclass
class PartText:
    number: int
    title: str
    content: str


TITLE_BANNED = re.compile(
    r"\b(?:best\s*sell(?:er|ing)|#1|free|kindle|ebook|e-book|bonus|sale|discount|book\s*\d+\s*of|volume\s*\d+|vol\.?\s*\d+|"
    r"limited time|new release|award[- ]winning)\b",
    re.IGNORECASE,
)


def check_length(book: Book, category: Category, parts: list[PartText], outline_count: int) -> list[Issue]:
    out: list[Issue] = []
    total = sum(word_count(p.content) for p in parts)
    if len(parts) < outline_count:
        out.append(Issue(category="structure", check="missing_parts", severity="critical",
                         message=f"Only {len(parts)} of {outline_count} {category.part_label.lower()}s are written."))
    if total < category.min_words:
        sev = "critical" if total < 0.7 * category.min_words else "major"
        out.append(Issue(category="structure", check="below_format_length", severity=sev,
                         message=f"{total:,} words is below the {category.label} range ({category.min_words:,}-{category.max_words:,}). "
                                 "Readers check page counts and leave '1-star: too short' reviews.",
                         suggestion="Add parts, extend thin chapters, or change the category."))
    elif total > category.max_words:
        out.append(Issue(category="structure", check="above_format_length", severity="minor",
                         message=f"{total:,} words is above the typical {category.label} range (max {category.max_words:,})."))
    if category.structure in ("chapters",) and len(parts) >= 4:
        counts = [word_count(p.content) for p in parts]
        median = statistics.median(counts)
        for p, c in zip(parts, counts):
            if c < 0.4 * median:
                out.append(Issue(category="structure", check="unbalanced_length", severity="minor", chapter_number=p.number,
                                 message=f"{category.part_label} {p.number} has {c:,} words versus a median of {int(median):,}."))
    titles = Counter(p.title.strip().lower() for p in parts if p.title.strip())
    for t, c in titles.items():
        if c > 1 and category.structure != "scenes":
            out.append(Issue(category="structure", check="duplicate_titles", severity="minor",
                             message=f"The title '{t}' is used by {c} parts."))
    return out


def _shingles(tokens: list[str], n: int = 6) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def check_duplicates(parts: list[PartText]) -> list[Issue]:
    """Exact repeated sentences and near-duplicate paragraphs (within and across parts)."""
    out: list[Issue] = []
    seen_sentences: dict[str, int] = {}
    reported = 0
    for p in parts:
        for s in sentences(p.content):
            if word_count(s) < 12:
                continue
            key = re.sub(r"\W+", " ", s.lower()).strip()
            if key in seen_sentences and reported < 20:
                reported += 1
                first = seen_sentences[key]
                where = "earlier in the same part" if first == p.number else f"in part {first}"
                out.append(Issue(category="repetition", check="duplicate_sentence", severity="major", chapter_number=p.number,
                                 message=f"This sentence also appears {where}.", excerpt=s[:200]))
            else:
                seen_sentences.setdefault(key, p.number)

    paras: list[tuple[int, str, list[str]]] = []
    for p in parts:
        for para in paragraphs(p.content):
            toks = [w.lower() for w in words(para)]
            if len(toks) >= 40:
                paras.append((p.number, para, toks))
    index: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for i, (_, _, toks) in enumerate(paras):
        for sh in _shingles(toks):
            index[sh].append(i)
    pair_hits: Counter = Counter()
    for ids in index.values():
        if 1 < len(ids) <= 20:
            uniq = sorted(set(ids))
            for a_i in range(len(uniq)):
                for b_i in range(a_i + 1, len(uniq)):
                    pair_hits[(uniq[a_i], uniq[b_i])] += 1
    found = 0
    for (a, b), hits in pair_hits.most_common():
        if hits < 3 or found >= 15:
            break
        ratio = fuzz.ratio(paras[a][1], paras[b][1])
        if ratio >= 75:
            found += 1
            out.append(Issue(category="repetition", check="near_duplicate_passage", severity="major", chapter_number=paras[b][0],
                             message=f"Passage is {int(ratio)}% similar to a passage in part {paras[a][0]} (repeated scene or recycled text).",
                             excerpt=paras[b][1][:200]))
    return out


def check_book_phrases(parts: list[PartText]) -> list[Issue]:
    out: list[Issue] = []
    gram_parts: dict[tuple[str, ...], set[int]] = defaultdict(set)
    gram_count: Counter = Counter()
    for p in parts:
        toks = [w.lower() for w in words(p.content)]
        for i in range(len(toks) - 4):
            g = tuple(toks[i : i + 5])
            if sum(1 for t in g if t not in STOPWORDS) >= 2:
                gram_count[g] += 1
                gram_parts[g].add(p.number)
    for g, c in gram_count.most_common(30):
        if c >= 6 and len(gram_parts[g]) >= 3:
            out.append(Issue(category="repetition", check="signature_phrase", severity="minor",
                             message=f"'{' '.join(g)}' appears {c} times across {len(gram_parts[g])} parts."))
    if len(parts) >= 4:
        openings = [(p.number, " ".join(words(p.content)[:10]).lower()) for p in parts]
        endings = [(p.number, " ".join(words(p.content)[-10:]).lower()) for p in parts]
        for label, items in (("opening", openings), ("ending", endings)):
            similar = 0
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    if fuzz.ratio(items[i][1], items[j][1]) > 70:
                        similar += 1
            if similar >= 2:
                out.append(Issue(category="repetition", check=f"formulaic_{label}s", severity="minor",
                                 message=f"Several parts have near-identical {label} lines; the book feels formulaic."))
    return out


def _proper_nouns(parts: list[PartText]) -> Counter:
    counts: Counter = Counter()
    for p in parts:
        for s in sentences(p.content):
            toks = re.findall(r"[A-Za-z][\w’'-]*", s)
            for t in toks[1:]:  # skip sentence-initial capitals
                if t[0].isupper() and len(t) >= 3 and t.lower() not in STOPWORDS and not t.isupper():
                    counts[t.strip("’'")] += 1
    return counts


def check_names(parts: list[PartText], bible: dict) -> list[Issue]:
    out: list[Issue] = []
    counts = _proper_nouns(parts)
    canonical = {str(c.get("name", "")).split()[0] for c in bible.get("characters", []) if isinstance(c, dict) and c.get("name")}
    canonical |= {str(s.get("name", "")).split()[0] for s in bible.get("settings", []) if isinstance(s, dict) and s.get("name")}
    canonical = {c for c in canonical if c}
    frequent = [n for n, c in counts.items() if c >= 5] + list(canonical)
    reported: set[tuple[str, str]] = set()
    for rare, rc in counts.items():
        if rc > 3 or len(rare) < 4:
            continue
        for main in frequent:
            if main == rare or len(main) < 4 or main.lower() == rare.lower():
                continue
            if rare.rstrip("s") == main or main.rstrip("s") == rare:
                continue
            if fuzz.ratio(rare.lower(), main.lower()) >= 80 and (main, rare) not in reported:
                reported.add((main, rare))
                where = [p.number for p in parts if re.search(rf"\b{re.escape(rare)}\b", p.content)]
                out.append(Issue(category="consistency", check="name_variant", severity="major",
                                 chapter_number=where[0] if len(where) == 1 else None,
                                 message=f"'{rare}' ({rc}×) looks like a misspelling of '{main}' (parts {', '.join(map(str, where[:6]))}).",
                                 suggestion=f"Use '{main}' consistently."))
    for main in canonical:
        if main and main not in counts and not any(main in p.content for p in parts):
            out.append(Issue(category="consistency", check="bible_name_missing", severity="info",
                             message=f"'{main}' is in the story bible but never appears in the text."))
    return out[:25]


def check_spelling_consistency(parts: list[PartText], language: str) -> list[Issue]:
    out: list[Issue] = []
    full = "\n".join(p.content for p in parts)
    found = spelling_variants_in(full)
    us_book = language.lower().startswith("en-us")
    uk_book = language.lower() in ("en-gb", "en-au", "en-nz", "en-za")
    for us, uk in US_UK:
        u, k = found.get(us, 0), found.get(uk, 0)
        if u and k:
            out.append(Issue(category="consistency", check="mixed_spelling_variants", severity="minor",
                             message=f"Both '{us}' ({u}×) and '{uk}' ({k}×) spellings are used.",
                             suggestion=f"Use '{us if us_book else uk}' throughout."))
        elif us_book and k and us not in ("toward", "mom"):
            out.append(Issue(category="consistency", check="locale_spelling", severity="minor",
                             message=f"British spelling '{uk}' ({k}×) in a US-English book.", suggestion=f"Use '{us}'."))
        elif uk_book and u and us not in ("toward",):
            out.append(Issue(category="consistency", check="locale_spelling", severity="minor",
                             message=f"American spelling '{us}' ({u}×) in a British-English book.", suggestion=f"Use '{uk}'."))
    lower = full.lower()
    hyphenated = Counter(m.group(0) for m in re.finditer(r"\b[a-z]{2,}-[a-z]{2,}\b", lower))
    for hw, c in hyphenated.items():
        closed = hw.replace("-", "")
        spaced = hw.replace("-", " ")
        cc = len(re.findall(rf"\b{closed}\b", lower))
        if cc:
            out.append(Issue(category="consistency", check="hyphenation_inconsistency", severity="minor",
                             message=f"'{hw}' ({c}×) and '{closed}' ({cc}×) are both used.", suggestion="Pick one form."))
        elif len(re.findall(rf"\b{spaced}\b", lower)) >= 2 and c >= 2 and hw.split("-")[0] not in STOPWORDS:
            out.append(Issue(category="consistency", check="hyphenation_inconsistency", severity="info",
                             message=f"'{hw}' is sometimes written as '{spaced}'. Check whether the compound should be hyphenated consistently."))
    return out[:25]


def check_terms_capitalization(parts: list[PartText], bible: dict) -> list[Issue]:
    out: list[Issue] = []
    terms = [g.get("term") for g in bible.get("glossary", []) if isinstance(g, dict) and g.get("term")]
    terms += [s.get("name") for s in bible.get("settings", []) if isinstance(s, dict) and s.get("name")]
    full = "\n".join(p.content for p in parts)
    for term in terms:
        term = str(term).strip()
        if not term or not term[0].isupper() or len(term) < 4:
            continue
        lower_hits = [m for m in re.finditer(rf"(?<=[a-z,;] ){re.escape(term.lower())}\b", full)]
        proper_hits = len(re.findall(rf"\b{re.escape(term)}\b", full))
        if lower_hits and proper_hits:
            out.append(Issue(category="consistency", check="term_capitalization", severity="minor",
                             message=f"'{term}' is capitalised {proper_hits}× but lowercase {len(lower_hits)}×.",
                             excerpt=excerpt_around(full, lower_hits[0].start(), lower_hits[0].end())))
    return out[:15]


def check_metadata(book: Book, category: Category) -> list[Issue]:
    out: list[Issue] = []
    for label, value in (("Title", book.title), ("Subtitle", book.subtitle or "")):
        if value and TITLE_BANNED.search(value):
            out.append(Issue(category="compliance", check="title_keyword_stuffing", severity="critical",
                             message=f"{label} contains a term stores prohibit (e.g. 'bestseller', 'free', 'Kindle', series numbering): "
                                     f"'{TITLE_BANNED.search(value).group(0)}'.",
                             suggestion="Remove it. Series info belongs in the series fields."))
    if len(book.title) + len(book.subtitle or "") > 200:
        out.append(Issue(category="compliance", check="title_too_long", severity="major",
                         message="Title + subtitle exceed KDP's 200-character limit."))
    if book.title.isupper() and len(book.title) > 6:
        out.append(Issue(category="compliance", check="title_all_caps", severity="minor",
                         message="Title is in ALL CAPS; stores ask for title case."))
    return out


def check_book(book: Book, category: Category, parts: list[PartText], outline_count: int, bible: dict) -> list[Issue]:
    issues: list[Issue] = []
    issues += check_length(book, category, parts, outline_count)
    issues += check_metadata(book, category)
    if category.structure != "poems":
        issues += check_duplicates(parts)
        issues += check_book_phrases(parts)
    if category.fiction:
        issues += check_names(parts, bible)
    issues += check_spelling_consistency(parts, book.language)
    issues += check_terms_capitalization(parts, bible)
    return issues
