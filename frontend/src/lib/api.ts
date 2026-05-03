import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
});

export interface Book {
  id: string;
  title: string;
  status: string;
  notes_on_outline_before: string;
  created_at: string;
}

export interface Outline {
  id: string;
  book_id: string;
  outline_text: string;
  status_outline_notes: string;
  version: number;
  notes_on_outline_after: string | null;
}

export interface Chapter {
  id: string;
  book_id: string;
  chapter_number: number;
  chapter_title: string;
  content: string;
  summary: string;
  chapter_notes_status: string;
  status: string;
  chapter_notes?: string;
}

export interface FinalDraft {
  id: string;
  book_id: string;
  final_review_notes: string | null;
  final_review_notes_status: string;
  output_file_path: string | null;
  book_output_status: string;
}

export const fetchBooks = async (): Promise<Book[]> => {
  const { data } = await api.get('/books');
  return data;
};

export const fetchBookDetails = async (id: string): Promise<{ book: Book, outline?: Outline, chapters: Chapter[], finalDraft?: FinalDraft }> => {
  const { data } = await api.get(`/books/${id}`);
  return data;
};

// Real endpoints mapped to FastAPI backend

export const generateOutline = async (title: string, notes: string) => {
  const { data } = await api.post('/outline/generate', {
    title,
    notes_on_outline_before: notes
  });
  return data;
};

export const reviewOutline = async (book_id: string, status: string, notes?: string) => {
  const { data } = await api.post('/outline/review', {
    book_id,
    status_outline_notes: status,
    notes_on_outline_after: notes
  });
  return data;
};

export const regenerateOutline = async (book_id: string) => {
  const { data } = await api.post('/outline/regenerate', {
    book_id
  });
  return data;
};

export const generateChapter = async (book_id: string, chapter_number: number) => {
  const { data } = await api.post('/chapters/generate', {
    book_id,
    chapter_number
  });
  return data;
};

export const reviewChapter = async (book_id: string, chapter_number: number, status: string, notes?: string) => {
  const { data } = await api.post('/chapter/review', {
    book_id,
    chapter_number,
    chapter_notes_status: status,
    chapter_notes: notes
  });
  return data;
};

export const regenerateChapter = async (book_id: string, chapter_number: number) => {
  const { data } = await api.post('/chapter/regenerate', {
    book_id,
    chapter_number
  });
  return data;
};

export const getChapterStatus = async (book_id: string, chapter_number: number) => {
  const { data } = await api.get(`/chapter/status/${book_id}/${chapter_number}`);
  return data;
};

export const reviewBook = async (book_id: string, status: string, notes?: string) => {
  const { data } = await api.post('/book/review', {
    book_id,
    final_review_notes_status: status,
    final_review_notes: notes
  });
  return data;
};

export const compileBook = async (book_id: string) => {
  const { data } = await api.post('/book/compile', {
    book_id
  });
  return data;
};
