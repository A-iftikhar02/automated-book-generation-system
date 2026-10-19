"use client";

import { createContext, useContext } from "react";
import type { BookDetail, Catalog, Category, Job } from "@/lib/api";

export type TabId = "overview" | "outline" | "manuscript" | "quality" | "publish" | "export";

export interface BookContextValue {
  book: BookDetail;
  catalog: Catalog | undefined;
  category: Category | undefined;
  /** "Chapter", "Scene", "Story", "Poem"... */
  partLabel: string;
  /** False when OpenRouter isn't configured (AI endpoints will 503). */
  aiReady: boolean;
  /** Revalidate everything cached for this book. */
  refresh: () => Promise<unknown>;
  goTo: (tab: TabId, part?: number) => void;
  selectedPart: number | null;
  /** Cache-busting token for the cover image (from the API's cover_version). */
  coverVersion: string;
  setSelectedPart: (n: number | null) => void;
}

const BookContext = createContext<BookContextValue | null>(null);
export const BookProvider = BookContext.Provider;

export function useBookCtx(): BookContextValue {
  const ctx = useContext(BookContext);
  if (!ctx) throw new Error("useBookCtx must be used inside <BookProvider>");
  return ctx;
}

/** Active jobs of the given types (optionally only those for part `n`). */
export function activeJobs(book: BookDetail, types: string[], n?: number): Job[] {
  return book.jobs.filter(
    (j) => types.includes(j.type) && (n === undefined || j.payload?.number === undefined || j.payload.number === n),
  );
}

export const WRITE_JOBS = ["write_chapter", "write_book", "revise_chapter"];
export const TEXT_JOBS = ["write_chapter", "write_book", "revise_chapter", "autofix", "ai_fix"];
