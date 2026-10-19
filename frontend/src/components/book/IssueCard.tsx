"use client";

import { memo } from "react";
import { Ban, Bot, Check, RotateCcw } from "lucide-react";
import type { Issue } from "@/lib/api";
import { capitalize, humanize } from "@/lib/format";
import { SeverityBadge } from "@/components/badges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

/** Locate the flagged text (`matched`) inside the excerpt shown to the user. */
export function highlightRange(issue: Issue): [number, number] | null {
  const { excerpt, matched } = issue;
  if (!excerpt || !matched) return null;
  const needle = matched.replace(/\n/g, " ");
  const idx = excerpt.indexOf(needle);
  return idx >= 0 && needle.length > 0 ? [idx, idx + needle.length] : null;
}

function Excerpt({ issue }: { issue: Issue }) {
  if (!issue.excerpt) return null;
  const range = highlightRange(issue);
  return (
    <blockquote className="mt-2 break-words rounded-md border-l-2 border-slate-300 bg-slate-50 px-3 py-2 font-serif text-sm text-slate-700">
      {range ? (
        <>
          {issue.excerpt.slice(0, range[0])}
          <mark className="rounded bg-amber-200 px-0.5 text-slate-900">{issue.excerpt.slice(range[0], range[1])}</mark>
          {issue.excerpt.slice(range[1])}
        </>
      ) : (
        issue.excerpt
      )}
    </blockquote>
  );
}

export const IssueCard = memo(function IssueCard({
  issue,
  busy,
  onApply,
  onStatus,
}: {
  issue: Issue;
  busy: boolean;
  onApply: (issue: Issue, replacement: string) => void;
  onStatus: (issue: Issue, status: "open" | "ignored") => void;
}) {
  const fixable = issue.status === "open" && issue.offset !== null && issue.replacements.length > 0;
  return (
    <li className="p-4">
      <div className="flex flex-wrap items-center gap-2">
        <SeverityBadge severity={issue.severity} />
        <span className="text-xs font-semibold text-slate-700">{capitalize(humanize(issue.category))}</span>
        <span className="text-xs text-slate-400">· {humanize(issue.check)}</span>
        {issue.source === "ai" && (
          <Badge variant="purple" className="ml-auto">
            <Bot className="h-3 w-3" /> AI
          </Badge>
        )}
        {issue.source === "languagetool" && (
          <Badge variant="outline" className="ml-auto">
            LanguageTool
          </Badge>
        )}
        {issue.status !== "open" && <Badge variant={issue.status === "fixed" ? "success" : "secondary"}>{capitalize(issue.status)}</Badge>}
      </div>
      <p className="mt-2 text-sm text-slate-900">{issue.message}</p>
      <Excerpt issue={issue} />
      {issue.suggestion && !fixable && <p className="mt-2 text-sm text-slate-600">
        <span className="font-medium text-slate-700">Suggestion:</span> {issue.suggestion}
      </p>}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {fixable &&
          issue.replacements.slice(0, 5).map((r) => (
            <Button key={r} size="sm" variant="secondary" disabled={busy} onClick={() => onApply(issue, r)} title={`Replace with “${r}”`}>
              <Check className="h-3.5 w-3.5 text-green-600" />
              {r === "" ? <em>(delete)</em> : <span className="max-w-[14rem] truncate">{r}</span>}
            </Button>
          ))}
        <span className="flex-1" />
        {issue.status === "open" ? (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus(issue, "ignored")}>
            <Ban className="h-3.5 w-3.5" /> Ignore
          </Button>
        ) : issue.status === "ignored" ? (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus(issue, "open")}>
            <RotateCcw className="h-3.5 w-3.5" /> Reopen
          </Button>
        ) : null}
      </div>
    </li>
  );
});
