# Gemini AI Integration

## Overview
The **Gemini AI Integration** replaces the initial mock generation logic with real-world generative power. By connecting the FastAPI backend to Google's Gemini models, the system can now produce coherent book outlines, full-length chapters, and narrative summaries.

## Service Layer Design
All AI logic is encapsulated within `app/services/llm_service.py`. This ensures:
- **Separation of Concerns**: The API routes (`app/main.py`) only care about request/response flow, while the service layer at `llm_service.py` handles prompt engineering and AI communication.
- **Model Consistency**: We use the `gemini-1.5-flash` model for high-speed, cost-effective generation.

## Key AI Functions

### 1. Outline Generation
- **Input**: Book title and editor notes.
- **Prompt**: Focuses on creating a logical, chapter-by-chapter progression.
- **Output**: A Markdown-formatted list of chapters.

### 2. Chapter Generation
- **Input**: Title, full outline, current chapter index, and previous chapter summaries.
- **Prompt**: Instructs the AI to maintain a consistent tone, respect the outline, and use the provided summaries to avoid contradicting earlier plot points.
- **Mechanism**: Splits the response into a `chapter_title` and `chapter_content` using a custom delimiter (`---CONTENT_START---`).

### 3. Chapter Summarization
- **Purpose**: After every chapter generation, Gemini creates a concise paragraph summarizing the key events.
- **Result**: This summary is stored in the `chapters` table and fed into the next chapter's generation prompt.

## Error Handling & Fallbacks
- **Validation**: If a `GEMINI_API_KEY` is missing, the service logs a warning.
- **Readable Errors**: Gemini API failures (like quota limits or network issues) are caught and returned as `502 Bad Gateway` errors with a descriptive `ValueError` message to the user.
- **Parsing Robustness**: If the AI fails to follow the title/content split format, the system gracefully falls back to using the raw response as content.

## Context Chaining Recap
The combination of **Supabase Persistence** and **Gemini Integration** allows for "Context Chaining":
1.  **Ch 1** is generated -> Summary 1 is saved.
2.  **Ch 2** is generated -> Uses Summary 1 for context -> Summary 2 is saved.
3.  **Ch 3** is generated -> Uses Summary 1 + Summary 2 for context.

This ensures the AI never "forgets" the story without needing to resubmit hundreds of pages of text in every request.

## Future Improvements
- **Prompt Tuning**: Refining the "voice" of the author.
- **Temperature Controls**: Allowing users to adjust the "creativity" of the generation.
- **Multi-model Support**: Switching to `gemini-pro` for complex narrative arcs.
