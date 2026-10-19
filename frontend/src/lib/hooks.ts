"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import {
  paths,
  type BookDetail,
  type BookSummary,
  type Catalog,
  type Chapter,
  type ExportItem,
  type Issue,
  type IssueFilters,
  type Job,
  type ModelCatalog,
  type Outline,
  type QAOverview,
  type Readiness,
  type Revision,
  type SystemStatus,
} from "./api";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "./api";

const STATIC = { revalidateOnFocus: false, dedupingInterval: 60_000 };

export const useCatalog = () => useSWR<Catalog>(paths.catalog, { ...STATIC, revalidateIfStale: false });
export const useSystemStatus = (refreshInterval = 30_000) => useSWR<SystemStatus>(paths.status, { refreshInterval });
export const useModels = (enabled = true) =>
  useSWR<ModelCatalog>(enabled ? paths.models : null, { ...STATIC, shouldRetryOnError: false });

export const useBooks = () =>
  useSWR<BookSummary[]>(paths.books, {
    refreshInterval: (data) => (data?.some((b) => b.active_job) ? 4000 : 30_000),
  });

/** Book detail: polls fast while jobs run, slowly otherwise. */
export const useBook = (id: string) =>
  useSWR<BookDetail>(id ? paths.book(id) : null, {
    refreshInterval: (data) => (data?.jobs.length ? 2000 : 15_000),
  });

export const useActiveJobs = () =>
  useSWR<Job[]>(paths.jobs({ active: true }), {
    refreshInterval: (data) => (data?.length ? 2500 : 15_000),
  });

export const useBookJobs = (id: string) => useSWR<Job[]>(paths.jobs({ book_id: id, limit: 20 }));
export const useOutlines = (id: string, enabled = true) => useSWR<Outline[]>(enabled ? paths.outlines(id) : null);
export const useChapter = (id: string, n: number | null) =>
  useSWR<Chapter>(n ? paths.chapter(id, n) : null, { revalidateOnFocus: false });
export const useRevisions = (id: string, n: number | null) => useSWR<Revision[]>(n ? paths.revisions(id, n) : null);
export const useQa = (id: string) => useSWR<QAOverview>(paths.qa(id));
export const useIssues = (id: string, filters: IssueFilters) =>
  useSWR<Issue[]>(paths.issues(id, filters), { keepPreviousData: true });
export const useReadiness = (id: string) => useSWR<Readiness>(paths.readiness(id));
export const useExports = (id: string) => useSWR<ExportItem[]>(paths.exports(id));

/** Revalidate every cached key belonging to a book (detail, QA, exports, chapters, jobs...). */
export function useRefreshBook(id: string) {
  const { mutate } = useSWRConfig();
  return useCallback(
    () =>
      mutate(
        (key) =>
          typeof key === "string" &&
          (key.startsWith(paths.book(id)) || key.startsWith("/api/jobs") || key === paths.books),
      ),
    [id, mutate],
  );
}

/**
 * Wrap an async mutation: tracks pending state, shows the backend `detail` as an error toast,
 * and optionally a success toast. Returns `undefined` on failure.
 */
export function useAction() {
  const toast = useToast();
  const [pending, setPending] = useState<string | null>(null);
  const run = useCallback(
    async <T,>(key: string, fn: () => Promise<T>, success?: string | ((r: T) => string)): Promise<T | undefined> => {
      setPending(key);
      try {
        const result = await fn();
        if (success) toast.success(typeof success === "function" ? success(result) : success);
        return result;
      } catch (err) {
        toast.error(errorMessage(err));
        return undefined;
      } finally {
        setPending(null);
      }
    },
    [toast],
  );
  return { run, pending, busy: pending !== null };
}

/** Call `onFinish` whenever a job that was active disappears from the active list. */
export function useJobsFinished(jobs: Job[] | undefined, onFinish: (finishedIds: string[]) => void) {
  const prev = useRef<Set<string>>(new Set());
  const cb = useRef(onFinish);
  useEffect(() => {
    cb.current = onFinish;
  });
  useEffect(() => {
    if (!jobs) return;
    const now = new Set(jobs.map((j) => j.id));
    const finished = [...prev.current].filter((id) => !now.has(id));
    prev.current = now;
    if (finished.length) cb.current(finished);
  }, [jobs]);
}
