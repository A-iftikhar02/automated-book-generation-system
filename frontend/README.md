# Agentic Book Generator - Frontend

This is a Next.js frontend for the FastAPI-based Automated Book Generation System. It provides a clean, responsive admin/editor dashboard for human-in-the-loop book generation.

## Stack
- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS
- Axios

## Setup Instructions

1. **Prerequisites**: Ensure you have Node.js (v18+) and npm installed.
2. **Install Dependencies**:
   ```bash
   cd frontend
   npm install
   ```
3. **Environment Variables**:
   By default, the `.env.local` file points to the local backend:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
4. **Run the Development Server**:
   ```bash
   npm run dev
   ```
5. **Access the App**: Open [http://localhost:3000](http://localhost:3000) in your browser.

## Integration Notes

### Missing Backend Endpoints (TODO)
During the creation of the frontend, the following backend endpoints were identified as missing and have been **mocked** in `src/lib/api.ts` so the frontend doesn't break:
- `GET /books`: To list all books on the dashboard.
- `GET /books/{id}`: To get the full details of a book, its outline, chapters, and final draft status.

Please implement these missing GET endpoints in the FastAPI backend (`app/main.py`) to serve real data to the dashboard.

### CORS Configuration
CORS has been added to the FastAPI backend (`app/main.py`) to allow requests from `http://localhost:3000`. If you run the frontend on a different port, update the `allow_origins` array in `app/main.py`.

## Pages
- `/`: Dashboard showing the list of generated books.
- `/books/new`: Page to start a new book generation by submitting title and initial notes.
- `/books/[id]`: Detail page for a specific book showing Outline Review, Chapter Generation, and Final Compilation phases.
