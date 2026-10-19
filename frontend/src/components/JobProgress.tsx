"use client";

import { CircleX, RotateCcw } from "lucide-react";
import { api, type Job } from "@/lib/api";
import { fmtAgo, jobLabel } from "@/lib/format";
import { useAction } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";

/** One active job: label, status message, progress bar and a cancel button. */
export function JobProgress({
  job,
  partLabel,
  title,
  onChange,
}: {
  job: Job;
  partLabel?: string;
  title?: React.ReactNode;
  onChange?: () => void;
}) {
  const { run, busy } = useAction();
  const cancelling = job.message?.toLowerCase().startsWith("cancelling");
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm">
          <Spinner className="text-blue-600" />
          <span className="font-semibold text-slate-900">{jobLabel(job.type, job.payload, partLabel)}</span>
          {title && <span className="truncate text-slate-500">· {title}</span>}
          <span className="text-xs text-slate-400">
            {job.status === "queued" ? "queued" : `started ${fmtAgo(job.started_at)}`}
          </span>
        </div>
        <p className="mt-0.5 truncate text-xs text-slate-500">{job.message || "Working…"}</p>
        <Progress value={job.status === "queued" ? 0 : job.progress} className="mt-2 h-1.5" label={`${jobLabel(job.type)} progress`} />
      </div>
      <Button
        size="sm"
        variant="outline"
        loading={busy}
        disabled={cancelling}
        onClick={() => run("cancel", () => api.cancelJob(job.id), "Cancellation requested").then(() => onChange?.())}
      >
        {!busy && <CircleX className="h-3.5 w-3.5" />}
        {cancelling ? "Cancelling…" : "Cancel"}
      </Button>
    </div>
  );
}

/** Banner for the most recent failed/cancelled job with its error and a Retry button. */
export function FailedJob({
  job,
  partLabel,
  onRetry,
  onDismiss,
}: {
  job: Job;
  partLabel?: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}) {
  const { run, busy } = useAction();
  const failed = job.status === "failed";
  return (
    <div
      role="alert"
      className={
        failed
          ? "flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm sm:flex-row sm:items-start"
          : "flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm sm:flex-row sm:items-start"
      }
    >
      <CircleX className={failed ? "h-5 w-5 shrink-0 text-red-600" : "h-5 w-5 shrink-0 text-slate-500"} aria-hidden />
      <div className="min-w-0 flex-1">
        <p className={failed ? "font-semibold text-red-900" : "font-semibold text-slate-800"}>
          {jobLabel(job.type, job.payload, partLabel)} {failed ? "failed" : "was cancelled"}{" "}
          <span className="font-normal text-slate-500">{fmtAgo(job.finished_at || job.created_at)}</span>
        </p>
        {job.error && <p className="mt-1 whitespace-pre-wrap break-words text-red-800">{job.error}</p>}
      </div>
      <div className="flex gap-2">
        {onDismiss && (
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            Dismiss
          </Button>
        )}
        <Button
          size="sm"
          variant="outline"
          loading={busy}
          onClick={() => run("retry", () => api.retryJob(job.id), "Job queued again").then((r) => r && onRetry?.())}
        >
          {!busy && <RotateCcw className="h-3.5 w-3.5" />}
          Retry
        </Button>
      </div>
    </div>
  );
}
