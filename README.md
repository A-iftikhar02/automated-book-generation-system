# BookPilot: AI book generation for KDP and Apple Books

BookPilot plans, writes, edits, quality-checks and typesets books, from short stories to epic novels, poetry and non-fiction. It produces files you can upload to **Amazon KDP** (Kindle and paperback) and **Apple Books**. You stay in control throughout: approve the outline, review every part (or run on autopilot), fix what the QA finds, then export.

- **Six AI providers**: [OpenRouter](https://openrouter.ai), Google AI Studio (Gemini), Groq, Cerebras, Mistral and local models through [Ollama](https://ollama.com). Each role (writer, editor) is a fallback chain, so when one provider is rate-limited or out of free quota the next takes over. A book's writer is pinned once its first part is written, so the voice stays consistent. Cover art uses OpenRouter.
- **11 book formats** with their own length, structure and writing guidance, plus 29 genres, audience levels, content ratings, POV and tense.
- **Consistency engine.** A story bible (characters, settings, world rules, glossary) is generated first and updated after every part. Each part is written with the full outline, summaries of everything before it and the end of the previous part. Long chapters are written in segments.
- **Quality assurance.** Self-hosted LanguageTool for spelling, grammar and punctuation, about 40 rule-based checks, an AI editorial review per part and for the whole book, a quality score, one-click fixes, auto-fix and AI fix. See [docs/quality-checks.md](docs/quality-checks.md).
- **Store-ready output.** EPUB 3 (validated with epubcheck), a KDP print interior PDF (trim sizes, mirrored margins, gutter set by page count, embedded fonts, chapters starting on right-hand pages), a full-wrap paperback cover with a computed spine, DOCX and TXT.
- **Selling tools.** AI-written description, back-cover copy, 7 keywords and categories; AI cover art with typeset title and author; a publishing-readiness checklist. See [docs/publishing-guide.md](docs/publishing-guide.md).
- **Durable background jobs** in Postgres. Writing a 40-part novel survives page reloads, and jobs can be cancelled and retried.
- **Optional Slack notifications.** They are off unless you turn them on.

## Book formats

| Format | Words | Structure |
| --- | --- | --- |
| Flash fiction collection | 5k–20k | 8–30 standalone stories |
| Short story | 3k–10k | one story in 2–6 scenes |
| Short story collection | 25k–70k | 6–15 stories |
| Novelette | 10k–20k | 4–10 chapters |
| Novella | 20k–50k | 8–20 chapters |
| Novel | 50k–100k | 18–40 chapters |
| Long / epic novel | 100k–150k | 35–60 chapters |
| Children's chapter book (6–9) | 4k–15k | 6–15 chapters |
| Non-fiction guide / how-to | 20k–60k | 8–20 chapters |
| Non-fiction short read | 7k–20k | 5–12 chapters |
| Poetry collection | 3k–15k | 20–80 poems |

## Quick start (Docker)

```bash
cp .env.example .env          # then add at least one provider key and set WRITER_MODELS / EDITOR_MODELS
docker compose up -d --build  # postgres, languagetool, api, worker, frontend
```

Open http://localhost:3000. The API docs are at http://localhost:8000/docs. Postgres is exposed on host port **5442** (change it with `POSTGRES_PORT`) so it doesn't clash with a local Postgres.

## Local development

```bash
docker compose up -d db languagetool          # infrastructure only
uv venv .venv && uv pip install -r requirements.txt   # or python -m venv / pip
cp .env.example .env                          # add provider keys
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000
.venv/bin/python -m app.worker                # in a second terminal
cd frontend && npm install && npm run dev     # http://localhost:3000
```

To run jobs inside the API process instead of a separate worker, set `RUN_WORKER_IN_PROCESS=true`.

### Tests

```bash
docker compose up -d db languagetool
.venv/bin/python -m pytest
```

The suite creates a `bookpilot_test` database. It drives the full pipeline through the HTTP API with a fake LLM, so no API key is needed and nothing is spent: plan → outline review → write and approve → revise → QA (including live LanguageTool) → single fix, auto-fix and AI fix → metadata → cover → every export format. It also exercises the real OpenRouter client against a local mock server.

## Moving to another laptop

Your books live in two places: the **database** (books, outlines, chapters, revisions, QA results) and the **storage folder** (covers and exported files). `scripts/backup.sh` packs both into one file, and `scripts/restore.sh` unpacks it on the new machine.

### 1. On the old laptop: make a backup

Let running jobs finish first (or cancel them). A job that is mid-way during the backup shows as failed after the restore, and you just press **Retry**.

```bash
cd automated-book-generation-system
./scripts/backup.sh                 # → backups/bookpilot-backup-<date>.tar.gz
./scripts/backup.sh --with-env      # also include .env (your API keys): keep that file private!
```

Copy the `.tar.gz` file to the new laptop (USB drive, AirDrop, Google Drive…). The `backups/` folder is ignored by git, so backups are never pushed.

### 2. On the new laptop: install and restore

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and start it.
2. Get the code. Either `git clone` your repository, or copy the project folder (you can leave out `.venv`, `frontend/node_modules`, `storage` and `backups`).
3. Create `.env`: copy it from the old laptop, or run `cp .env.example .env` and paste your keys. If you made the backup with `--with-env`, the restore creates it for you.
4. Build and start once, then restore:

   ```bash
   cd automated-book-generation-system
   docker compose up -d --build
   ./scripts/restore.sh ~/Downloads/bookpilot-backup-<date>.tar.gz
   ```

   The restore **replaces** any books already on the new laptop (it asks first; add `--yes` to skip the question). It restores the database and files, then starts everything. Database migrations run automatically, so a backup from an older version of the app works with newer code.
5. Open http://localhost:3000. Your books, chapters, QA results, covers and exports are all there.

### What is *not* in the backup

- **Ollama models** (several GB each). On the new laptop, install [Ollama](https://ollama.com/download) and run `ollama pull <model>` for the models named in your `.env`, for example `ollama pull qwen3.8:27b`. On an Apple Silicon Mac (M1–M4), Ollama uses the GPU and runs many times faster than on an Intel Mac.
- **API keys**, unless you used `--with-env`.
- The LanguageTool and Postgres programs themselves. Docker downloads them again automatically.

Tip: run `./scripts/backup.sh` regularly, for example after finishing each book, so you always have a copy.

## Configuration (`.env`)

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | – | [OpenRouter](https://openrouter.ai/keys): any model, plus cover art |
| `GEMINI_API_KEY` | – | [Google AI Studio](https://aistudio.google.com/apikey) free tier |
| `GROQ_API_KEY` | – | [Groq](https://console.groq.com/keys) free tier |
| `CEREBRAS_API_KEY` | – | [Cerebras](https://cloud.cerebras.ai) free tier |
| `MISTRAL_API_KEY` | – | [Mistral](https://console.mistral.ai/api-keys) free "Experiment" plan |
| `OLLAMA_ENABLED` / `OLLAMA_BASE_URL` | `false` / `http://localhost:11434` | Local models via Ollama (`ollama:<model>`). Docker containers reach it at `host.docker.internal` |
| `OLLAMA_NUM_CTX` | `32768` | Context window requested from Ollama |
| `WRITER_MODELS` | `anthropic/claude-sonnet-5.5` | Fallback chain `provider:model, …` (no prefix = OpenRouter) for the bible, outline and prose |
| `EDITOR_MODELS` | `anthropic/claude-haiku-5.5` | Fallback chain for summaries, QA review and the store listing |
| `IMAGE_MODEL` | `google/gemini-3.1-flash-image` | Cover artwork (OpenRouter) |
| `DATABASE_URL` | `postgresql+psycopg://bookpilot:bookpilot@localhost:5442/bookpilot` | Docker Postgres |
| `LANGUAGETOOL_URL` | `http://localhost:8010` | Grammar and spelling server |
| `EPUBCHECK_JAR` | – (set in the Docker image) | EPUB validation |
| `SLACK_ENABLED` / `SLACK_WEBHOOK_URL` | `false` / – | Optional notifications; both are needed to send |
| `STORAGE_DIR` | `./storage` | Covers and exported files |

**Cost.** Spend depends on the models you pick. Every book tracks its token use and its OpenRouter cost, which is shown in the app. As a rough guide, a 75,000-word novel uses about 100k output tokens of prose plus context for every segment, so with the defaults expect a few dollars per novel, more if you revise heavily.

## How it works

```
Create book ──► plan_book job: story bible + outline (v1)
                    │
Outline review ─────┤ approve ─► write part 1 ─► review ─► approve ─► write part 2 … (manual)
  (edit / revise)   └──────────► write_book: every part, quick QA after each (autopilot)
                                              │
Quality tab ◄─────────────────────────────────┘  full QA ─► apply / auto-fix / AI fix / ignore
Publish tab:  AI listing (description, keywords, categories) · cover · readiness checklist
Export tab:   EPUB · KDP print PDF · wrap cover · DOCX · TXT
```

The **API** (FastAPI, `app/api`) validates requests and queues jobs. The **worker** (`python -m app.worker`) claims jobs with `SELECT … FOR UPDATE SKIP LOCKED` and runs one job per book at a time. Each running job sends a heartbeat, and stuck jobs are failed automatically. Progress is shown live in the UI.

```
app/
  api/                 REST endpoints (books, outline, chapters, qa, publishing, jobs, system)
  services/
    generation.py      bible → outline → segmented chapter writing → summaries/continuity
    prompts.py         every prompt in one place
    llm.py             multi-provider client: fallback chains, rate-limit backoff, JSON, images, cost tracking
    jobs.py, tasks.py  durable job queue + handlers
    qa/                languagetool, rules, book_rules, editorial (AI), runner (scoring), fixes
    publishing/        manuscript model, epub, print_pdf, cover, docx/txt, metadata + readiness
    notifications.py   optional Slack
  catalog.py           formats, genres, audiences, trim sizes
  db/                  SQLAlchemy models + session
alembic/               migrations
scripts/               backup.sh / restore.sh (move your books to another machine)
frontend/              Next.js dashboard
tests/                 end-to-end and unit tests
```

Bulk import: `POST /api/books/import-csv` takes a CSV such as [samples/books_import_example.csv](samples/books_import_example.csv).

---

Originally developed by Abdullah Iftikhar. Fonts: Crimson Text and Bebas Neue (SIL Open Font License, see `app/assets/fonts`).
