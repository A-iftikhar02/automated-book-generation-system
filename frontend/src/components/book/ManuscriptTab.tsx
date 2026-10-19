"use client";

import { useState } from "react";
import { LoaderCircle, PenLine, ScrollText } from "lucide-react";
import { api } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { fmtNumber, plural } from "@/lib/format";
import { PartStatusBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { activeJobs, TEXT_JOBS, useBookCtx, WRITE_JOBS } from "./context";
import { ChapterPane } from "./ChapterPane";
import { UnwrittenPart } from "./UnwrittenPart";

export interface PartRow {
  number: number;
  title: string;
  status: string;
  words: number;
  target: number;
  written: boolean;
}

export function ManuscriptTab() {
  const { book, partLabel, selectedPart, setSelectedPart, refresh } = useBookCtx();
  const { run, pending } = useAction();
  const [confirmAll, setConfirmAll] = useState(false);
  const label = partLabel.toLowerCase();

  const chapters = new Map(book.chapters.map((c) => [c.number, c]));
  const planned = book.outline?.chapters || [];
  const numbers = [...new Set([...planned.map((p) => p.number), ...book.chapters.map((c) => c.number)])].sort((a, b) => a - b);
  const rows: PartRow[] = numbers.map((n) => {
    const ch = chapters.get(n);
    const plan = planned.find((p) => p.number === n);
    return {
      number: n,
      title: ch?.title || plan?.title || `${partLabel} ${n}`,
      status: ch ? ch.status : "not_written",
      words: ch?.word_count || 0,
      target: plan?.target_words || 0,
      written: !!ch,
    };
  });

  if (!rows.length) {
    return (
      <EmptyState icon={ScrollText} title="Nothing planned yet">
        The manuscript appears here once the outline exists.
      </EmptyState>
    );
  }

  const fallback = book.chapters.find((c) => c.status === "pending_review")?.number ?? book.next_part ?? rows[0].number;
  const selected = rows.find((r) => r.number === selectedPart) ?? rows.find((r) => r.number === fallback) ?? rows[0];
  const outlineApproved = book.outline?.status === "approved";
  const writeJobs = activeJobs(book, WRITE_JOBS);
  const busyParts = new Set(activeJobs(book, TEXT_JOBS).map((j) => j.payload?.number as number | undefined));
  const bookWide = book.jobs.some((j) => j.type === "write_book" || j.type === "autofix");

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-slate-500">
          {book.parts_written}/{rows.length} {plural(label)} written · {book.parts_approved} approved · {fmtNumber(book.words_written)} words
        </p>
        {outlineApproved && book.next_part && (
          <Button variant="accent" onClick={() => setConfirmAll(true)} disabled={writeJobs.length > 0} loading={pending === "all"}>
            {pending !== "all" && <PenLine className="h-4 w-4" />} Write all remaining
          </Button>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[17rem_1fr]">
        {/* Phone/tablet: compact select */}
        <div className="lg:hidden">
          <label htmlFor="part-select" className="sr-only">
            Choose a {label}
          </label>
          <Select id="part-select" value={selected.number} onChange={(e) => setSelectedPart(Number(e.target.value))}>
            {rows.map((r) => (
              <option key={r.number} value={r.number}>
                {partLabel} {r.number}: {r.title} {r.written ? `(${r.status.replace(/_/g, " ")})` : "(not written)"}
              </option>
            ))}
          </Select>
        </div>
        {/* Desktop: list */}
        <Card className="hidden self-start overflow-hidden lg:block">
          <nav aria-label={`${plural(partLabel)}`}>
            <ul className="max-h-[70vh] divide-y divide-slate-100 overflow-y-auto">
              {rows.map((r) => {
                const active = r.number === selected.number;
                const working = busyParts.has(r.number) || (bookWide && r.number === book.next_part);
                return (
                  <li key={r.number}>
                    <button
                      onClick={() => setSelectedPart(r.number)}
                      aria-current={active ? "true" : undefined}
                      className={cn(
                        "flex w-full flex-col gap-1 px-4 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500",
                        active ? "bg-blue-50" : "hover:bg-slate-50",
                      )}
                    >
                      <span className="flex items-center gap-2">
                        <span className={cn("text-xs font-bold", active ? "text-blue-700" : "text-slate-400")}>{r.number}</span>
                        <span className={cn("min-w-0 flex-1 truncate text-sm font-medium", r.written ? "text-slate-900" : "text-slate-500")}>{r.title}</span>
                        {working && <LoaderCircle className="h-3.5 w-3.5 animate-spin text-blue-600" aria-label="Job running" />}
                      </span>
                      <span className="flex items-center justify-between gap-2 pl-5">
                        <PartStatusBadge status={r.status} />
                        <span className="text-xs text-slate-500">{r.written ? `${fmtNumber(r.words)} w` : `~${fmtNumber(r.target)} w`}</span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
        </Card>

        <div className="min-w-0">
          {selected.written ? (
            <ChapterPane key={selected.number} number={selected.number} target={selected.target} />
          ) : (
            <UnwrittenPart key={selected.number} number={selected.number} />
          )}
        </div>
      </div>

      <ConfirmDialog
        open={confirmAll}
        onClose={() => setConfirmAll(false)}
        title={`Write all remaining ${plural(label)}?`}
        description={`Every unwritten ${label} from ${label} ${book.next_part} onward will be written in order without waiting for your approval (like autopilot). You can still revise them afterwards.`}
        confirmLabel="Write all"
        onConfirm={() => run("all", () => api.writeAll(book.id), "Writing all remaining parts").then(refresh)}
      />
    </div>
  );
}
