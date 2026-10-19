"use client";

import { useState } from "react";
import { ArrowLeft, RotateCcw } from "lucide-react";
import { useSWRConfig } from "swr";
import { api, paths, type RevisionDetail } from "@/lib/api";
import { useAction, useRevisions } from "@/lib/hooks";
import { capitalize, fmtDate, fmtNumber, humanize } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useBookCtx } from "./context";
import { Reader } from "./Reader";

const REASONS: Record<string, string> = {
  written: "First draft",
  rewritten: "AI rewrite",
  revised: "AI revision",
  manual_edit: "Manual edit",
  restored: "Restored",
  qa_fix: "QA fix",
  autofix: "Auto-fix",
  ai_fix: "AI fix",
};

export function RevisionHistory({
  open,
  onClose,
  number,
  currentRevision,
}: {
  open: boolean;
  onClose: () => void;
  number: number;
  currentRevision: number;
}) {
  const { book, category, partLabel, refresh } = useBookCtx();
  const { mutate } = useSWRConfig();
  const { data, isLoading } = useRevisions(book.id, open ? number : null);
  const { run, busy, pending } = useAction();
  const [viewing, setViewing] = useState<(RevisionDetail & { id: string }) | null>(null);
  const [restoreId, setRestoreId] = useState<string | null>(null);

  const close = () => {
    setViewing(null);
    onClose();
  };

  const view = async (id: string) => {
    const rev = await run(`view-${id}`, () => api.getRevision(book.id, number, id));
    if (rev) setViewing({ ...rev, id });
  };

  return (
    <>
      <Dialog
        open={open}
        onClose={close}
        className="max-w-3xl"
        title={viewing ? `Revision ${viewing.revision}: ${viewing.title}` : `${partLabel} ${number} history`}
        description={viewing ? `${REASONS[viewing.reason] || capitalize(humanize(viewing.reason))} · ${fmtDate(viewing.created_at)}` : "Every saved version of this part. Restoring creates a new revision."}
        footer={
          viewing ? (
            <>
              <Button variant="outline" onClick={() => setViewing(null)}>
                <ArrowLeft className="h-4 w-4" /> All revisions
              </Button>
              {viewing.revision !== currentRevision && (
                <Button onClick={() => setRestoreId(viewing.id)}>
                  <RotateCcw className="h-4 w-4" /> Restore this version
                </Button>
              )}
            </>
          ) : undefined
        }
      >
        {viewing ? (
          <Reader content={viewing.content} verse={category?.structure === "poems"} className="text-base" />
        ) : isLoading || !data ? (
          <div className="space-y-2">
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
          </div>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100">
            {data.map((r) => (
              <li key={r.id} className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-semibold">Revision {r.revision}</span>
                    <Badge variant="secondary">{REASONS[r.reason] || capitalize(humanize(r.reason))}</Badge>
                    {r.revision === currentRevision && <Badge variant="success">Current</Badge>}
                  </p>
                  <p className="mt-0.5 truncate text-xs text-slate-500">
                    {r.title} · {fmtNumber(r.word_count)} words · {fmtDate(r.created_at)}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" loading={pending === `view-${r.id}`} onClick={() => view(r.id)}>
                    View
                  </Button>
                  {r.revision !== currentRevision && (
                    <Button size="sm" variant="ghost" onClick={() => setRestoreId(r.id)}>
                      <RotateCcw className="h-3.5 w-3.5" /> Restore
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Dialog>
      <ConfirmDialog
        open={!!restoreId}
        onClose={() => setRestoreId(null)}
        title="Restore this revision?"
        description="The current text is kept in history; the restored text becomes a new revision. Open QA issues for this part may no longer line up, so re-run QA afterwards."
        confirmLabel="Restore"
        pending={busy}
        onConfirm={async () => {
          if (!restoreId) return;
          const ch = await run("restore", () => api.restoreRevision(book.id, number, restoreId), "Revision restored");
          if (ch) {
            mutate(paths.chapter(book.id, number), ch, { revalidate: false });
            mutate(paths.revisions(book.id, number));
            refresh();
            close();
          }
        }}
      />
    </>
  );
}
