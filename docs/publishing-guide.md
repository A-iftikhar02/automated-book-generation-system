# Publishing guide: Amazon KDP and Apple Books

BookPilot produces the files and metadata the stores ask for. The steps below take a finished book from the **Publish** and **Export** tabs onto the stores.

## Before you upload

1. **Read the book yourself.** AI drafts need a human editor. Stores remove low-quality, duplicated or misleading content, and readers' reviews will catch what you miss.
2. Get the **Readiness** checklist to green: every part approved, length within the category, a recent QA run with no critical issues and a score of 80 or more, an author name, a description, keywords, categories and a cover.
3. **Disclose AI use.** KDP asks during setup whether the text, images or translations are AI-generated, and you must answer accurately. Check Apple's current content guidelines too.
4. Only publish content you have the right to publish: no real people portrayed in a defamatory way, no lyrics or long quotes from other works, no trademarks in the title.

## Amazon KDP: Kindle eBook

| KDP field | Where it comes from |
| --- | --- |
| Title, subtitle, series, edition | Publish tab |
| Author | Author / pen name |
| Description | Publish → Description (KDP accepts the HTML subset it uses) |
| Keywords (7 boxes) | Publish → Keywords |
| Categories | Publish → Store categories (choose the closest matches in KDP's picker) |
| Manuscript | Export → **EPUB** (or DOCX) |
| Cover | Publish → Cover. Download `cover.jpg` (1600 × 2560) |
| ISBN | Optional for ebooks; KDP assigns an ASIN |

Use KDP's online previewer to check the book on phone, tablet and Kindle.

## Amazon KDP: Paperback

1. Export → **Print PDF**. Pick a trim size (6 × 9 in is the most common for fiction and non-fiction; 5 × 8 or 5.5 × 8.5 suits novellas). Turn on **large print** if the book is too short. KDP needs **at least 24 pages**; the export warns you if it falls short.
   - All fonts are embedded and margins are mirrored. The inside margin is set from KDP's gutter table for the final page count.
   - The title page and every part start on a right-hand page.
2. Export → **Wrap cover PDF** with the same trim size and the paper you'll choose in KDP (white or cream). Spine width comes from KDP's per-page thickness, with 0.125 in bleed on every side. The bottom-right of the back cover is left clear for KDP's barcode. Spine text is only added above 79 pages, as KDP requires.
3. In KDP choose "No bleed" for the interior and upload the PDF; upload the wrap PDF as the cover. Take KDP's free ISBN or enter your own (Publish → ISBN print).
4. Order a proof copy before publishing.

## Apple Books (Apple Books for Authors / iTunes Producer)

| Apple field | Where it comes from |
| --- | --- |
| Book file | Export → **EPUB**. It is EPUB 3, with a cover, navigation, landmarks and a Start location, and is validated with **epubcheck** (the validator Apple uses) when it's available |
| Cover | `cover.jpg` (Apple requires at least 1400 px on the shortest side) |
| Description, categories, series | Publish tab |
| ISBN | Optional on Apple Books |

Apple rejects books that mention other retailers. QA flags "Amazon", "Kindle" and similar words in the text.

## Other stores

The same EPUB works for Kobo Writing Life, Google Play Books and Barnes & Noble Press, and the DOCX works for Draft2Digital.
