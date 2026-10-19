"use client";

import Link from "next/link";
import { useSWRConfig } from "swr";
import { BookOpen, CirclePlus, DollarSign, Feather, Gauge, Library, LoaderCircle, PenLine } from "lucide-react";
import { paths } from "@/lib/api";
import { useActiveJobs, useBooks, useCatalog, useJobsFinished } from "@/lib/hooks";
import { categoryLabel, fmtAgo, fmtCost, fmtNumber, genreLabel, partLabelFor } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { SetupBanner } from "@/components/SetupBanner";
import { BookCover } from "@/components/BookCover";
import { BookStatusBadge, ScoreBadge } from "@/components/badges";
import { JobProgress } from "@/components/JobProgress";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";

function Stat({ label, value, icon: Icon, hint }: { label: string; value: React.ReactNode; icon: React.ComponentType<{ className?: string }>; hint?: string }) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
        <Icon className="h-4 w-4 text-slate-400" />
      </div>
      <p className="mt-2 text-2xl font-bold tabular-nums text-slate-900">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </Card>
  );
}

export default function DashboardPage() {
  const { data: books, isLoading, error } = useBooks();
  const { data: catalog } = useCatalog();
  const { data: jobs } = useActiveJobs();
  const { mutate } = useSWRConfig();
  useJobsFinished(jobs, () => mutate(paths.books));

  const list = books || [];
  const scored = list.filter((b) => b.quality_score !== null);
  const avgScore = scored.length ? scored.reduce((s, b) => s + (b.quality_score || 0), 0) / scored.length : null;
  const inProgress = list.filter((b) => b.status !== "editing").length;
  const words = list.reduce((s, b) => s + b.words_written, 0);
  const spend = list.reduce((s, b) => s + b.cost_usd, 0);
  const recent = [...list].sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, 5);
  const titles = new Map(list.map((b) => [b.id, b]));

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Your books, what the AI is working on, and what needs your review."
        actions={
          <LinkButton href="/books/new">
            <CirclePlus className="h-4 w-4" /> New book
          </LinkButton>
        }
      />
      <SetupBanner />

      {isLoading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          <Stat label="Books" value={list.length} icon={Library} />
          <Stat label="Words written" value={fmtNumber(words)} icon={Feather} />
          <Stat label="In progress" value={inProgress} icon={PenLine} hint="Not yet in editing" />
          <Stat label="Avg. quality" value={avgScore === null ? "–" : avgScore.toFixed(1)} icon={Gauge} hint={scored.length ? `${scored.length} book(s) checked` : "Run QA on a book"} />
          <Stat label="AI spend" value={fmtCost(spend)} icon={DollarSign} />
        </div>
      )}

      {jobs && jobs.length > 0 && (
        <Card className="mt-6 border-blue-200">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <LoaderCircle className="h-4 w-4 animate-spin text-blue-600" /> Active jobs ({jobs.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {jobs.map((job) => {
              const book = job.book_id ? titles.get(job.book_id) : undefined;
              return (
                <JobProgress
                  key={job.id}
                  job={job}
                  partLabel={book ? partLabelFor(catalog, book.category) : undefined}
                  title={
                    book ? (
                      <Link href={`/books/${book.id}`} className="font-medium text-blue-700 hover:underline">
                        {book.title}
                      </Link>
                    ) : undefined
                  }
                  onChange={() => mutate(paths.jobs({ active: true }))}
                />
              );
            })}
          </CardContent>
        </Card>
      )}

      <div className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Recently updated</h2>
          {list.length > 0 && (
            <Link href="/books" className="text-sm font-medium text-blue-600 hover:underline">
              View library
            </Link>
          )}
        </div>
        {error ? (
          <EmptyState icon={BookOpen} title="Could not load books">
            {String(error.message || error)}
          </EmptyState>
        ) : isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
        ) : recent.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="No books yet"
            action={
              <LinkButton href="/books/new">Create your first book</LinkButton>
            }
          >
            Pick a format and genre, describe your idea, and BookPilot will plan an outline for you to review.
          </EmptyState>
        ) : (
          <Card className="divide-y divide-slate-100">
            {recent.map((b) => {
              const pct = b.target_chapter_count ? b.parts_approved / b.target_chapter_count : 0;
              return (
                <Link
                  key={b.id}
                  href={`/books/${b.id}`}
                  className="flex items-center gap-4 p-4 transition-colors first:rounded-t-xl last:rounded-b-xl hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500"
                >
                  <BookCover bookId={b.id} hasCover={b.has_cover} version={b.cover_version} title={b.title} className="w-10" />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate font-semibold text-slate-900">{b.title}</span>
                      <BookStatusBadge status={b.status} />
                      <ScoreBadge score={b.quality_score} />
                      {b.active_job && <LoaderCircle className="h-3.5 w-3.5 animate-spin text-blue-600" aria-label="Job running" />}
                    </div>
                    <p className="mt-0.5 truncate text-xs text-slate-500">
                      {categoryLabel(catalog, b.category)} · {genreLabel(catalog, b.genre)} · {fmtNumber(b.words_written)} words · updated {fmtAgo(b.updated_at)}
                    </p>
                  </div>
                  <div className="hidden w-32 shrink-0 sm:block">
                    <Progress value={pct} label="Parts approved" />
                    <p className="mt-1 text-right text-xs text-slate-500">
                      {b.parts_approved}/{b.target_chapter_count} approved
                    </p>
                  </div>
                </Link>
              );
            })}
          </Card>
        )}
      </div>
    </div>
  );
}
