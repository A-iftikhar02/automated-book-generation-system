"use client";

import { useCallback, useMemo, useState } from "react";
import { ChevronDown, ListChecks, WandSparkles } from "lucide-react";
import { useSWRConfig } from "swr";
import { api, paths, type Issue, type IssueFilters, type QAOverview } from "@/lib/api";
import { useAction, useIssues } from "@/lib/hooks";
import { capitalize, humanize } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { activeJobs, TEXT_JOBS, useBookCtx } from "./context";
import { IssueCard } from "./IssueCard";

const PAGE = 25;

interface Handlers {
  busy: boolean;
  onApply: (issue: Issue, replacement: string) => void;
  onStatus: (issue: Issue, status: "open" | "ignored") => void;
}

function Group({
  number,
  title,
  issues,
  defaultOpen,
  handlers,
}: {
  number: number | null;
  title: string;
  issues: Issue[];
  defaultOpen: boolean;
  handlers: Handlers;
}) {
  const { book, partLabel, refresh } = useBookCtx();
  const { run, pending } = useAction();
  const [open, setOpen] = useState(defaultOpen);
  const [shown, setShown] = useState(PAGE);
  const openCount = issues.filter((i) => i.status === "open").length;
  const locked = number !== null && activeJobs(book, TEXT_JOBS, number).length > 0;
  const counts = issues.reduce<Record<string, number>>((acc, i) => ({ ...acc, [i.severity]: (acc[i.severity] || 0) + 1 }), {});

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-2 border-b border-slate-100 bg-slate-50/60 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="flex min-w-0 items-center gap-2 rounded text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <ChevronDown className={cn("h-4 w-4 shrink-0 text-slate-400 transition-transform", !open && "-rotate-90")} aria-hidden />
          <span className="truncate font-semibold text-slate-900">{title}</span>
          <span className="shrink-0 text-xs text-slate-500">
            {issues.length} issue{issues.length === 1 ? "" : "s"}
            {Object.keys(counts).length > 0 && ` · ${["critical", "major", "minor", "info"].filter((s) => counts[s]).map((s) => `${counts[s]} ${s}`).join(", ")}`}
          </span>
        </button>
        {number !== null && openCount > 0 && (
          <Button
            size="sm"
            variant="outline"
            loading={pending === "aifix"}
            disabled={locked}
            onClick={() => run("aifix", () => api.aiFix(book.id, number), `AI is fixing ${partLabel.toLowerCase()} ${number}`).then(refresh)}
          >
            {pending !== "aifix" && <WandSparkles className="h-3.5 w-3.5" />} AI-fix this {partLabel.toLowerCase()}
          </Button>
        )}
      </div>
      {open && (
        <>
          <ul className="divide-y divide-slate-100">
            {issues.slice(0, shown).map((i) => (
              <IssueCard key={i.id} issue={i} busy={handlers.busy || locked} onApply={handlers.onApply} onStatus={handlers.onStatus} />
            ))}
          </ul>
          {issues.length > shown && (
            <div className="border-t border-slate-100 p-3 text-center">
              <Button size="sm" variant="ghost" onClick={() => setShown((s) => s + PAGE * 2)}>
                Show more ({issues.length - shown} remaining)
              </Button>
            </div>
          )}
        </>
      )}
    </Card>
  );
}

export function IssueList({ qa }: { qa: QAOverview | undefined }) {
  const { book, partLabel } = useBookCtx();
  const { mutate } = useSWRConfig();
  const { run, busy } = useAction();
  const [status, setStatus] = useState<IssueFilters["status"]>("open");
  const [severity, setSeverity] = useState("");
  const [category, setCategory] = useState("");
  const [source, setSource] = useState("");
  const [part, setPart] = useState("");

  const filters: IssueFilters = {
    status,
    severity: severity || undefined,
    category: category || undefined,
    source: source || undefined,
    ...(part === "book" ? { book_level: true } : part ? { chapter: Number(part) } : {}),
    limit: 1000,
  };
  const key = paths.issues(book.id, filters);
  const { data: issues, isLoading } = useIssues(book.id, filters);

  const groups = useMemo(() => {
    const map = new Map<number | null, Issue[]>();
    for (const i of issues || []) {
      const k = i.chapter_number;
      if (!map.has(k)) map.set(k, []);
      map.get(k)!.push(i);
    }
    return [...map.entries()].sort(([a], [b]) => (a ?? -1) - (b ?? -1));
  }, [issues]);

  const titles = new Map(book.chapters.map((c) => [c.number, c.title]));

  /** Update one issue in the cached list (drop it if it no longer matches the status filter). */
  const patchList = useCallback(
    (updated: Issue) =>
      mutate<Issue[]>(
        key,
        (list) =>
          (list || []).flatMap((i) => (i.id !== updated.id ? [i] : status === "all" || updated.status === status ? [updated] : [])),
        { revalidate: false },
      ),
    [key, mutate, status],
  );

  const onApply = useCallback(
    async (issue: Issue, replacement: string) => {
      const updated = await run("apply", () => api.applyIssue(issue.id, replacement), `Replaced with “${replacement}”`);
      if (updated) {
        await patchList(updated);
        // Other offsets in this part shifted, the text changed, and counts moved.
        mutate((k) => typeof k === "string" && k.startsWith(`/api/books/${book.id}/qa/issues`) && k !== key);
        mutate(key);
        mutate(paths.qa(book.id));
        if (issue.chapter_number) mutate(paths.chapter(book.id, issue.chapter_number));
      }
    },
    [run, patchList, mutate, key, book.id],
  );
  const onStatus = useCallback(
    async (issue: Issue, next: "open" | "ignored") => {
      const updated = await run("status", () => api.updateIssue(issue.id, next), next === "ignored" ? "Issue ignored" : "Issue reopened");
      if (updated) {
        await patchList(updated);
        mutate(paths.qa(book.id));
      }
    },
    [run, patchList, mutate, book.id],
  );
  const handlers: Handlers = useMemo(() => ({ busy, onApply, onStatus }), [busy, onApply, onStatus]);

  const categories = Object.keys(qa?.by_category || {});

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <ListChecks className="h-5 w-5 text-slate-400" /> Issues
          {issues && <span className="text-sm font-normal text-slate-500">({issues.length})</span>}
        </h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          <Select aria-label="Status" value={status} onChange={(e) => setStatus(e.target.value as IssueFilters["status"])}>
            <option value="open">Open</option>
            <option value="ignored">Ignored</option>
            <option value="fixed">Fixed</option>
            <option value="all">All statuses</option>
          </Select>
          <Select aria-label="Severity" value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="">All severities</option>
            {["critical", "major", "minor", "info"].map((s) => (
              <option key={s} value={s}>
                {capitalize(s)}
              </option>
            ))}
          </Select>
          <Select aria-label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {capitalize(humanize(c))}
              </option>
            ))}
          </Select>
          <Select aria-label={partLabel} value={part} onChange={(e) => setPart(e.target.value)}>
            <option value="">All {partLabel.toLowerCase()}s</option>
            <option value="book">Whole book</option>
            {book.chapters.map((c) => (
              <option key={c.number} value={c.number}>
                {partLabel} {c.number}
              </option>
            ))}
          </Select>
          <Select aria-label="Source" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">All sources</option>
            <option value="rule">Rules</option>
            <option value="languagetool">LanguageTool</option>
            <option value="ai">AI editor</option>
          </Select>
        </div>
      </div>

      {isLoading && !issues ? (
        <div className="space-y-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      ) : !groups.length ? (
        <EmptyState icon={ListChecks} title={status === "open" ? "No open issues" : "No issues match"}>
          {qa?.latest_run ? "Nothing matches these filters." : "Run a quality check to find issues."}
        </EmptyState>
      ) : (
        groups.map(([n, list], idx) => (
          <Group
            key={`${n}-${key}`}
            number={n}
            title={n === null ? "Whole book" : `${partLabel} ${n}${titles.get(n) ? `: ${titles.get(n)}` : ""}`}
            issues={list}
            defaultOpen={idx === 0 || groups.length <= 2 || (idx === 1 && groups[0][0] === null)}
            handlers={handlers}
          />
        ))
      )}
    </div>
  );
}
