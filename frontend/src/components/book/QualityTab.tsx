"use client";

import { useState } from "react";
import { Bot, Gauge, Play, TriangleAlert, Wrench } from "lucide-react";
import { api, type QAOverview } from "@/lib/api";
import { useAction, useQa } from "@/lib/hooks";
import { capitalize, fmtAgo, fmtNumber, humanize, scoreTone } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/ui/empty";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { activeJobs, TEXT_JOBS, useBookCtx } from "./context";
import { IssueList } from "./IssueList";

const TONE_COLORS = {
  success: "text-green-600",
  info: "text-blue-600",
  warning: "text-amber-500",
  destructive: "text-red-500",
  secondary: "text-slate-300",
};

function ScoreGauge({ score, grade }: { score: number | null; grade: string | null }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score ?? 0)) / 100;
  return (
    <div className="flex items-center gap-5">
      <div className="relative h-32 w-32 shrink-0">
        <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90" aria-hidden>
          <circle cx="60" cy="60" r={r} fill="none" strokeWidth="10" className="stroke-slate-100" />
          <circle
            cx="60"
            cy="60"
            r={r}
            fill="none"
            strokeWidth="10"
            strokeLinecap="round"
            stroke="currentColor"
            className={cn("transition-all duration-700", TONE_COLORS[scoreTone(score)])}
            strokeDasharray={`${c * pct} ${c}`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold tabular-nums text-slate-900">{score === null ? "–" : Math.round(score)}</span>
          <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">of 100</span>
        </div>
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Quality score</p>
        <p className="text-lg font-semibold text-slate-900">{grade || "Not checked yet"}</p>
        <p className="mt-1 text-xs text-slate-500">90+ publish-ready · 80+ good · 65+ needs editing</p>
      </div>
    </div>
  );
}

const SEV_STYLES: Record<string, string> = {
  critical: "bg-red-50 text-red-700 border-red-100",
  major: "bg-amber-50 text-amber-800 border-amber-100",
  minor: "bg-blue-50 text-blue-700 border-blue-100",
  info: "bg-slate-50 text-slate-600 border-slate-100",
};

function Summary({ qa }: { qa: QAOverview }) {
  const { book, partLabel } = useBookCtx();
  const run = qa.latest_run;
  const maxCat = Math.max(1, ...Object.values(qa.by_category));
  const numbers = Object.keys(qa.chapter_stats)
    .map(Number)
    .sort((a, b) => a - b);
  const titles = new Map(book.chapters.map((c) => [c.number, c.title]));
  const pct = (v?: number) => (v === undefined ? "–" : `${Math.round(v * 100)}%`);
  const num = (v?: number) => (v === undefined ? "–" : v.toFixed(1));

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[auto_1fr]">
        <Card className="p-5">
          <ScoreGauge score={qa.score} grade={qa.grade} />
          {run && (
            <p className="mt-4 text-xs text-slate-500">
              Last run {fmtAgo(run.completed_at || run.created_at)} · {run.chapter_numbers.length} {partLabel.toLowerCase()}(s) ·{" "}
              {run.include_ai ? "with AI editor" : "rules + grammar only"}
            </p>
          )}
        </Card>
        <Card className="p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Open issues ({fmtNumber(qa.open_issues)})</p>
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {(["critical", "major", "minor", "info"] as const).map((s) => (
              <div key={s} className={cn("rounded-lg border px-3 py-2", SEV_STYLES[s])}>
                <p className="text-xl font-bold tabular-nums">{qa.by_severity[s] ?? 0}</p>
                <p className="text-xs font-semibold capitalize">{s}</p>
              </div>
            ))}
          </div>
          {Object.keys(qa.by_category).length > 0 && (
            <ul className="mt-4 grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
              {Object.entries(qa.by_category).map(([cat, n]) => (
                <li key={cat} className="grid grid-cols-[7rem_1fr_2.5rem] items-center gap-2 text-xs">
                  <span className="truncate text-slate-600">{capitalize(humanize(cat))}</span>
                  <span className="h-1.5 rounded-full bg-slate-100">
                    <span className="block h-full rounded-full bg-indigo-400" style={{ width: `${(n / maxCat) * 100}%` }} />
                  </span>
                  <span className="text-right tabular-nums text-slate-700">{n}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {run && run.warnings.length > 0 && (
        <div role="status" className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <TriangleAlert className="h-5 w-5 shrink-0 text-amber-600" aria-hidden />
          <ul className="space-y-1">
            {run.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {qa.book_review && (qa.book_review.verdict || qa.book_review.summary) && (
        <Card className="border-indigo-100">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Bot className="h-4 w-4 text-indigo-500" /> AI editor&apos;s whole-book review
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {qa.book_review.verdict && <p className="font-semibold text-slate-900">{capitalize(humanize(qa.book_review.verdict))}</p>}
            {qa.book_review.summary && <p className="whitespace-pre-wrap text-slate-700">{qa.book_review.summary}</p>}
          </CardContent>
        </Card>
      )}

      {numbers.length > 0 && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[44rem] text-sm">
              <caption className="sr-only">Per-{partLabel.toLowerCase()} quality statistics</caption>
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th scope="col" className="px-4 py-2">{partLabel}</th>
                  <th scope="col" className="px-3 py-2 text-right">Score</th>
                  <th scope="col" className="px-3 py-2 text-right">Words</th>
                  <th scope="col" className="px-3 py-2 text-right" title="Flesch-Kincaid grade level">FK grade</th>
                  <th scope="col" className="px-3 py-2 text-right">Reading ease</th>
                  <th scope="col" className="px-3 py-2 text-right">Dialogue</th>
                  <th scope="col" className="px-3 py-2 text-right">Passive</th>
                  <th scope="col" className="px-3 py-2 text-right">Avg. sentence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {numbers.map((n) => {
                  const s = qa.chapter_stats[String(n)];
                  const score = qa.chapter_scores[String(n)] ?? s.score;
                  return (
                    <tr key={n}>
                      <th scope="row" className="max-w-[16rem] truncate px-4 py-2 text-left font-medium text-slate-800">
                        {n}. {titles.get(n) || ""}
                      </th>
                      <td className={cn("px-3 py-2 text-right font-semibold tabular-nums", TONE_COLORS[scoreTone(score)])}>{score === undefined ? "–" : Math.round(score)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{fmtNumber(s.words)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{num(s.fk_grade)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{num(s.reading_ease)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{pct(s.dialogue_ratio)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{pct(s.passive_ratio)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{num(s.avg_sentence_words)} w</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

function Controls({ qa }: { qa: QAOverview | undefined }) {
  const { book, partLabel, aiReady, refresh } = useBookCtx();
  const { run, pending } = useAction();
  const [scope, setScope] = useState("");
  const [includeAi, setIncludeAi] = useState(aiReady);
  const qaRunning = activeJobs(book, ["qa"]).length > 0;
  const textBusy = activeJobs(book, TEXT_JOBS).length > 0;
  const noText = book.chapters.length === 0;

  return (
    <Card className="p-4 sm:p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="qa-scope">Scope</Label>
            <Select id="qa-scope" value={scope} onChange={(e) => setScope(e.target.value)} className="sm:w-56">
              <option value="">Whole book</option>
              {book.chapters.map((c) => (
                <option key={c.number} value={c.number}>
                  {partLabel} {c.number}: {c.title}
                </option>
              ))}
            </Select>
          </div>
          <Checkbox
            id="qa-ai"
            checked={includeAi && aiReady}
            onChange={setIncludeAi}
            disabled={!aiReady}
            label="Include AI editor"
            description={aiReady ? "Plot, continuity and style review (costs tokens)" : "Unavailable: OpenRouter not configured"}
            className="pb-1"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            loading={pending === "autofix"}
            disabled={textBusy || !qa?.auto_fixable}
            title="Apply suggested replacements that are safe to apply automatically, plus typography clean-up"
            onClick={() => run("autofix", () => api.autofix(book.id, scope ? [Number(scope)] : null), "Auto-fix started").then(refresh)}
          >
            {pending !== "autofix" && <Wrench className="h-4 w-4" />} Auto-fix safe issues{qa?.auto_fixable ? ` (${qa.auto_fixable})` : ""}
          </Button>
          <Button
            loading={pending === "qa"}
            disabled={qaRunning || noText}
            onClick={() => run("qa", () => api.runQa(book.id, scope ? [Number(scope)] : null, includeAi && aiReady), "Quality check started").then(refresh)}
          >
            {pending !== "qa" && <Play className="h-4 w-4" />} {qaRunning ? "Checking…" : "Run QA"}
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function QualityTab() {
  const { book } = useBookCtx();
  const { data: qa, isLoading } = useQa(book.id);

  if (!book.chapters.length) {
    return (
      <EmptyState icon={Gauge} title="Nothing to check yet">
        Quality checks run on written parts. Write and approve some parts first.
      </EmptyState>
    );
  }

  return (
    <div className="space-y-6">
      <Controls qa={qa} />
      {isLoading ? (
        <Skeleton className="h-48" />
      ) : qa?.latest_run ? (
        <Summary qa={qa} />
      ) : (
        <EmptyState icon={Gauge} title="No quality check yet">
          Run QA to score the manuscript and list spelling, grammar, repetition, continuity and style issues.
        </EmptyState>
      )}
      <IssueList qa={qa} />
    </div>
  );
}
