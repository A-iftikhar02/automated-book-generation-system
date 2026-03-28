# Final Book Compilation

## Overview
The **Final Compilation** stage aggregates all generated chapter drafts into a single, cohesive document. It marks the conclusion of the automated generation workflow and prepares the draft for the final human review.

## Implementation Details

### Compilation Logic
1.  **Retrieval**: The system fetches the book metadata (for the title) and all associated chapters from Supabase.
2.  **Ordering**: Chapters are sorted by `chapter_number` (ascending) to ensure the narrative flows correctly.
3.  **Formatting**: The `build_compiled_book_text` helper constructs a structured text block:
    -   Book Title header.
    -   Draft markers.
    -   Chapter headers with titles and their full content.
4.  **File Generation**: The compiled text is saved as a `.txt` file in the `/outputs` directory with the naming convention: `generated_book_<book_id>.txt`.
5.  **Persistence**:
    -   A new record is inserted into the `final_drafts` table with `book_output_status = 'compiled'`.
    -   The `books.status` is updated to `completed`.

## Validation Rules
- **Book Existence**: Returns `404` if the `book_id` is invalid.
- **Content Check**: Returns `400` if no chapters exist for the book. Compilation cannot proceed with an empty draft.

## File Naming Convention
- **Path**: `outputs/generated_book_[UUID].txt`
- **Purpose**: Unique identification of drafts linked to the database record.

## Current Status
- **File System Orchestration**: ✅ Complete. Directories are created automatically if missing.
- **Database Persistence**: ✅ Complete. `final_drafts` records capture the output path for future retrieval.
- **Content Quality**: ⏳ Mocked. While the structure is final, the content is still powered by simulation templates rather than Gemini.
