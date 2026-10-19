"use client";

import { Check, RefreshCw, Sparkles } from "lucide-react";
import { useSWRConfig } from "swr";
import { api, paths } from "@/lib/api";
import { useState } from "react";
import { useAction, useQa, useReadiness, useSystemStatus } from "@/lib/hooks";
import { ModelPicker } from "@/components/ModelPicker";
import { Dialog } from "@/components/ui/dialog";
import { capitalize, fmtNumber, humanize, plural } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { activeJobs, useBookCtx, WRITE_JOBS } from "./context";
import { StoryBible } from "./StoryBible";

const STEPS = ["Planning", "Outline review", "Writing", "Editing & QA", "Ready to publish"];
const STATUS_INDEX: Record<string, number> = { planning: 0, outline_review: 1, writing: 2, editing: 3 };

function Stepper({ current }: { current: number }) {
  return (
    <ol className="grid grid-cols-5 gap-1 sm:gap-2" aria-label="Workflow">
      {STEPS.map((s, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={s} aria-current={active ? "step" : undefined} className="flex min-w-0 flex-col items-center gap-1.5 text-center">
            <div className="flex w-full items-center">
              <div className={cn("h-0.5 flex-1", i === 0 ? "invisible" : done || active ? "bg-blue-500" : "bg-slate-200")} />
              <span
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold",
                  done ? "border-blue-600 bg-blue-600 text-white" : active ? "border-blue-600 bg-white text-blue-700" : "border-slate-200 bg-white text-slate-400",
                )}
              >
                {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </span>
              <div className={cn("h-0.5 flex-1", i === STEPS.length - 1 ? "invisible" : done ? "bg-blue-500" : "bg-slate-200")} />
            </div>
            <span className={cn("text-[11px] font-semibold leading-tight sm:text-xs", active ? "text-blue-700" : done ? "text-slate-700" : "text-slate-400")}>{s}</span>
          </li>
        );
      })}
    </ol>
  );
}

function NextStep({ ready }: { ready: boolean }) {
  const { book, partLabel, goTo, refresh } = useBookCtx();
  const { run, pending } = useAction();
  const { data: qa } = useQa(book.id);
  const writing = activeJobs(book, WRITE_JOBS);
  const planning = activeJobs(book, ["plan_book", "revise_outline"]);
  const label = partLabel.toLowerCase();
  const pendingPart = book.chapters.find((c) => c.status === "pending_review");

  let title: string;
  let body: string;
  let action: React.ReactNode = null;

  if (book.status === "planning") {
    if (planning.length) {
      title = "Planning in progress";
      body = "The AI is building the story bible and outline. This page updates automatically.";
    } else {
      title = "Planning has not finished";
      body = "Planning failed or was cancelled. Re-run it to create the story bible and outline.";
      action =
        book.chapters.length === 0 ? (
          <Button loading={pending === "replan"} onClick={() => run("replan", () => api.replan(book.id), "Planning queued").then(refresh)}>
            <RefreshCw className="h-4 w-4" /> Re-plan book
          </Button>
        ) : null;
    }
  } else if (book.status === "outline_review") {
    if (planning.length) {
      title = "Outline is being revised";
      body = "Your feedback is being applied. Review the new version when it is ready.";
    } else {
      title = "Review the outline";
      body = "Read the plan, edit parts directly or request changes, then approve it to start writing.";
      action = <Button onClick={() => goTo("outline")}>Open outline</Button>;
    }
  } else if (book.status === "writing") {
    if (pendingPart && !writing.length) {
      title = `Review ${label} ${pendingPart.number}`;
      body = `“${pendingPart.title}” is waiting for your approval or revision notes.`;
      action = <Button onClick={() => goTo("manuscript", pendingPart.number)}>Review {label} {pendingPart.number}</Button>;
    } else if (writing.length) {
      title = "Writing in progress";
      body = "You can read finished parts while the next one is written.";
      action = (
        <Button variant="outline" onClick={() => goTo("manuscript")}>
          Open manuscript
        </Button>
      );
    } else if (book.next_part) {
      title = `Write ${label} ${book.next_part}`;
      body = "The previous parts are approved. Start the next one, or write everything that's left.";
      action = <Button onClick={() => goTo("manuscript", book.next_part!)}>Go to {label} {book.next_part}</Button>;
    } else {
      title = "Finish reviewing";
      body = `Approve every ${label} to move on to editing.`;
      action = <Button onClick={() => goTo("manuscript")}>Open manuscript</Button>;
    }
  } else if (!qa?.latest_run) {
    title = "Run a quality check";
    body = "Every part is approved. Check spelling, grammar, repetition, continuity and readability before publishing.";
    action = <Button onClick={() => goTo("quality")}>Go to quality</Button>;
  } else if (!ready) {
    title = "Get ready to publish";
    body = "Fix remaining issues, fill in the store listing and cover, then work through the readiness checklist.";
    action = (
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => goTo("quality")}>
          Quality issues
        </Button>
        <Button onClick={() => goTo("publish")}>Publishing checklist</Button>
      </div>
    );
  } else {
    title = "Ready to publish";
    body = "The checklist passes. Export store-ready files and upload them.";
    action = <Button onClick={() => goTo("export")}>Export files</Button>;
  }

  const busy = planning.length > 0 || writing.length > 0;
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-blue-50 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex gap-3">
        {busy ? <Spinner className="mt-0.5 h-5 w-5 text-indigo-600" /> : <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-indigo-600" aria-hidden />}
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-500">Next step</p>
          <p className="font-semibold text-slate-900">{title}</p>
          <p className="text-sm text-slate-600">{body}</p>
        </div>
      </div>
      {action}
    </div>
  );
}

/** Change the book's writer/editor model, e.g. when the pinned writer's provider is out of quota. */
function ModelsDialogButton() {
  const { book } = useBookCtx();
  const { data: status } = useSystemStatus();
  const { mutate } = useSWRConfig();
  const { run, pending } = useAction();
  const [open, setOpen] = useState(false);
  const [writer, setWriter] = useState(book.writer_model || "");
  const [editor, setEditor] = useState(book.editor_model || "");
  const written = book.parts_written > 0;
  const save = async () => {
    const b = await run(
      "models",
      () => api.updateBook(book.id, { writer_model: writer || null, editor_model: editor || null }),
      "Models updated",
    );
    if (b) {
      mutate(paths.book(book.id), b, { revalidate: false });
      setOpen(false);
    }
  };
  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => {
          setWriter(book.writer_model || "");
          setEditor(book.editor_model || "");
          setOpen(true);
        }}
      >
        Change models
      </Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="AI models for this book"
        className="max-w-2xl"
        description={
          written
            ? "This book's writer is pinned so every part keeps the same voice. Switch it only if its provider is unavailable; later parts may read slightly differently."
            : "The writer is pinned to whichever model writes the first part."
        }
        footer={
          <>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={save} disabled={pending === "models"}>
              Save
            </Button>
          </>
        }
      >
        <div className="space-y-6">
          <ModelPicker id="book-writer" label="Writer" value={writer} onChange={setWriter} defaultHint={status?.ai.writer_models.join(" → ")} />
          <ModelPicker id="book-editor" label="Editor (QA, summaries, listing)" value={editor} onChange={setEditor} defaultHint={status?.ai.editor_models.join(" → ")} />
        </div>
      </Dialog>
    </>
  );
}

function Details() {
  const { book, catalog, partLabel } = useBookCtx();
  const { mutate } = useSWRConfig();
  const { run, busy } = useAction();
  const fiction = !!catalog?.categories.find((c) => c.key === book.category)?.fiction;
  const rows: [string, React.ReactNode][] = [
    ["Audience", catalog?.audiences[book.audience]?.label || book.audience],
    ["Content rating", (catalog?.content_ratings[book.content_rating] || book.content_rating).split(":")[0]],
    ...(fiction
      ? ([
          ["Point of view", catalog?.povs[book.pov] || book.pov],
          ["Tense", catalog?.tenses[book.tense] || book.tense],
        ] as [string, React.ReactNode][])
      : []),
    ["Tone", book.tone || "–"],
    ["Target", `${fmtNumber(book.target_word_count)} words in ${book.target_chapter_count} ${plural(partLabel, book.target_chapter_count).toLowerCase()}`],
    ["Writer model", book.writer_model || "server default (pinned when the first part is written)"],
    ["Editor model", book.editor_model || "server default"],
    ["Tokens", `${fmtNumber(book.prompt_tokens)} in / ${fmtNumber(book.completion_tokens)} out`],
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Brief</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Premise</p>
          <p className="whitespace-pre-wrap text-slate-800">{book.premise}</p>
        </div>
        {book.style_notes && (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Style notes</p>
            <p className="whitespace-pre-wrap text-slate-800">{book.style_notes}</p>
          </div>
        )}
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
          {rows.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-slate-500">{k}</dt>
              <dd className="min-w-0 break-words text-slate-800">{v}</dd>
            </div>
          ))}
        </dl>
        <ModelsDialogButton />
        <div className="space-y-1.5 border-t border-slate-100 pt-4">
          <label htmlFor="review-mode" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Review mode
          </label>
          <Select
            id="review-mode"
            value={book.review_mode}
            disabled={busy}
            onChange={(e) => {
              const review_mode = e.target.value as "manual" | "autopilot";
              run("mode", () => api.updateBook(book.id, { review_mode }), `Review mode: ${capitalize(humanize(review_mode))}`).then(
                (b) => b && mutate(paths.book(book.id), b, { revalidate: false }),
              );
            }}
          >
            <option value="manual">Manual: approve each part</option>
            <option value="autopilot">Autopilot: write unattended</option>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}

export function OverviewTab() {
  const { book } = useBookCtx();
  const { data: readiness } = useReadiness(book.id);
  const ready = book.status === "editing" && !!readiness?.ready;
  const current = ready ? 4 : (STATUS_INDEX[book.status] ?? 0);
  return (
    <div className="space-y-6">
      <Card className="p-4 sm:p-6">
        <Stepper current={current} />
        <div className="mt-6">
          <NextStep ready={ready} />
        </div>
      </Card>
      <div className="grid items-start gap-6 lg:grid-cols-[1fr_1.4fr]">
        <Details />
        <StoryBible />
      </div>
    </div>
  );
}
