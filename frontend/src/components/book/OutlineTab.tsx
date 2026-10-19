"use client";

import { useState } from "react";
import { Check, ChevronDown, History, MessageSquare, Pencil } from "lucide-react";
import { api, type Outline, type OutlinePart } from "@/lib/api";
import { useAction, useOutlines } from "@/lib/hooks";
import { capitalize, fmtDate, fmtNumber, humanize, plural } from "@/lib/format";
import { PartStatusBadge } from "@/components/badges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { activeJobs, useBookCtx } from "./context";
import { OutlineEditor } from "./OutlineEditor";

function PartList({ parts, showStatus = true }: { parts: OutlinePart[]; showStatus?: boolean }) {
  const { book, partLabel, goTo } = useBookCtx();
  const byNumber = new Map(book.chapters.map((c) => [c.number, c]));
  return (
    <ol className="space-y-3">
      {parts.map((p) => {
        const ch = byNumber.get(p.number);
        return (
          <li key={p.number} className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="min-w-0 font-semibold text-slate-900">
                <span className="mr-2 text-slate-400">
                  {partLabel} {p.number}
                </span>
                {p.title}
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">~{fmtNumber(p.target_words)} words</span>
                {showStatus && (
                  <button onClick={() => goTo("manuscript", p.number)} className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500" aria-label={`Open ${partLabel} ${p.number} in manuscript`}>
                    <PartStatusBadge status={ch ? ch.status : "not_written"} />
                  </button>
                )}
              </div>
            </div>
            {p.synopsis && <p className="mt-2 text-sm text-slate-600">{p.synopsis}</p>}
            {p.beats?.length > 0 && (
              <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-slate-600 marker:text-slate-300">
                {p.beats.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function VersionHistory({ current }: { current: Outline }) {
  const { book } = useBookCtx();
  const { data, isLoading } = useOutlines(book.id);
  const [open, setOpen] = useState<string | null>(null);
  const older = (data || []).filter((o) => o.id !== current.id);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <History className="h-4 w-4 text-slate-400" /> Version history
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-16" />
        ) : !older.length ? (
          <p className="text-sm text-slate-500">This is the only version.</p>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100">
            {older.map((o) => (
              <li key={o.id}>
                <button
                  onClick={() => setOpen(open === o.id ? null : o.id)}
                  aria-expanded={open === o.id}
                  className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500"
                >
                  <span>
                    <span className="font-semibold">v{o.version}</span> <span className="text-slate-500">· {fmtDate(o.created_at)}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <Badge variant="secondary">{capitalize(humanize(o.status))}</Badge>
                    <ChevronDown className={cn("h-4 w-4 text-slate-400 transition-transform", open === o.id && "rotate-180")} />
                  </span>
                </button>
                {open === o.id && (
                  <div className="space-y-3 border-t border-slate-100 bg-slate-50/50 p-3">
                    {o.feedback && (
                      <p className="text-sm text-slate-600">
                        <span className="font-semibold">Feedback:</span> {o.feedback}
                      </p>
                    )}
                    <p className="text-sm text-slate-700">{o.synopsis}</p>
                    <PartList parts={o.chapters} showStatus={false} />
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function OutlineTab() {
  const { book, partLabel, refresh } = useBookCtx();
  const { run, pending } = useAction();
  const [editing, setEditing] = useState(false);
  const [reviseOpen, setReviseOpen] = useState(false);
  const [feedback, setFeedback] = useState("");
  const outline = book.outline;
  const planningJobs = activeJobs(book, ["plan_book", "revise_outline"]);
  const busyJob = book.jobs.length > 0;

  if (!outline) {
    return (
      <EmptyState title="No outline yet">
        {planningJobs.length ? "The outline is being planned. It will appear here when ready." : "Planning hasn't produced an outline. Use Re-plan on the Overview tab."}
      </EmptyState>
    );
  }
  if (editing) return <OutlineEditor outline={outline} onDone={() => setEditing(false)} />;

  const approved = outline.status === "approved";
  const hasChapters = book.chapters.length > 0;
  const total = outline.chapters.reduce((s, c) => s + (c.target_words || 0), 0);

  return (
    <div className="space-y-6">
      <Card className="p-4 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold">Outline v{outline.version}</h2>
              <Badge variant={approved ? "success" : outline.status === "changes_requested" ? "info" : "warning"}>
                {approved ? "Approved" : outline.status === "changes_requested" ? "Changes requested" : "Awaiting review"}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              {outline.chapters.length} {plural(partLabel, outline.chapters.length).toLowerCase()} · ~{fmtNumber(total)} words · created {fmtDate(outline.created_at)}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setEditing(true)} disabled={planningJobs.length > 0}>
              <Pencil className="h-4 w-4" /> Edit
            </Button>
            {!approved && (
              <>
                {!hasChapters && (
                  <Button variant="outline" onClick={() => setReviseOpen(true)} disabled={planningJobs.length > 0}>
                    <MessageSquare className="h-4 w-4" /> Request changes
                  </Button>
                )}
                <Button
                  loading={pending === "approve"}
                  disabled={busyJob}
                  title={busyJob ? "Wait for the running job to finish" : undefined}
                  onClick={() =>
                    run(
                      "approve",
                      () => api.approveOutline(book.id),
                      book.review_mode === "autopilot" ? "Outline approved. Autopilot writing started." : `Outline approved. Writing ${partLabel.toLowerCase()} 1.`,
                    ).then(refresh)
                  }
                >
                  {pending !== "approve" && <Check className="h-4 w-4" />} Approve outline
                </Button>
              </>
            )}
          </div>
        </div>
        {outline.feedback && (
          <p className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
            <span className="font-semibold">Your last feedback:</span> {outline.feedback}
          </p>
        )}
        {outline.synopsis && (
          <div className="mt-4">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Synopsis</p>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{outline.synopsis}</p>
          </div>
        )}
      </Card>

      <PartList parts={outline.chapters} />
      <VersionHistory current={outline} />

      <Dialog
        open={reviseOpen}
        onClose={() => setReviseOpen(false)}
        title="Request outline changes"
        description="The AI will produce a new outline version based on your notes."
        footer={
          <>
            <Button variant="outline" onClick={() => setReviseOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={pending === "revise"}
              disabled={feedback.trim().length < 3}
              onClick={async () => {
                const job = await run("revise", () => api.reviseOutline(book.id, feedback.trim()), "Revision queued");
                if (job) {
                  setReviseOpen(false);
                  setFeedback("");
                  refresh();
                }
              }}
            >
              Send feedback
            </Button>
          </>
        }
      >
        <Label htmlFor="outline-feedback">What should change?</Label>
        <Textarea
          id="outline-feedback"
          className="mt-2"
          rows={6}
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder={`e.g. Merge ${partLabel.toLowerCase()}s 3 and 4, give the antagonist a clearer motive, end on a twist.`}
        />
      </Dialog>
    </div>
  );
}
