"use client";

import { useState } from "react";
import { Check, History, Pencil, Save, WandSparkles } from "lucide-react";
import { useSWRConfig } from "swr";
import { api, errorMessage, paths } from "@/lib/api";
import { useAction, useChapter } from "@/lib/hooks";
import { fmtAgo, fmtNumber } from "@/lib/format";
import { PartStatusBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { activeJobs, TEXT_JOBS, useBookCtx } from "./context";
import { Reader } from "./Reader";
import { RevisionHistory } from "./RevisionHistory";

function countWords(text: string) {
  return (text.match(/[A-Za-z0-9À-ɏ]+(?:['’-][A-Za-z0-9À-ɏ]+)*/g) || []).length;
}

function ReviseDialog({ open, onClose, number }: { open: boolean; onClose: () => void; number: number }) {
  const { book, partLabel, refresh } = useBookCtx();
  const { run, busy } = useAction();
  const [instructions, setInstructions] = useState("");
  const [mode, setMode] = useState<"revise" | "rewrite">("revise");
  const label = partLabel.toLowerCase();
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`Revise ${label} ${number}`}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            loading={busy}
            disabled={instructions.trim().length < 3}
            onClick={async () => {
              const job = await run("revise", () => api.reviseChapter(book.id, number, instructions.trim(), mode), "Revision queued");
              if (job) {
                setInstructions("");
                onClose();
                refresh();
              }
            }}
          >
            {mode === "rewrite" ? "Rewrite" : "Revise"}
          </Button>
        </>
      }
    >
      <fieldset className="mb-4">
        <legend className="mb-2 text-sm font-medium text-slate-700">Mode</legend>
        <div className="grid gap-2 sm:grid-cols-2">
          {(
            [
              ["revise", "Revise", "Targeted edits that keep what works."],
              ["rewrite", "Rewrite", "Write the part again from scratch using your notes."],
            ] as const
          ).map(([id, title, body]) => (
            <label
              key={id}
              className={cn(
                "cursor-pointer rounded-lg border p-3 text-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-blue-500",
                mode === id ? "border-blue-500 bg-blue-50/50" : "border-slate-200",
              )}
            >
              <input type="radio" name="revise-mode" value={id} checked={mode === id} onChange={() => setMode(id)} className="sr-only" />
              <span className="font-semibold text-slate-900">{title}</span>
              <span className="mt-0.5 block text-xs text-slate-500">{body}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <Label htmlFor="revise-notes">Instructions</Label>
      <Textarea
        id="revise-notes"
        className="mt-2"
        rows={6}
        value={instructions}
        onChange={(e) => setInstructions(e.target.value)}
        placeholder="e.g. Slow down the reveal, cut the repeated descriptions of the lantern, give Ysolde more agency."
      />
    </Dialog>
  );
}

export function ChapterPane({ number, target }: { number: number; target: number }) {
  const { book, category, partLabel, refresh } = useBookCtx();
  const { mutate } = useSWRConfig();
  const { data: chapter, error, isLoading } = useChapter(book.id, number);
  const { run, pending } = useAction();
  const [editing, setEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState("");
  const [draft, setDraft] = useState("");
  const [cont, setCont] = useState(true);
  const [reviseOpen, setReviseOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const label = partLabel.toLowerCase();
  const brief = book.chapters.find((c) => c.number === number);
  const jobs = activeJobs(book, TEXT_JOBS, number);
  const locked = jobs.length > 0;
  const manual = book.review_mode === "manual";
  const hasNext = (book.outline?.chapters || []).some((c) => c.number === number + 1);

  if (error) return <Card className="p-6 text-sm text-red-600">{errorMessage(error)}</Card>;
  if (isLoading || !chapter) return <Skeleton className="h-96" />;

  const words = editing ? countWords(draft) : chapter.word_count;
  const pct = target ? Math.round((words / target) * 100) : null;
  // The cached chapter can lag the book poll by a request; prefer the brief's status.
  const status = brief?.status ?? chapter.status;

  const save = async () => {
    const saved = await run("save", () => api.saveChapter(book.id, number, { title: draftTitle.trim(), content: draft }), "Saved");
    if (saved) {
      mutate(paths.chapter(book.id, number), saved, { revalidate: false });
      setEditing(false);
      refresh();
    }
  };

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-100 p-4 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              {partLabel} {number} · revision {chapter.revision} · updated {fmtAgo(chapter.updated_at)}
            </p>
            {editing ? (
              <Input value={draftTitle} onChange={(e) => setDraftTitle(e.target.value)} className="mt-1 text-lg font-semibold" aria-label="Title" maxLength={300} />
            ) : (
              <h2 className="mt-1 break-words text-xl font-semibold text-slate-900">{chapter.title}</h2>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-500">
              <PartStatusBadge status={status} />
              <span className={cn(pct !== null && (pct < 70 || pct > 140) && "font-medium text-amber-700")}>
                {fmtNumber(words)} {target ? `/ ${fmtNumber(target)}` : ""} words{pct !== null ? ` (${pct}%)` : ""}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {editing ? (
              <>
                <Button variant="ghost" onClick={() => setEditing(false)} disabled={pending === "save"}>
                  Cancel
                </Button>
                <Button onClick={save} loading={pending === "save"} disabled={!draftTitle.trim() || !draft.trim()}>
                  {pending !== "save" && <Save className="h-4 w-4" />} Save
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline" size="sm" onClick={() => setHistoryOpen(true)}>
                  <History className="h-3.5 w-3.5" /> History
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={locked}
                  onClick={() => {
                    setDraftTitle(chapter.title);
                    setDraft(chapter.content);
                    setEditing(true);
                  }}
                >
                  <Pencil className="h-3.5 w-3.5" /> Edit
                </Button>
                <Button variant="outline" size="sm" disabled={locked} onClick={() => setReviseOpen(true)}>
                  <WandSparkles className="h-3.5 w-3.5" /> Revise
                </Button>
              </>
            )}
          </div>
        </div>

        {status === "changes_requested" && chapter.feedback && (
          <p className="mt-3 rounded-lg bg-blue-50 p-3 text-sm text-blue-900">
            <span className="font-semibold">Revision requested:</span> {chapter.feedback}
          </p>
        )}
        {locked && (
          <p className="mt-3 flex items-center gap-2 text-sm font-medium text-blue-700">
            <Spinner /> {jobs[0].message || "Working on this part…"}
          </p>
        )}

        {status !== "approved" && !editing && (
          <div className="mt-4 flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50/60 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm text-amber-900">
              <p className="font-semibold">Ready for your review</p>
              {manual && hasNext && (
                <Checkbox
                  id="continue-writing"
                  className="mt-2"
                  checked={cont}
                  onChange={setCont}
                  label={`Continue writing ${label} ${number + 1} after approval`}
                />
              )}
            </div>
            <Button
              loading={pending === "approve"}
              disabled={locked}
              onClick={async () => {
                const updated = await run("approve", () => api.approveChapter(book.id, number, cont), `${partLabel} ${number} approved`);
                if (updated) {
                  mutate(paths.book(book.id), updated, { revalidate: false });
                  mutate(paths.chapter(book.id, number));
                }
              }}
            >
              {pending !== "approve" && <Check className="h-4 w-4" />} Approve {label}
            </Button>
          </div>
        )}
      </div>

      <div className="p-4 sm:p-8">
        {editing ? (
          <div className="space-y-2">
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={28}
              className="font-serif text-base leading-7"
              aria-label={`${partLabel} text`}
            />
            <p className="text-xs text-slate-500">
              Separate paragraphs with a blank line. Use <code>* * *</code> on its own line for a scene break and <code>*text*</code> for italics.
            </p>
          </div>
        ) : (
          <Reader content={chapter.content} verse={category?.structure === "poems"} />
        )}
      </div>

      <ReviseDialog open={reviseOpen} onClose={() => setReviseOpen(false)} number={number} />
      <RevisionHistory open={historyOpen} onClose={() => setHistoryOpen(false)} number={number} currentRevision={chapter.revision} />
    </Card>
  );
}
