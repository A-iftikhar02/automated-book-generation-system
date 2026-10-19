"""Deterministic per-chapter checks: encoding, AI artifacts, typography, repetition, style, readability,
tense/POV drift, audience-appropriate language and store-compliance problems."""

import re
import statistics
from collections import Counter
from dataclasses import dataclass, field

import textstat

from ...catalog import AUDIENCES
from ..prompts import BANNED_PHRASES
from ..text import is_scene_break, paragraphs, sentences, word_count, words
from .base import Issue, excerpt_around, span_issue


@dataclass
class ChapterContext:
    number: int
    title: str
    target_words: int
    is_last: bool
    fiction: bool
    structure: str  # chapters | scenes | stories | poems
    audience: str
    content_rating: str
    pov: str
    tense: str
    language: str
    known_names: set[str] = field(default_factory=set)  # lower-cased


STOPWORDS = set(
    """a about above after again against all am an and any are as at be because been before being below between both but by
    can could did do does doing down during each few for from further had has have having he her here hers herself him himself
    his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours
    ourselves out over own same she should so some such than that the their theirs them themselves then there these they this
    those through to too under until up very was we were what when where which while who whom why will with would you your
    yours yourself yourselves said one back like into upon still even through around away again know get got make made""".split()
)

CLICHES = [
    "at the end of the day", "dead as a doornail", "in the nick of time", "avoid it like the plague", "cold as ice",
    "time will tell", "only time will tell", "every cloud has a silver lining", "fit as a fiddle", "scared to death",
    "all walks of life", "better late than never", "calm before the storm", "crystal clear", "dark and stormy night",
    "easier said than done", "few and far between", "heart of gold", "hit the ground running", "in the blink of an eye",
    "it goes without saying", "last but not least", "light at the end of the tunnel", "low-hanging fruit",
    "needle in a haystack", "noticeable by its absence", "on cloud nine", "plenty of fish in the sea",
    "quiet as a mouse", "read between the lines", "think outside the box", "tip of the iceberg", "under the weather",
    "white as a sheet", "worth its weight in gold", "all hell broke loose", "blood ran cold", "butterflies in her stomach",
    "butterflies in his stomach", "heart skipped a beat", "time stood still", "deafening silence", "fell on deaf ears",
    "frozen in place", "the rest is history", "a chill ran down", "let out a breath", "hung in the air",
    "the silence was deafening", "a wave of relief", "a pang of guilt", "jaw dropped", "rolled her eyes", "rolled his eyes",
]

SOFT_AI_TELLS = [
    "a mix of", "the weight of", "for what felt like an eternity", "something shifted", "a flicker of", "in that moment",
    "the silence stretched", "a wave of", "heart pounded", "jaw clenched", "a testament", "echoed through", "whispered secrets",
    "danced across", "her voice was barely", "his voice was barely", "the world seemed to", "it was as if", "an unspoken",
]

FILLER_WORDS = {"very", "really", "just", "quite", "rather", "somewhat", "actually", "basically", "literally", "totally",
                "completely", "simply", "suddenly", "somehow", "definitely", "certainly", "truly"}
FILTER_PHRASES = re.compile(
    r"\b(?:i|he|she|they|we)\s+(?:felt|saw|heard|noticed|realized|realised|watched|wondered|knew|thought|smelled|seemed)\b",
    re.IGNORECASE,
)
WEAK_VERB_RE = re.compile(r"\b(?:began|started|seemed|managed|proceeded)\s+to\b", re.IGNORECASE)
TELLING_RE = re.compile(
    r"\b(?:was|were|felt|feel|feels|am|is|are)\s+(?:so\s+|very\s+)?(?:angry|sad|happy|scared|afraid|nervous|excited|furious|"
    r"terrified|anxious|jealous|embarrassed|lonely|frustrated|annoyed|relieved|confused)\b",
    re.IGNORECASE,
)
LY_EXCEPTIONS = {
    "only", "family", "early", "likely", "reply", "supply", "belly", "ugly", "holy", "lonely", "lovely", "friendly", "silly",
    "jelly", "rally", "ally", "fly", "july", "italy", "emily", "lily", "sally", "molly", "holly", "bully", "curly", "daily",
    "weekly", "monthly", "yearly", "elderly", "costly", "deadly", "lively", "orderly", "unlikely", "apply", "rely", "imply",
    "comply", "multiply", "assembly", "anomaly", "butterfly", "dragonfly", "firefly", "gully", "chilly", "hilly", "wobbly",
    "ghostly", "kindly", "lowly", "manly", "queenly", "scholarly", "sickly", "smelly", "wily", "worldly", "bodily", "melancholy",
    "monopoly", "rely", "barely", "nearly", "hardly", "really", "finally", "actually", "suddenly", "simply", "probably",
}
SAID_BOOKISMS = {
    "exclaimed", "hissed", "growled", "snarled", "retorted", "quipped", "chortled", "interjected", "opined", "breathed",
    "purred", "barked", "spat", "snapped", "intoned", "declared", "ejaculated", "expostulated", "chided", "vociferated",
    "admonished", "sneered", "scoffed", "huffed", "gushed", "drawled",
}
PASSIVE_RE = re.compile(
    r"\b(?:am|is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?(?:\w+ed|known|seen|done|given|taken|made|written|told|found|held|"
    r"left|brought|built|caught|driven|eaten|forgotten|hidden|broken|chosen|shaken|stolen|thrown|worn|torn|born|kept|sent|"
    r"bought|thought|taught|lost|paid|sold|shot|struck|bound|drawn|grown|shown|spoken|woken|frozen|beaten|bitten)\b",
    re.IGNORECASE,
)
PROFANITY_MILD = re.compile(r"\b(?:damn(?:ed|it)?|hell|crap(?:py)?|bloody|bastards?|ass(?:es)?|arse|piss(?:ed)?|bugger)\b", re.IGNORECASE)
PROFANITY_STRONG = re.compile(
    r"\b(?:fuck\w*|motherfuck\w*|shit\w*|bullshit|bitch\w*|cunt\w*|dick(?:head)?s?|cock(?:sucker)?s?|pussy|twat|wanker)\b",
    re.IGNORECASE,
)
SLURS = re.compile(r"\b(?:n[i1]gg\w*|f[a@]gg?[o0]t\w*|r[e3]t[a@]rd(?:ed|s)?|ch[i1]nks?|sp[i1]cs?|k[i1]kes?|tr[a@]nn(?:y|ies))\b", re.IGNORECASE)
URL_RE = re.compile(r"\b(?:https?://|www\.)\S+|\b[\w.-]+\.(?:com|net|org|io|co|ai)\b(?:/\S*)?", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PHONE_RE = re.compile(r"\b(?:\+?\d{1,2}[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")
STORE_RE = re.compile(r"\b(?:amazon|kindle|apple books|ibooks|kobo|barnes\s*&\s*noble|nook|google play books|smashwords|audible)\b", re.IGNORECASE)
TRADEMARKS = re.compile(
    r"\b(?:iphone|ipad|google|facebook|instagram|tiktok|twitter|youtube|netflix|coca-cola|coke|pepsi|starbucks|mcdonald's|disney|"
    r"marvel|harry potter|star wars|lego|barbie|uber|tesla|xbox|playstation|nintendo|post-it|band-aid|kleenex|jacuzzi|velcro|"
    r"photoshop|zoom|chatgpt|openai)\b",
    re.IGNORECASE,
)
AI_META_RE = re.compile(
    r"\b(?:as an ai|as a language model|i cannot (?:fulfill|comply|continue)|i'm sorry, but i|here is (?:the|your|a) (?:chapter|story|revised|"
    r"rewritten|continuation)|here's (?:the|your|a) (?:chapter|story|revised|continuation)|word count|end of (?:chapter|story|scene)|"
    r"chapter summary|\[insert|\[placeholder|\[name\]|lorem ipsum|to be continued in the next|---content_start---)",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|TBD|FIXME|XXX)\b|\{\{.*?\}\}|\[\[.*?\]\]")
MOJIBAKE_RE = re.compile(r"â€[™œ\x9d“”˜¦\"]|Ã[©¨¢ ¶¼±§]|Â[ \xa0]")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f​-‍﻿]")
ACRONYM_OK = {"OK", "TV", "USA", "UK", "FBI", "CIA", "NASA", "DNA", "CEO", "GPS", "ATM", "ID", "AM", "PM", "SOS", "BC", "AD",
              "NYPD", "LAPD", "ER", "ICU", "MRI", "PDF", "USB", "AI", "NATO", "UN", "EU", "IV", "II", "III", "VI", "VII", "VIII",
              "IX", "XI", "XII"}
US_UK = [("color", "colour"), ("favorite", "favourite"), ("honor", "honour"), ("neighbor", "neighbour"), ("realize", "realise"),
         ("organize", "organise"), ("recognize", "recognise"), ("apologize", "apologise"), ("center", "centre"),
         ("theater", "theatre"), ("meter", "metre"), ("gray", "grey"), ("traveled", "travelled"), ("traveling", "travelling"),
         ("defense", "defence"), ("analyze", "analyse"), ("catalog", "catalogue"), ("labor", "labour"), ("humor", "humour"),
         ("armor", "armour"), ("rumor", "rumour"), ("odor", "odour"), ("flavor", "flavour"), ("behavior", "behaviour"),
         ("jewelry", "jewellery"), ("pajamas", "pyjamas"), ("mom", "mum"), ("toward", "towards"), ("aluminum", "aluminium"),
         ("plow", "plough"), ("cozy", "cosy"), ("skeptical", "sceptical"), ("fulfill", "fulfil"), ("canceled", "cancelled")]

QUOTED_RE = re.compile(r"“[^”]*”|\"[^\"\n]*\"")
PAST_MARKERS = re.compile(r"\b(?:was|were|had|did|said|went|looked|walked|felt|thought|knew|saw|came|took|turned|asked|stood|sat|ran)\b", re.I)
PRESENT_MARKERS = re.compile(r"\b(?:is|are|has|does|says|goes|looks|walks|feels|thinks|knows|sees|comes|takes|turns|asks|stands|sits|runs)\b", re.I)
FIRST_PERSON = re.compile(r"\b(?:I|me|my|mine|myself)\b")


def narration_only(text: str) -> str:
    """Remove quoted dialogue so tense/POV checks look at narration only."""
    return QUOTED_RE.sub(" ", text)


def _cap(issues: list[Issue], limit: int) -> list[Issue]:
    return issues[:limit]


def _per_1000(count: int, total_words: int) -> float:
    return count * 1000.0 / max(1, total_words)


def check_encoding(text: str) -> list[Issue]:
    out = []
    for m in re.finditer("�", text):
        out.append(span_issue(text, m.start(), m.end(), category="encoding", check="replacement_character", severity="critical",
                              message="Unicode replacement character (�): text was corrupted.", suggestion="Retype the affected word."))
    for m in MOJIBAKE_RE.finditer(text):
        out.append(span_issue(text, m.start(), m.end(), category="encoding", check="mojibake", severity="critical",
                              message="Garbled characters from a text-encoding error.", suggestion="Replace with the intended punctuation."))
    for m in CONTROL_RE.finditer(text):
        out.append(span_issue(text, m.start(), m.end(), category="encoding", check="invisible_character", severity="major",
                              message="Invisible control or zero-width character; can break ebook rendering and search.",
                              replacements=[""], suggestion="Remove it."))
    return _cap(out, 30)


def check_ai_artifacts(text: str, ctx: ChapterContext) -> list[Issue]:
    out = []
    for m in re.finditer(r"\*\*[^*]+\*\*|__[^_]+__", text):
        out.append(span_issue(text, m.start(), m.end(), category="ai_artifact", check="markdown_bold", severity="critical",
                              message="Markdown bold markers will appear as literal asterisks in the book.",
                              replacements=[m.group(0)[2:-2]], suggestion="Remove the markers."))
    for m in re.finditer(r"(?m)^#{1,6}\s+.*$", text):
        out.append(span_issue(text, m.start(), m.end(), category="ai_artifact", check="markdown_heading", severity="critical",
                              message="Markdown heading inside the body text.", suggestion="Remove the heading line."))
    for m in re.finditer(r"```|</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^<>]*)?>", text):
        out.append(span_issue(text, m.start(), m.end(), category="ai_artifact", check="code_or_html", severity="critical",
                              message="Code fence or HTML tag in the text.", replacements=[""], suggestion="Remove it."))
    for m in AI_META_RE.finditer(text):
        out.append(span_issue(text, m.start(), m.end(), category="ai_artifact", check="ai_meta_text", severity="critical",
                              message="Assistant/meta text left in the manuscript (a strong sign of AI generation that readers will notice).",
                              suggestion="Delete the meta commentary."))
    for m in PLACEHOLDER_RE.finditer(text):
        out.append(span_issue(text, m.start(), m.end(), category="ai_artifact", check="placeholder", severity="critical",
                              message="Placeholder text left in the manuscript.", suggestion="Replace with real content."))
    if ctx.structure != "poems":
        for m in re.finditer(r"(?m)^\s*(?:[-•]|\d+\.)\s+\S.*$", text):
            sev = "major" if ctx.fiction else "info"
            msg = ("List formatting inside fiction prose." if ctx.fiction
                   else "List line: renders as a plain paragraph in exports; make sure it reads well.")
            out.append(span_issue(text, m.start(), m.end(), category="formatting", check="list_formatting", severity=sev, message=msg))
    for p_match in re.finditer(r"(?im)^\s*chapter\s+(?:\d+|[ivxlc]+|one|two|three|four|five|six|seven|eight|nine|ten)\b.{0,60}$", text):
        if word_count(p_match.group(0)) <= 10:
            out.append(span_issue(text, p_match.start(), p_match.end(), category="ai_artifact", check="inline_chapter_heading",
                                  severity="major", message="A chapter heading appears inside the body; headings are added automatically.",
                                  replacements=[""], suggestion="Remove the line."))
    if not ctx.is_last and ctx.structure in ("chapters", "scenes"):
        for m in re.finditer(r"(?im)^\s*the end\.?\s*$", text):
            out.append(span_issue(text, m.start(), m.end(), category="structure", check="premature_the_end", severity="major",
                                  message="'The End' appears before the final part.", replacements=[""]))
    return _cap(out, 40)


def _smart_quote_issues(text: str) -> list[Issue]:
    out = []
    straight_d, curly_d = text.count('"'), text.count("“") + text.count("”")
    straight_s = len(re.findall(r"(?<=\w)'(?=\w)|(?<=\s)'|'(?=\s)", text))
    curly_s = text.count("’") + text.count("‘")
    if straight_d and curly_d:
        out.append(Issue(category="typography", check="mixed_double_quotes", severity="minor",
                         message=f"Mixed straight (\") and curly (“ ”) double quotes ({straight_d} straight, {curly_d} curly).",
                         suggestion="Run auto-fix to convert to curly quotes consistently."))
    elif straight_d:
        out.append(Issue(category="typography", check="straight_quotes", severity="info",
                         message="Straight double quotes used; professionally typeset books use curly quotes (“ ”).",
                         suggestion="Run auto-fix to convert to curly quotes."))
    if straight_s and curly_s:
        out.append(Issue(category="typography", check="mixed_apostrophes", severity="minor",
                         message=f"Mixed straight (') and curly (’) apostrophes/single quotes.",
                         suggestion="Run auto-fix to convert to curly apostrophes."))
    return out


def _balance_issues(text: str, ctx: ChapterContext) -> list[Issue]:
    out = []
    paras = paragraphs(text)
    cursor = 0
    for i, p in enumerate(paras):
        start = text.find(p, cursor)
        cursor = start + len(p) if start >= 0 else cursor
        opens, closes = p.count("“"), p.count("”")
        straight = p.count('"')
        next_opens_quote = i + 1 < len(paras) and paras[i + 1].lstrip()[:1] in ("“", '"')
        unbalanced = (opens != closes and not (opens == closes + 1 and next_opens_quote)) or (straight % 2 == 1 and not next_opens_quote)
        if unbalanced:
            out.append(Issue(category="punctuation", check="unbalanced_quotes", severity="minor",
                             message="Quotation marks don't balance in this paragraph (missing opening or closing quote).",
                             excerpt=excerpt_around(text, max(0, start), max(0, start) + min(len(p), 120)), offset=start if start >= 0 else None))
        if p.count("(") != p.count(")") or p.count("[") != p.count("]"):
            out.append(Issue(category="punctuation", check="unbalanced_brackets", severity="minor",
                             message="Parentheses or brackets don't balance in this paragraph.",
                             excerpt=excerpt_around(text, max(0, start), max(0, start) + min(len(p), 120)), offset=start if start >= 0 else None))
    return _cap(out, 15)


def check_typography(text: str, ctx: ChapterContext) -> list[Issue]:
    out: list[Issue] = []
    for m in re.finditer(r"(?<=\S)  +(?=\S)", text):
        out.append(span_issue(text, m.start(), m.end(), category="typography", check="double_space", severity="minor",
                              message="Multiple spaces between words.", replacements=[" "]))
    for m in re.finditer(r"(?<=\w) +(?=[,.;:!?](?:\s|$))", text):
        out.append(span_issue(text, m.start(), m.end(), category="typography", check="space_before_punctuation", severity="minor",
                              message="Space before punctuation.", replacements=[""]))
    for m in re.finditer(r"(?<=[a-z]{2})([,;:])(?=[A-Za-z])|(?<=[a-z]{2})([.!?])(?=[A-Z][a-z])", text):
        out.append(span_issue(text, m.start(), m.end(), category="typography", check="missing_space_after_punctuation", severity="minor",
                              message="Missing space after punctuation.", replacements=[m.group(0) + " "]))
    for m in re.finditer(r"!{2,}|\?{2,}|[?!]{3,}|,{2,}|;{2,}|(?<!\.)\.\.(?!\.)|\.{4,}", text):
        rep = "…" if m.group(0).startswith(".") and len(m.group(0)) >= 4 else m.group(0)[0]
        out.append(span_issue(text, m.start(), m.end(), category="punctuation", check="repeated_punctuation", severity="minor",
                              message="Repeated punctuation looks unprofessional in print.", replacements=[rep]))
    for m in re.finditer(r"(?<=\w) - (?=\w)|(?<=\w)--(?=\w)| -- ", text):
        out.append(span_issue(text, m.start(), m.end(), category="typography", check="hyphen_as_dash", severity="minor",
                              message="Hyphen(s) used where an em dash (—) belongs.", replacements=["—"]))
    if "..." in text and "…" in text:
        out.append(Issue(category="typography", check="mixed_ellipses", severity="minor",
                         message="Both '...' and '…' ellipsis styles are used.", suggestion="Use one style consistently (auto-fix uses …)."))
    spaced = len(re.findall(r" — ", text))
    closed = len(re.findall(r"\w—\w", text))
    if spaced and closed:
        out.append(Issue(category="typography", check="mixed_em_dash_spacing", severity="info",
                         message=f"Em dashes are both spaced ({spaced}) and closed ({closed}).",
                         suggestion="US style closes em dashes (word—word); pick one."))
    out.extend(_smart_quote_issues(text))
    out.extend(_balance_issues(text, ctx))
    if ctx.audience not in ("children", "middle_grade"):
        caps = [m for m in re.finditer(r"\b[A-Z]{4,}\b", text) if m.group(0) not in ACRONYM_OK and m.group(0).lower() not in ctx.known_names]
        for m in caps[:5]:
            out.append(span_issue(text, m.start(), m.end(), category="style", check="all_caps", severity="info",
                                  message="Word in ALL CAPS reads as shouting; consider italics for emphasis."))
    if ctx.fiction and ctx.structure != "poems":
        nums = [m for m in re.finditer(r"(?<![\d$£€.,:/#-])\b([1-9]\d?)\b(?![\d:%.,/]\d|\s?(?:%|percent|am|pm|a\.m\.|p\.m\.))", narration_only(text))]
        if len(nums) >= 3:
            out.append(Issue(category="style", check="numerals_in_fiction", severity="info",
                             message=f"{len(nums)} small numbers written as digits; fiction style (Chicago) spells out numbers up to one hundred.",
                             suggestion="Write numbers as words in narration and dialogue."))
    return _cap(out, 60)


def _repeated_word_issues(text: str) -> list[Issue]:
    out = []
    for m in re.finditer(r"\b(\w+)\s+\1\b", text, re.IGNORECASE):
        if m.group(1).lower() in {"had", "that", "is", "ha", "no", "yes", "very", "so", "bye", "knock", "tick", "tock", "now", "go", "run"}:
            continue
        out.append(span_issue(text, m.start(), m.end(), category="repetition", check="repeated_word", severity="major",
                              message=f"Word repeated: '{m.group(0)}'.", replacements=[m.group(1)]))
    return out


def check_repetition(text: str, ctx: ChapterContext) -> list[Issue]:
    out: list[Issue] = _repeated_word_issues(text)
    sents = sentences(text)
    total = word_count(text)

    # Same first word for several consecutive sentences
    common = {"i", "he", "she", "they", "the", "we", "you"}
    run_word, run_len, run_start = None, 0, 0
    for i, s in enumerate(sents + [""]):
        first = (words(s)[:1] or [""])[0].lower()
        if first and first == run_word:
            run_len += 1
            continue
        if run_word and run_len >= (4 if run_word in common else 3):
            out.append(Issue(category="repetition", check="repeated_sentence_openers", severity="minor",
                             message=f"{run_len} consecutive sentences start with '{run_word.capitalize()}'.",
                             excerpt=sents[run_start][:160], suggestion="Vary sentence openings."))
        run_word, run_len, run_start = first, 1, i

    paras = [p for p in paragraphs(text) if not is_scene_break(p)]
    for i in range(len(paras) - 2):
        firsts = [(words(p)[:1] or [""])[0].lower() for p in paras[i : i + 3]]
        if firsts[0] and len(set(firsts)) == 1 and firsts[0] not in {"the", "i"}:
            out.append(Issue(category="repetition", check="repeated_paragraph_openers", severity="minor",
                             message=f"Three paragraphs in a row start with '{firsts[0].capitalize()}'.", excerpt=paras[i][:160]))

    tokens = [w.lower() for w in words(text)]
    counts = Counter(t for t in tokens if t not in STOPWORDS and len(t) > 3 and t not in ctx.known_names)
    for w, c in counts.most_common(8):
        if c >= 8 and _per_1000(c, total) > 4.5:
            out.append(Issue(category="repetition", check="overused_word", severity="minor",
                             message=f"'{w}' is used {c} times ({_per_1000(c, total):.1f} per 1,000 words).",
                             suggestion="Use synonyms or restructure some sentences."))

    # Echoes: same uncommon word within 25 words
    echoes = 0
    last_seen: dict[str, int] = {}
    for idx, t in enumerate(tokens):
        if len(t) >= 6 and t not in STOPWORDS and t not in ctx.known_names:
            if t in last_seen and idx - last_seen[t] <= 25:
                echoes += 1
            last_seen[t] = idx
    if echoes >= max(6, total // 400):
        out.append(Issue(category="repetition", check="word_echoes", severity="minor",
                         message=f"{echoes} 'echoes' (the same distinctive word repeated within ~25 words).",
                         suggestion="Read aloud and vary repeated words that sit close together."))

    grams = Counter(tuple(tokens[i : i + 4]) for i in range(len(tokens) - 3))
    for gram, c in grams.most_common(10):
        if c >= 3 and sum(1 for g in gram if g not in STOPWORDS) >= 2:
            out.append(Issue(category="repetition", check="repeated_phrase", severity="minor",
                             message=f"Phrase '{' '.join(gram)}' appears {c} times in this part."))

    lower = text.lower()
    for phrase in BANNED_PHRASES:
        for m in re.finditer(r"\b" + re.escape(phrase) + r"\b", lower):
            out.append(span_issue(text, m.start(), m.end(), category="ai_artifact", check="ai_tell_phrase", severity="major",
                                  message=f"'{phrase}' is a phrase readers associate with AI-written text.",
                                  suggestion="Rewrite with a specific, concrete image."))
    for phrase in SOFT_AI_TELLS:
        hits = list(re.finditer(r"\b" + re.escape(phrase) + r"\b", lower))
        if len(hits) >= 2:
            out.append(Issue(category="style", check="stock_phrase", severity="minor",
                             message=f"Stock phrase '{phrase}' used {len(hits)} times.", excerpt=excerpt_around(text, hits[0].start(), hits[0].end())))
    for phrase in CLICHES:
        for m in re.finditer(r"\b" + re.escape(phrase) + r"\b", lower):
            out.append(span_issue(text, m.start(), m.end(), category="style", check="cliche", severity="minor",
                                  message=f"Cliché: '{phrase}'.", suggestion="Replace with a fresh, specific image."))
    return _cap(out, 60)


def compute_stats(text: str, ctx: ChapterContext) -> dict:
    sents = sentences(text)
    lens = [word_count(s) for s in sents] or [0]
    total = word_count(text)
    narration = narration_only(text)
    quoted_words = total - word_count(narration)
    tokens = [w.lower() for w in words(text)]
    adverbs = sum(1 for t in tokens if t.endswith("ly") and len(t) > 4 and t not in LY_EXCEPTIONS)
    fillers = sum(1 for t in tokens if t in FILLER_WORDS)
    passive = sum(1 for s in sents if PASSIVE_RE.search(s))
    prose = " ".join(sents)
    try:
        grade = float(textstat.flesch_kincaid_grade(prose)) if total >= 100 else None
        ease = float(textstat.flesch_reading_ease(prose)) if total >= 100 else None
    except Exception:
        grade = ease = None
    return {
        "words": total,
        "sentences": len(sents),
        "paragraphs": len(paragraphs(text)),
        "avg_sentence_words": round(statistics.mean(lens), 1),
        "sentence_length_stdev": round(statistics.pstdev(lens), 1) if len(lens) > 1 else 0,
        "fk_grade": round(grade, 1) if grade is not None else None,
        "reading_ease": round(ease, 1) if ease is not None else None,
        "dialogue_ratio": round(quoted_words / max(1, total), 2),
        "passive_ratio": round(passive / max(1, len(sents)), 2),
        "adverbs_per_1000": round(_per_1000(adverbs, total), 1),
        "fillers_per_1000": round(_per_1000(fillers, total), 1),
        "reading_minutes": round(total / 250, 1),
    }


def check_style(text: str, ctx: ChapterContext, stats: dict) -> list[Issue]:
    out: list[Issue] = []
    total = stats["words"]
    if ctx.structure == "poems" or total < 50:
        return out
    audience = AUDIENCES.get(ctx.audience, AUDIENCES["adult"])

    if stats["fillers_per_1000"] > 8:
        out.append(Issue(category="style", check="filler_words", severity="minor",
                         message=f"Filler words (very, really, just, suddenly…) at {stats['fillers_per_1000']} per 1,000 words.",
                         suggestion="Cut most fillers; they weaken prose."))
    if stats["adverbs_per_1000"] > 15:
        out.append(Issue(category="style", check="adverb_density", severity="minor",
                         message=f"High adverb density ({stats['adverbs_per_1000']} -ly adverbs per 1,000 words).",
                         suggestion="Prefer strong verbs over verb + adverb."))
    if stats["passive_ratio"] > 0.15:
        examples = [s for s in sentences(text) if PASSIVE_RE.search(s)][:3]
        out.append(Issue(category="style", check="passive_voice", severity="minor",
                         message=f"{int(stats['passive_ratio'] * 100)}% of sentences use passive voice.",
                         excerpt=" | ".join(e[:90] for e in examples), suggestion="Rewrite key sentences in active voice."))
    weak = len(WEAK_VERB_RE.findall(text))
    if _per_1000(weak, total) > 3:
        out.append(Issue(category="style", check="weak_verbs", severity="info",
                         message=f"'began to / started to / seemed to' used {weak} times.", suggestion="Show the action directly."))
    if ctx.fiction:
        filt = len(FILTER_PHRASES.findall(narration_only(text)))
        if _per_1000(filt, total) > 4:
            out.append(Issue(category="style", check="filter_words", severity="info",
                             message=f"{filt} filter phrases (she felt / he saw / I noticed) distance the reader from the POV.",
                             suggestion="Describe the sensation or sight directly."))
        telling = TELLING_RE.findall(text)
        if len(telling) >= 4:
            out.append(Issue(category="style", check="telling_emotions", severity="minor",
                             message=f"Emotions are named rather than shown {len(telling)} times (e.g. '{telling[0]}').",
                             suggestion="Show emotion through action, body language and dialogue."))
        tag_adverbs = list(re.finditer(r"[”\"],?\s+(?:\w+\s+)?(?:said|asked|replied|whispered)\s+(\w+ly)\b", text))
        if len(tag_adverbs) >= 3:
            out.append(Issue(category="dialogue", check="dialogue_tag_adverbs", severity="minor",
                             message=f"{len(tag_adverbs)} dialogue tags use adverbs ('said softly').",
                             excerpt=excerpt_around(text, tag_adverbs[0].start(), tag_adverbs[0].end())))
        bookisms = [m for m in re.finditer(r"[”\"],?\s+(?:\w+\s+){0,2}(\w+)\b", text) if m.group(1).lower() in SAID_BOOKISMS]
        if len(bookisms) > 3:
            out.append(Issue(category="dialogue", check="said_bookisms", severity="minor",
                             message=f"{len(bookisms)} showy dialogue tags (hissed, growled, exclaimed…). 'Said' is usually invisible and better.",
                             excerpt=excerpt_around(text, bookisms[0].start(), bookisms[0].end())))
        if ctx.structure in ("chapters", "scenes") and total > 1500:
            if stats["dialogue_ratio"] < 0.05:
                out.append(Issue(category="dialogue", check="little_dialogue", severity="info",
                                 message="Almost no dialogue in this part; long narrative stretches can feel slow."))
            elif stats["dialogue_ratio"] > 0.85:
                out.append(Issue(category="dialogue", check="dialogue_heavy", severity="info",
                                 message="This part is almost all dialogue; add grounding action and setting."))
    exclaims = len(re.findall(r"!", narration_only(text)))
    if _per_1000(exclaims, total) > 3:
        out.append(Issue(category="style", check="exclamation_overuse", severity="minor",
                         message=f"{exclaims} exclamation marks in narration.", suggestion="Let the writing carry the emphasis."))

    long_limit = 22 if ctx.audience == "children" else 30 if ctx.audience == "middle_grade" else 45
    cursor = 0
    long_count = 0
    for s in sentences(text):
        n = word_count(s)
        pos = text.find(s[:40], cursor)
        if pos >= 0:
            cursor = pos
        if n > long_limit and long_count < 10:
            long_count += 1
            out.append(Issue(category="readability", check="long_sentence", severity="minor",
                             message=f"Very long sentence ({n} words; limit for this audience is {long_limit}).",
                             excerpt=s[:200] + ("…" if len(s) > 200 else ""), offset=pos if pos >= 0 else None,
                             suggestion="Split it into two or three sentences."))
    para_limit = 90 if ctx.audience == "children" else 140 if ctx.audience == "middle_grade" else 230
    for p in paragraphs(text):
        n = word_count(p)
        if n > para_limit:
            out.append(Issue(category="readability", check="long_paragraph", severity="minor",
                             message=f"Wall-of-text paragraph ({n} words). Long paragraphs are hard to read on phones and e-readers.",
                             excerpt=p[:160] + "…", suggestion="Break it up at natural shifts in action or thought."))
    if stats["fk_grade"] is not None and stats["fk_grade"] > audience["max_grade"] + 1:
        sev = "major" if ctx.audience in ("children", "middle_grade") else "minor"
        out.append(Issue(category="readability", check="reading_level", severity=sev,
                         message=f"Reading level is grade {stats['fk_grade']}, above the target for {audience['label']} (≤ {audience['max_grade']}).",
                         suggestion="Use shorter sentences and simpler words."))
    if stats["avg_sentence_words"] > audience["max_avg_sentence"]:
        out.append(Issue(category="readability", check="avg_sentence_length", severity="minor",
                         message=f"Average sentence length is {stats['avg_sentence_words']} words (target ≤ {audience['max_avg_sentence']})."))
    if stats["sentences"] >= 30 and stats["sentence_length_stdev"] < 4:
        out.append(Issue(category="style", check="monotonous_rhythm", severity="info",
                         message="Sentence lengths barely vary; prose rhythm may feel monotonous.",
                         suggestion="Mix short punchy sentences with longer flowing ones."))
    return _cap(out, 40)


def check_tense_pov(text: str, ctx: ChapterContext) -> list[Issue]:
    out: list[Issue] = []
    if not ctx.fiction or ctx.structure == "poems":
        return out
    narration = narration_only(text)
    past = len(PAST_MARKERS.findall(narration))
    present = len(PRESENT_MARKERS.findall(narration))
    total_markers = past + present
    if total_markers >= 40:
        if ctx.tense == "past" and present / total_markers > 0.35:
            out.append(Issue(category="pov_tense", check="tense_drift", severity="major",
                             message=f"Narration looks largely present tense ({present} present vs {past} past markers) but the book is past tense."))
        if ctx.tense == "present" and past / total_markers > 0.6:
            out.append(Issue(category="pov_tense", check="tense_drift", severity="major",
                             message=f"Narration looks largely past tense ({past} past vs {present} present markers) but the book is present tense."))
    if ctx.tense == "past":
        flagged = 0
        for p in paragraphs(narration):
            if word_count(p) >= 40 and len(PRESENT_MARKERS.findall(p)) >= 4 and not PAST_MARKERS.search(p) and flagged < 5:
                flagged += 1
                out.append(Issue(category="pov_tense", check="tense_shift_paragraph", severity="minor",
                                 message="Paragraph narrated in present tense in a past-tense book (check for a tense slip).",
                                 excerpt=p.strip()[:160]))
    fp = FIRST_PERSON.findall(narration)
    total = word_count(narration)
    if ctx.pov == "first" and total > 400 and len(fp) == 0:
        out.append(Issue(category="pov_tense", check="pov_drift", severity="major",
                         message="No first-person narration found, but the book is written in first person."))
    if ctx.pov.startswith("third") and _per_1000(len(fp), total) > 4:
        out.append(Issue(category="pov_tense", check="pov_slip", severity="minor",
                         message=f"{len(fp)} first-person pronouns outside dialogue in a third-person book (POV slip or unmarked thoughts).",
                         suggestion="Put direct thoughts in italics or convert to third person."))
    return out


def check_content(text: str, ctx: ChapterContext) -> list[Issue]:
    out: list[Issue] = []
    young = ctx.audience in ("children", "middle_grade")
    for m in SLURS.finditer(text):
        out.append(span_issue(text, m.start(), m.end(), category="content", check="slur", severity="critical",
                              message="Slur detected. Stores may reject the book and readers will report it."))
    for m in PROFANITY_STRONG.finditer(text):
        if young or ctx.content_rating in ("clean", "moderate") or ctx.audience == "young_adult":
            sev = "critical" if young or ctx.content_rating == "clean" else "major"
            out.append(span_issue(text, m.start(), m.end(), category="content", check="strong_profanity", severity=sev,
                                  message=f"Strong profanity not suitable for a {ctx.content_rating} book for {AUDIENCES.get(ctx.audience, {}).get('label', ctx.audience)}."))
    for m in PROFANITY_MILD.finditer(text):
        if young or ctx.content_rating == "clean":
            out.append(span_issue(text, m.start(), m.end(), category="content", check="mild_profanity", severity="major",
                                  message="Mild profanity in a clean/young-reader book."))
    return _cap(out, 30)


def check_compliance(text: str, ctx: ChapterContext) -> list[Issue]:
    out: list[Issue] = []
    for m in URL_RE.finditer(text):
        out.append(span_issue(text, m.start(), m.end(), category="compliance", check="url", severity="major",
                              message=("Web address in the text. AI-generated links are often fake, and links to other stores get books rejected."
                                       if not ctx.fiction else "Web address inside fiction; remove it or make it obviously fictional.")))
    for m in EMAIL_RE.finditer(text):
        out.append(span_issue(text, m.start(), m.end(), category="compliance", check="email", severity="major",
                              message="Email address in the text; make sure it is fictional or yours."))
    for m in PHONE_RE.finditer(text):
        out.append(span_issue(text, m.start(), m.end(), category="compliance", check="phone_number", severity="major",
                              message="Phone number in the text; real numbers belong to real people. Use a 555-01xx number."))
    for m in STORE_RE.finditer(text):
        out.append(span_issue(text, m.start(), m.end(), category="compliance", check="store_reference", severity="minor",
                              message="Retailer name in the text. Apple Books rejects references to competing stores (Amazon, Kindle…).",
                              suggestion="Remove or generalise (e.g. 'an e-reader')."))
    seen: set[str] = set()
    for m in TRADEMARKS.finditer(text):
        name = m.group(0).lower()
        if name in seen:
            continue
        seen.add(name)
        out.append(span_issue(text, m.start(), m.end(), category="compliance", check="trademark", severity="info",
                              message=f"Trademark '{m.group(0)}': fine in passing, but never disparage it or use it in your title/cover."))
    return _cap(out, 30)


def check_structure(text: str, ctx: ChapterContext, stats: dict) -> list[Issue]:
    out: list[Issue] = []
    if not text.strip():
        return [Issue(category="structure", check="empty_part", severity="critical", message="This part has no text.")]
    if ctx.structure not in ("scenes",) and not ctx.title.strip():
        out.append(Issue(category="structure", check="missing_title", severity="minor", message="This part has no title."))
    if len(ctx.title) > 80:
        out.append(Issue(category="structure", check="long_title", severity="minor", message="Title is longer than 80 characters."))
    if ctx.target_words and ctx.structure != "poems":
        ratio = stats["words"] / max(1, ctx.target_words)
        if ratio < 0.6:
            out.append(Issue(category="structure", check="too_short", severity="major",
                             message=f"Only {stats['words']:,} words against a target of {ctx.target_words:,} ({int(ratio * 100)}%).",
                             suggestion="Regenerate or extend; short parts make the book feel thin."))
        elif ratio > 1.6:
            out.append(Issue(category="structure", check="too_long", severity="minor",
                             message=f"{stats['words']:,} words against a target of {ctx.target_words:,}; consider splitting."))
    stripped = text.rstrip()
    if ctx.structure != "poems" and stripped and stripped[-1] not in ".!?”\"’'…*)—":
        out.append(Issue(category="structure", check="truncated_ending", severity="major",
                         message="The text ends mid-sentence (likely truncated generation).",
                         excerpt="…" + stripped[-120:], suggestion="Regenerate or finish the final sentence."))
    first = text.lstrip()[:1]
    if ctx.structure != "poems" and first.isalpha() and first.islower():
        out.append(Issue(category="structure", check="lowercase_start", severity="minor", message="The text starts with a lowercase letter."))
    return out


def check_chapter(text: str, ctx: ChapterContext) -> tuple[list[Issue], dict]:
    stats = compute_stats(text, ctx)
    issues: list[Issue] = []
    issues += check_structure(text, ctx, stats)
    issues += check_encoding(text)
    issues += check_ai_artifacts(text, ctx)
    issues += check_typography(text, ctx)
    issues += check_repetition(text, ctx)
    issues += check_style(text, ctx, stats)
    issues += check_tense_pov(text, ctx)
    issues += check_content(text, ctx)
    issues += check_compliance(text, ctx)
    for i in issues:
        i.chapter_number = ctx.number
    return issues, stats


def spelling_variants_in(text: str) -> dict[str, int]:
    lower = text.lower()
    found: dict[str, int] = {}
    for us, uk in US_UK:
        for w in (us, uk):
            c = len(re.findall(rf"\b{w}(?:s|ed|ing|ite)?\b", lower))
            if c:
                found[w] = found.get(w, 0) + c
    return found
