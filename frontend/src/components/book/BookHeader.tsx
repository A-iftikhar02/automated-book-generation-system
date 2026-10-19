"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSWRConfig } from "swr";
import { ArrowLeft, Trash2 } from "lucide-react";
import { api, paths } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { categoryLabel, fmtCost, fmtNumber, genreLabel, plural } from "@/lib/format";
import { BookCover } from "@/components/BookCover";
import { BookStatusBadge, ScoreBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { useBookCtx } from "./context";

export function BookHeader() {
  const { book, catalog, partLabel, coverVersion } = useBookCtx();
  const router = useRouter();
  const { mutate } = useSWRConfig();
  const { run, busy } = useAction();
  const [confirm, setConfirm] = useState(false);
  const wordsPct = book.target_word_count ? book.words_written / book.target_word_count : 0;

  return (
    <div className="mb-6">
      <Link href="/books" className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-slate-900">
        <ArrowLeft className="h-4 w-4" /> Library
      </Link>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <BookCover bookId={book.id} hasCover={book.has_cover} version={coverVersion} title={book.title} className="w-20 sm:w-24" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <BookStatusBadge status={book.status} />
            <ScoreBadge score={book.quality_score} />
            <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
              {book.review_mode === "autopilot" ? "Autopilot" : "Manual review"}
            </span>
          </div>
          <h1 className="mt-1 break-words text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{book.title}</h1>
          {book.subtitle && <p className="text-slate-600">{book.subtitle}</p>}
          <p className="mt-1 text-sm text-slate-500">
            {categoryLabel(catalog, book.category)} · {genreLabel(catalog, book.genre)}
            {book.author_name && <> · by {book.author_name}</>}
          </p>
          <div className="mt-3 grid max-w-xl grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
            <div className="col-span-2">
              <div className="flex justify-between text-xs text-slate-500">
                <span>
                  {fmtNumber(book.words_written)} / {fmtNumber(book.target_word_count)} words
                </span>
                <span>
                  {book.parts_approved}/{book.target_chapter_count} {plural(partLabel, book.target_chapter_count).toLowerCase()} approved
                </span>
              </div>
              <Progress value={wordsPct} className="mt-1" label="Words written" />
            </div>
            <div className="text-xs text-slate-500">
              AI cost <span className="block text-sm font-semibold text-slate-900">{fmtCost(book.cost_usd)}</span>
            </div>
          </div>
        </div>
        <Button variant="ghost" size="sm" className="self-start text-red-600 hover:bg-red-50 hover:text-red-700" onClick={() => setConfirm(true)}>
          <Trash2 className="h-4 w-4" /> Delete
        </Button>
      </div>
      <ConfirmDialog
        open={confirm}
        onClose={() => setConfirm(false)}
        title={`Delete “${book.title}”?`}
        description="This permanently deletes the book, its outline, every part and revision, QA results, cover and exports."
        confirmLabel="Delete book"
        destructive
        pending={busy}
        onConfirm={async () => {
          const ok = await run("delete", () => api.deleteBook(book.id).then(() => true), "Book deleted");
          if (ok) {
            await mutate(paths.books);
            router.push("/books");
          }
        }}
      />
    </div>
  );
}
