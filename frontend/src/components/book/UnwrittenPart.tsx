"use client";

import { useState } from "react";
import { PenLine } from "lucide-react";
import { api } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { fmtNumber } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { activeJobs, useBookCtx, WRITE_JOBS } from "./context";

/** A planned part that hasn't been written: shows the plan and (when allowed) a Write button. */
export function UnwrittenPart({ number }: { number: number }) {
  const { book, partLabel, refresh, goTo } = useBookCtx();
  const { run, busy } = useAction();
  const [notes, setNotes] = useState("");
  const plan = book.outline?.chapters.find((c) => c.number === number);
  const label = partLabel.toLowerCase();
  const prev = book.chapters.find((c) => c.number === number - 1);
  const writing = activeJobs(book, WRITE_JOBS);
  const thisJob = book.jobs.find((j) => (j.type === "write_chapter" && j.payload?.number === number) || (j.type === "write_book" && book.next_part === number));

  let blocker: string | null = null;
  if (book.outline?.status !== "approved") blocker = "Approve the outline before writing.";
  else if (number !== book.next_part) blocker = `Write ${label} ${book.next_part ?? number - 1} first.`;
  else if (number > 1 && prev && prev.status !== "approved") blocker = `Approve ${label} ${number - 1} before writing ${label} ${number}.`;
  else if (writing.length) blocker = "Another part is being written.";

  return (
    <Card className="p-4 sm:p-6">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        {partLabel} {number} · not written
      </p>
      <h2 className="mt-1 text-xl font-semibold text-slate-900">{plan?.title || `${partLabel} ${number}`}</h2>
      {plan && <p className="mt-1 text-sm text-slate-500">Target ~{fmtNumber(plan.target_words)} words</p>}
      {plan?.synopsis && <p className="mt-4 text-sm leading-relaxed text-slate-700">{plan.synopsis}</p>}
      {plan?.beats?.length ? (
        <ul className="mt-3 list-disc space-y-0.5 pl-5 text-sm text-slate-600">
          {plan.beats.map((b, i) => (
            <li key={i}>{b}</li>
          ))}
        </ul>
      ) : null}

      <div className="mt-6 border-t border-slate-100 pt-5">
        {thisJob ? (
          <p className="flex items-center gap-2 text-sm font-medium text-blue-700">
            <Spinner /> {thisJob.message || `Writing ${label} ${number}…`}
          </p>
        ) : blocker ? (
          <div className="flex flex-col gap-2 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <p>{blocker}</p>
            {book.outline?.status !== "approved" && (
              <Button size="sm" variant="outline" onClick={() => goTo("outline")}>
                Review outline
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="write-notes">Notes for the writer (optional)</Label>
              <Textarea id="write-notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. Open with dialogue; keep the reveal for the last scene." />
            </div>
            <Button loading={busy} onClick={() => run("write", () => api.writeChapter(book.id, number, notes.trim() || undefined), `Writing ${label} ${number}`).then(refresh)}>
              {!busy && <PenLine className="h-4 w-4" />} Write {label} {number}
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
