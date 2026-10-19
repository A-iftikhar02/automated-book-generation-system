"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { BookOpen, CirclePlus, LoaderCircle, Search } from "lucide-react";
import { useBooks, useCatalog } from "@/lib/hooks";
import { BOOK_STATUS_LABELS, categoryLabel, fmtNumber, genreLabel, jobLabel, partLabelFor, plural } from "@/lib/format";
import { errorMessage } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { BookCover } from "@/components/BookCover";
import { BookStatusBadge, ScoreBadge } from "@/components/badges";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { LinkButton } from "@/components/ui/link-button";
import { Progress } from "@/components/ui/progress";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

export default function LibraryPage() {
  const { data: books, isLoading, error } = useBooks();
  const { data: catalog } = useCatalog();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (books || []).filter(
      (b) =>
        (!needle || b.title.toLowerCase().includes(needle) || (b.subtitle || "").toLowerCase().includes(needle)) &&
        (!status || b.status === status) &&
        (!category || b.category === category),
    );
  }, [books, q, status, category]);

  const usedCategories = useMemo(() => [...new Set((books || []).map((b) => b.category))], [books]);

  return (
    <div>
      <PageHeader
        title="Library"
        description={books ? `${books.length} ${books.length === 1 ? "book" : "books"}` : "All your books"}
        actions={
          <LinkButton href="/books/new">
            <CirclePlus className="h-4 w-4" /> New book
          </LinkButton>
        }
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-[1fr_auto_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by title" className="pl-9" aria-label="Search by title" />
        </div>
        <Select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status" className="sm:w-44">
          <option value="">All statuses</option>
          {Object.entries(BOOK_STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </Select>
        <Select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Filter by category" className="sm:w-52">
          <option value="">All formats</option>
          {(catalog?.categories || []).filter((c) => usedCategories.includes(c.key)).map((c) => (
            <option key={c.key} value={c.key}>
              {c.label}
            </option>
          ))}
        </Select>
      </div>

      {error ? (
        <EmptyState icon={BookOpen} title="Could not load books">
          {errorMessage(error)}
        </EmptyState>
      ) : isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-44" />
          ))}
        </div>
      ) : !books?.length ? (
        <EmptyState icon={BookOpen} title="Your library is empty" action={<LinkButton href="/books/new">Create a book</LinkButton>}>
          Start a new book and it will appear here.
        </EmptyState>
      ) : !filtered.length ? (
        <EmptyState icon={Search} title="No matching books">
          Try a different search or clear the filters.
        </EmptyState>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((b) => {
            const label = partLabelFor(catalog, b.category);
            const pct = b.target_chapter_count ? b.parts_approved / b.target_chapter_count : 0;
            return (
              <li key={b.id}>
                <Link
                  href={`/books/${b.id}`}
                  className="group block h-full rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  <Card className="flex h-full gap-4 p-4 transition-all group-hover:border-blue-200 group-hover:shadow-md">
                    <BookCover bookId={b.id} hasCover={b.has_cover} version={b.cover_version} title={b.title} className="w-20 self-start" />
                    <div className="flex min-w-0 flex-1 flex-col">
                      <div className="flex items-start justify-between gap-2">
                        <h2 className="line-clamp-2 font-semibold leading-snug text-slate-900 group-hover:text-blue-700">{b.title}</h2>
                        {b.active_job && <LoaderCircle className="h-4 w-4 shrink-0 animate-spin text-blue-600" aria-label="Job running" />}
                      </div>
                      {b.subtitle && <p className="truncate text-xs text-slate-500">{b.subtitle}</p>}
                      <p className="mt-1 truncate text-xs text-slate-500">
                        {categoryLabel(catalog, b.category)} · {genreLabel(catalog, b.genre)}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        <BookStatusBadge status={b.status} />
                        <ScoreBadge score={b.quality_score} />
                      </div>
                      <div className="mt-auto pt-3">
                        <Progress value={pct} label={`${plural(label)} approved`} />
                        <div className="mt-1 flex justify-between gap-2 text-xs text-slate-500">
                          <span>
                            {b.parts_approved}/{b.target_chapter_count} {plural(label, b.target_chapter_count).toLowerCase()}
                          </span>
                          <span>{fmtNumber(b.words_written)} words</span>
                        </div>
                        {b.active_job && <p className="mt-1 truncate text-xs font-medium text-blue-700">{jobLabel(b.active_job)}…</p>}
                      </div>
                    </div>
                  </Card>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
