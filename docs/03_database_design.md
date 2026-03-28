# Database Design: Automated Book Generation System

## Schema Overview
The database schema for the **Automated Book Generation System** focuses on state management and content persistence. Each table tracks a stage of development or a piece of the content hierarchy.

## Tables & Fields

### 1. `books`
This is the root table for any generation project.
- `id` (uuid, primary key): Unique identifier.
- `title` (text): Book title.
- `status` (text): Enum value like `in_progress`, `completed`, or `paused`.
- `current_step` (text): Stage tracking (e.g., `outline_phase`, `chapter_phases`, `compiling_phase`).
- `meta_data` (jsonb): Generic bucket for AI system prompts or configuration.

### 2. `outlines`
Stores the chapter structure for a specific book.
- `id` (uuid, primary key): Unique identifier.
- `book_id` (uuid, foreign key): References `books.id`.
- `content` (text): The generated outline in markdown format.
- `notes` (text): User-provided feedback for the outline.
- `version` (int): Track iterations of the outline.

### 3. `chapters`
The core of the system. Each entry represents one chapter of a book.
- `id` (uuid, primary key): Unique identifier.
- `book_id` (uuid, foreign key): References `books.id`.
- `chapter_number` (int): Sequential index for the chapter.
- `title` (text): Chapter title from the outline.
- `content` (text): The full generated text of the chapter.
- `summary` (text): A concise summary of the chapter for context chaining.
- `status` (text): State tracking (`draft`, `review_needed`, `approved`, `regenerating`).

### 4. `final_drafts`
Metadata about compiled exports.
- `id` (uuid, primary key): Unique identifier.
- `book_id` (uuid, foreign key): References `books.id`.
- `file_path` (text): The path or URL to the final `.txt` document.
- `created_at` (timestamp): Tracking the date of completion.

## MVP Design Rationale
- **Foreign Key Constraints:** Ensure all data remains linked to a single `book_id`.
- **Status Fields:** Necessary for the human-in-the-loop and pause/resume logic.
- **Summary Column:** Essential for the context chaining strategy discussed in the architecture.
