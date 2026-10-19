# Quality checks

Every QA run combines three layers. Each issue has a **severity**: `critical` (must fix before publishing), `major` (should fix), `minor` (polish) or `info` (worth knowing). It is stored with the exact text span when there is one, so it can be fixed with one click.

| Layer | Source | Needs |
| --- | --- | --- |
| Spelling, grammar, punctuation, style | [LanguageTool](https://languagetool.org) (self-hosted, `picky` level) | the `languagetool` container |
| Rule-based checks (below) | `app/services/qa/rules.py`, `book_rules.py` | nothing |
| AI editorial review | the editor model on OpenRouter | `OPENROUTER_API_KEY` |

If LanguageTool or OpenRouter is unavailable, the run still completes and records a warning saying which checks were skipped.

## Language (LanguageTool)

- Spelling and typos. Invented names and terms from the story bible, and capitalised words used 3 or more times, are never flagged.
- Grammar, agreement, confused words (their/there, affect/effect), collocations, non-standard phrases.
- Punctuation and capitalisation.
- Redundancy, wordiness, plain-English and style suggestions.
- British spellings in a US book and vice versa. These are reported as minor consistency issues, not typos.

## Per-part rule checks

| Category | Checks |
| --- | --- |
| **Encoding** | Unicode replacement characters (`�`), mojibake (`â€™`), zero-width and control characters |
| **AI artifacts** | Markdown bold or headings, code fences, HTML tags, assistant text ("Here is the chapter…", "As an AI…"), placeholders (`[insert…]`, TODO, `{{…}}`), chapter headings inside the body, a premature "The End", list formatting in fiction |
| **AI-tell phrases** | Phrases readers associate with machine writing ("delve", "tapestry", "a testament to", "couldn't help but", "barely above a whisper", …), plus repeated stock phrases ("a flicker of", "the weight of", …) |
| **Typography** | Double spaces, a space before punctuation, a missing space after punctuation, repeated punctuation (`!!`, `??`, `..`), hyphens used as dashes, mixed `...` and `…`, mixed em-dash spacing, straight or mixed quotes and apostrophes, ALL-CAPS shouting, numerals in fiction narration |
| **Punctuation balance** | Unbalanced quotation marks (follows the convention where multi-paragraph dialogue leaves the closing quote off), unbalanced parentheses and brackets |
| **Repetition** | Doubled words ("the the"), runs of sentences or paragraphs starting with the same word, overused words, word echoes (the same distinctive word within about 25 words), repeated 4-word phrases, clichés |
| **Style** | Filler-word density, adverb density, passive voice ratio, weak verbs ("began to"), filter words ("she felt / he saw"), emotions named instead of shown, adverbs in dialogue tags, showy dialogue tags ("hissed", "growled"), too little or too much dialogue, exclamation overuse, monotonous sentence rhythm |
| **Readability** | Flesch-Kincaid grade compared with the audience target, average sentence length, overlong sentences and wall-of-text paragraphs (limits are stricter for children and middle grade) |
| **Tense and POV** | Present-tense narration in a past-tense book (and vice versa) at both part and paragraph level, first-person pronouns in third-person narration, missing first person in first-person books. Dialogue is excluded. |
| **Content** | Slurs; strong or mild profanity measured against the audience and content rating |
| **Store compliance** | URLs (AI-generated links are often fake), email addresses, real-looking phone numbers, retailer names (Apple rejects references to Amazon or Kindle), trademarks |
| **Structure** | Empty parts, missing or overlong titles, parts much shorter or longer than their outline target, text that ends mid-sentence (truncated generation), a lowercase start |

## Whole-book rule checks

- Total length against the category's word range (for example, a "novel" under 50,000 words).
- Missing parts compared with the outline, unbalanced part lengths, duplicate titles.
- **Duplicated text**: identical sentences repeated anywhere, and near-duplicate passages across parts (an LLM sometimes rewrites a scene twice).
- Signature phrases repeated throughout the book, and formulaic part openings or endings.
- **Name consistency**: likely misspellings of character and place names (for example "Corwyn" against "Corwin"), and story-bible names that never appear.
- US/UK spelling mixtures, inconsistent hyphenation ("half-light" against "halflight"), inconsistent capitalisation of world terms.
- Metadata that stores reject: "bestseller", "free", "Kindle" or series numbering in the title, title plus subtitle over 200 characters, an all-caps title.

## AI editorial review

For each part, the editor model checks it against the story bible, the earlier parts and the outline:

- Fiction: continuity (names, ages, appearance, injuries, objects, who knows what), timeline, plot logic and holes, characterisation, POV and tense slips, dialogue quality, pacing, show-vs-tell, anachronisms.
- Non-fiction: factual accuracy, **fabricated statistics, studies, quotes or URLs**, clarity, structure, actionability, and medical, legal or financial advice risk.
- Both: outline adherence, audience fit, copyright risk (quoted lyrics or passages, real living people), and machine-sounding prose.

For the whole book it acts as an acquisitions editor and checks unresolved plot threads, character arcs, repeated beats, cross-part timeline errors, whether the ending is earned, the strength of the opening hook (the store's "Look Inside" sample) and market fit. Its quotes are matched back to the text, exactly where possible and fuzzily otherwise, so issues can be located.

## Scoring

Each part's score is 100 minus a severity-weighted issue density per 1,000 words:

- Critical = 15, major = 4, minor = 1, info = 0.
- Repeats of the same problem count `1 + log2(n)` times, not `n` times.
- Any open critical issue caps the score at 69.

The book score is the word-weighted average of the part scores, minus a penalty (capped) for whole-book issues.

| Score | Grade |
| --- | --- |
| ≥ 90 | Publish-ready |
| 80–89 | Good: polish recommended |
| 65–79 | Needs editing |
| < 65 | Not ready |

## Fixing

- **Apply** a single suggestion. The exact span is replaced, and the fix is refused if the text changed since the check ran.
- **Auto-fix** applies safe mechanical fixes: single-suggestion spelling and grammar corrections, doubled words, spacing, repeated punctuation, dashes, invisible characters and Markdown leftovers. It also normalises typography to curly quotes and `…`, then re-checks the affected parts.
- **AI fix** sends a part's open issues to the writer model as revision instructions, then re-checks it. The part keeps its approval, and the previous text stays in its revision history.
- **Ignore** hides an issue. Ignored issues stay ignored on later runs.

Every change creates a revision, and any revision can be restored.
