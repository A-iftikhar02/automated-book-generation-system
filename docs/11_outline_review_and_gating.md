# Outline Review and Workflow Gating

## Overview
To ensure high-quality book generation, the system includes a **Human-in-the-Loop (HITL)** stage for the skeleton outline. This allows editors to review, approve, or request changes before the AI begins the resource-intensive process of drafting full chapters.

## Gating Mechanism
The system enforces a strict "gate" at the chapter generation stage. A chapter cannot be generated unless the latest version of the outline has been explicitly approved by a human.

### Chapter Generation Rules:
- **`pending_review`**: Chapter generation is BLOCKED. (Default state after generation).
- **`yes`**: Chapter generation is BLOCKED. (Indicates changes are needed).
- **`no`**: Chapter generation is BLOCKED. (Stops the workflow entirely).
- **`no_notes_needed`**: Chapter generation is ALLOWED.

## Review Status Meanings
| Status | Meaning | Next Step |
| :--- | :--- | :--- |
| `pending_review` | Newly generated; needs eyes. | Editor calls `/outline/review`. |
| `yes` | Changes requested. | Editor provides feedback; calls `/outline/regenerate`. |
| `no` | Projects paused/cancelled. | Workflow stops. |
| `no_notes_needed` | Outline is perfect. | Proceed to `/chapters/generate`. |

## Iterative Outline Generation
If an editor sets the status to `yes` and provides `notes_on_outline_after`, they can call the **Regenerate** endpoint.
- **`POST /outline/regenerate`**:
    - Fetches the previous outline, original notes, and the new editor feedback.
    - Uses Gemini to produce a refined version (e.g., Version 2).
    - Sets the new version back to `pending_review`.

## Bulk Initiation
- **`POST /outline/from-file`**:
    - Supports CSV uploads (MVP).
    - Expects columns: `title`, `notes_on_outline_before`.
    - Allows editors to kick off book generation without manual data entry in the API UI.

## Database Persistence
- The `outlines` table uses a `version` integer to track iterations.
- The `status_outline_notes` column functions as the primary state-machine driver for the whole project.
