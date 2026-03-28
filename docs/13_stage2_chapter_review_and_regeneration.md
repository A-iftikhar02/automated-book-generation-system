# Stage 2: Chapter Generation, Review, and Regeneration

This document outlines the workflow and implementation details for Stage 2 of the Automated Book Generation System.

## Chapter Generation Workflow

The generation of chapters follows a strict sequential process with human-in-the-loop (HITL) review.

### 1. Sequential Gating
To ensure narrative continuity and high quality, chapter generation is gated by the following rules:
- **Outline Approval**: The latest outline must have a status of `no_notes_needed`.
- **Sequential Progression**: Chapter N can only be generated if Chapter N-1 has been generated and approved (`no_notes_needed`).
- **Duplicate Prevention**: Chapter N cannot be regenerated using the `/chapters/generate` endpoint if it already exists. For improvements, use `/chapter/regenerate`.

### 2. Context Chaining
During generation, the AI (Gemini) is provided with summaries of all previous chapters. This ensures that the current chapter maintains consistency in style, plot, and character development.

## Chapter Review Statuses

Every newly generated or regenerated chapter enters a `pending_review` state. The editor must review the content and set one of the following statuses via `POST /chapter/review`:

- `no_notes_needed`: **Approved**. The chapter is finalized, and the system can proceed to the next chapter.
- `yes`: **Revision Requested**. The editor provides `chapter_notes` detailing what needs to be changed. This enables the regeneration workflow.
- `no`: **Paused**. The workflow for this chapter (and subsequent ones) is paused.

## Chapter Regeneration

If a chapter is marked as `yes` (needs revision), the editor can trigger a regeneration via `POST /chapter/regenerate`.

- **Mechanism**: The system fetches the current chapter content, the editor's notes, and all previous chapter summaries.
- **AI Instruction**: Gemini is instructed to revise the existing content specifically addressing the editor's feedback while preserving continuity.
- **Versioning**: Currently, regeneration updates the existing chapter row in the database.
- **Loop**: After regeneration, the chapter returns to the `pending_review` state for a fresh round of review.

## API Endpoints

### POST `/chapter/review`
- **Purpose**: Mark a chapter as approved, needing revision, or paused.
- **Payload**: `book_id`, `chapter_number`, `chapter_notes_status`, `chapter_notes` (optional).

### POST `/chapter/regenerate`
- **Purpose**: AI-driven revision of a chapter based on feedback.
- **Payload**: `book_id`, `chapter_number`.

### GET `/chapter/status/{book_id}/{chapter_number}`
- **Purpose**: Helper endpoint to check existence and review status.

## MVP Limitations
- **In-place Updates**: Regeneration overwrites the current content rather than maintaining a visible version history in the database (unlike outlines).
- **Manual Progression**: The transition from chapter N to N+1 requires a separate API call.
