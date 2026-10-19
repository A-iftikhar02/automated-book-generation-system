"use client";

import { useState } from "react";
import { ChevronDown, Lightbulb } from "lucide-react";
import type { Category, ReviewMode } from "@/lib/api";
import { fmtNumber, plural } from "@/lib/format";
import { useSystemStatus } from "@/lib/hooks";
import { ModelPicker } from "@/components/ModelPicker";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { SetField, WizardState } from "./types";

const MODES: { id: ReviewMode; title: string; body: string }[] = [
  {
    id: "manual",
    title: "Manual review",
    body: "You approve the outline and every part. Approving a part queues the next one, and you can ask for revisions at each step.",
  },
  {
    id: "autopilot",
    title: "Autopilot",
    body: "After you approve the outline, every part is written unattended (with a quick QA pass after each). Review and edit at the end.",
  },
];

export function StoryStep({ category, state, set }: { category: Category; state: WizardState; set: SetField }) {
  const [advanced, setAdvanced] = useState(false);
  const { data: status } = useSystemStatus();
  const label = category.part_label;
  const perPart = state.target_chapter_count ? Math.round(state.target_word_count / state.target_chapter_count) : 0;
  const premiseShort = state.premise.trim().length < 20;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor="title">Title</Label>
          <Input id="title" value={state.title} maxLength={200} onChange={(e) => set("title", e.target.value)} placeholder="Working title (you can change it later)" required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="subtitle">Subtitle (optional)</Label>
          <Input id="subtitle" value={state.subtitle} maxLength={200} onChange={(e) => set("subtitle", e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="author">Author / pen name</Label>
          <Input id="author" value={state.author_name} maxLength={200} onChange={(e) => set("author_name", e.target.value)} placeholder="Shown on the cover and title page" />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="premise">Premise</Label>
        <Textarea
          id="premise"
          rows={6}
          value={state.premise}
          onChange={(e) => set("premise", e.target.value)}
          aria-invalid={state.premise.length > 0 && premiseShort}
          aria-describedby="premise-help"
          placeholder={
            category.fiction
              ? "A disgraced lighthouse keeper discovers the lantern shows the drowned town's secrets..."
              : "A practical guide for freelance writers who want to protect four hours of focused work every day..."
          }
        />
        <div id="premise-help" className="flex flex-col gap-2 text-xs sm:flex-row sm:justify-between">
          <span className={cn(premiseShort && state.premise.length > 0 ? "text-red-600" : "text-slate-500")}>
            {state.premise.trim().length} characters{premiseShort ? " (minimum 20)" : ""}
          </span>
        </div>
        <div className="flex gap-2 rounded-lg border border-indigo-100 bg-indigo-50/60 p-3 text-xs text-indigo-900">
          <Lightbulb className="h-4 w-4 shrink-0 text-indigo-500" aria-hidden />
          <ul className="list-disc space-y-0.5 pl-4">
            {category.fiction ? (
              <>
                <li>Name the protagonist, what they want, and what stands in the way.</li>
                <li>Mention the setting and the stakes; hint at the ending if you have one in mind.</li>
              </>
            ) : (
              <>
                <li>Say who the reader is and the problem the book solves for them.</li>
                <li>List key topics, frameworks or chapters you want covered.</li>
              </>
            )}
            <li>Anything you want to avoid (tropes, topics, words) is worth stating too.</li>
          </ul>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="tone">Tone (optional)</Label>
          <Input id="tone" value={state.tone} maxLength={200} onChange={(e) => set("tone", e.target.value)} placeholder={category.fiction ? "e.g. atmospheric, wry, hopeful" : "e.g. warm, direct, practical"} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="style">Style notes (optional)</Label>
          <Input id="style" value={state.style_notes} onChange={(e) => set("style_notes", e.target.value)} placeholder="e.g. short chapters, British spelling" />
        </div>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <Label htmlFor="words">Target length</Label>
            <span className="text-sm font-semibold tabular-nums text-slate-900">{fmtNumber(state.target_word_count)} words</span>
          </div>
          <input
            id="words"
            type="range"
            min={category.min_words}
            max={category.max_words}
            step={category.max_words - category.min_words > 20_000 ? 1000 : 500}
            value={state.target_word_count}
            onChange={(e) => set("target_word_count", Number(e.target.value))}
            className="w-full accent-blue-600"
          />
          <div className="flex justify-between text-xs text-slate-500">
            <span>{fmtNumber(category.min_words)}</span>
            <span>{fmtNumber(category.max_words)}</span>
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="parts">Number of {plural(label).toLowerCase()}</Label>
          <Input
            id="parts"
            type="number"
            min={category.min_parts}
            max={category.max_parts}
            value={state.target_chapter_count || ""}
            onChange={(e) => set("target_chapter_count", Number(e.target.value))}
            onBlur={() =>
              set("target_chapter_count", Math.min(category.max_parts, Math.max(category.min_parts, state.target_chapter_count || category.default_parts)))
            }
          />
          <p className="text-xs text-slate-500">
            {category.min_parts}–{category.max_parts} allowed · about {fmtNumber(perPart)} words per {label.toLowerCase()}
          </p>
        </div>
      </div>

      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium text-slate-700">Review mode</legend>
        <div role="radiogroup" className="grid gap-3 sm:grid-cols-2">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              role="radio"
              aria-checked={state.review_mode === m.id}
              onClick={() => set("review_mode", m.id)}
              className={cn(
                "rounded-xl border bg-white p-4 text-left transition-colors hover:border-blue-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                state.review_mode === m.id ? "border-blue-500 ring-1 ring-blue-500" : "border-slate-200",
              )}
            >
              <span className="font-semibold text-slate-900">{m.title}</span>
              <span className="mt-1 block text-xs text-slate-500">{m.body}</span>
            </button>
          ))}
        </div>
      </fieldset>

      <div className="rounded-xl border border-slate-200 bg-white">
        <button
          type="button"
          onClick={() => setAdvanced((v) => !v)}
          aria-expanded={advanced}
          aria-controls="advanced-panel"
          className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          Advanced: AI models
          <ChevronDown className={cn("h-4 w-4 transition-transform", advanced && "rotate-180")} aria-hidden />
        </button>
        {advanced && (
          <div id="advanced-panel" className="grid gap-6 border-t border-slate-100 p-4 lg:grid-cols-2">
            <ModelPicker id="writer-model" label="Writer model" value={state.writer_model} onChange={(v) => set("writer_model", v)} defaultHint={status?.ai.writer_models.join(" → ")} />
            <ModelPicker id="editor-model" label="Editor model" value={state.editor_model} onChange={(v) => set("editor_model", v)} defaultHint={status?.ai.editor_models.join(" → ")} />
          </div>
        )}
      </div>
    </div>
  );
}
