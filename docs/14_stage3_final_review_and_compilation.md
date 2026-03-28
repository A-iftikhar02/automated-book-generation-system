# Stage 3: Final Review and Compilation Workflow

This stage handles the transition from individual chapter drafts to a single, cohesive book file. It incorporates a final Human-in-the-Loop (HITL) review checkpoint to ensure the book is ready for export.

## Final Review Process

Before the final `.txt` file can be compiled, an editor must perform a final review. This is managed via the `/book/review` endpoint.

### Review Statuses
- `no_notes_needed`: **Approved**. The book is ready for compilation without further changes.
- `yes`: **Revision/Notes Required**. The editor provides final feedback. Compilation is allowed only if the feedback notes are documented.
- `no`: **Paused**. The final compilation stage is explicitly halted.

## Compilation Gating Rules

The `/book/compile` endpoint enforces strict rules to prevent premature compilation:

1.  **Dependency Check**: The book and its chapters must exist in the database.
2.  **State Check**: A final review record must exist (initiated via `/book/review`).
3.  **Status Check**:
    - **Allowed** if status is `no_notes_needed`.
    - **Allowed** if status is `yes` AND `final_review_notes` is not empty.
    - **Blocked** if status is `yes` but notes are missing.
    - **Blocked** if status is `no` or empty (initial state).

## Book Output Status

The `book_output_status` field in the `final_drafts` table tracks the progress:
- `paused`: Initial state after a review is requested but before compilation.
- `compiled`: Set automatically after a successful run of the compilation logic.

## Event Logging

The system logs significant milestones during this stage:
- `final_review_requested`: When status is set to `yes`.
- `final_review_paused`: When status is set to `no`.
- `final_review_approved`: When status is set to `no_notes_needed`.
- `final_compilation_completed`: Upon successful file generation.
- `compile_blocked`: When a compilation attempt fails the gating rules (logs the specific reason).

## Final Output Behavior

- **File Format**: Plain text (`.txt`).
- **Location**: Local `outputs/` directory.
- **Naming Convention**: `generated_book_{book_id}.txt`.
- **Database**: The `output_file_path` is updated in Supabase for persistence.
