# API Design: Automated Book Generation System

## Endpoint Overview

| Method | Endpoint | Purpose | Status |
| :--- | :--- | :--- | :--- |
| GET | `/` | Root Welcome Message | **Implemented** |
| GET | `/health` | Server Health Check | **Implemented** |
| POST | `/outline/generate` | Start book construction by creating an outline | **Implemented Skeleton** |
| POST | `/chapters/generate` | Generate specific chapters in sequence | **Implemented Skeleton** |
| POST | `/book/compile` | Merge chapters into a final .txt file | **Implemented Skeleton** |

---

## Detailed Endpoint Specification

### 1. GET `/`
- **Purpose:** Simple entry point to confirm the service is live.
- **Output:** Welcome message and version info.

### 2. POST `/outline/generate`
- **Purpose:** Initiates the generation of a new book outline based on a concept or title.
- **Input:** `OutlineGenerateRequest` (`title`, `notes_on_outline_before`).
- **Output:** `OutlineGenerateResponse` (`message`, `book_id`, `outline_status`).
- **Expectations:** This will later integrate with Gemini to generate a JSON/Markdown structure of chapters.

### 3. POST `/chapters/generate`
- **Purpose:** Generates the content for a specific chapter within a book.
- **Input:** `ChapterGenerateRequest` (`book_id`, `chapter_number`).
- **Output:** `ChapterGenerateResponse` (`message`, `chapter_number`, `chapter_status`).
- **Expectations:** This endpoint will handle context chaining (previous summaries) and long-running AI tasks.

### 4. POST `/book/compile`
- **Purpose:** Aggregates all approved chapters for a book and writes them to a final text document.
- **Input:** `CompileBookRequest` (`book_id`).
- **Output:** `CompileBookResponse` (`message`, `output_path`, `book_output_status`).
- **Expectations:** Files will be stored in the `/outputs` folder.
