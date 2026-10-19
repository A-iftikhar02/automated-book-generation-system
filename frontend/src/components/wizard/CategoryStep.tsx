"use client";

import { CircleCheck } from "lucide-react";
import type { Category } from "@/lib/api";
import { fmtNumber, plural } from "@/lib/format";
import { cn } from "@/lib/utils";

export function CategoryStep({
  categories,
  value,
  onSelect,
}: {
  categories: Category[];
  value: string;
  onSelect: (c: Category) => void;
}) {
  const groups = [
    { title: "Fiction", items: categories.filter((c) => c.fiction) },
    { title: "Non-fiction", items: categories.filter((c) => !c.fiction) },
  ].filter((g) => g.items.length);

  return (
    <div className="space-y-6">
      {groups.map((g) => (
        <fieldset key={g.title}>
          <legend className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{g.title}</legend>
          <div role="radiogroup" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {g.items.map((c) => {
              const active = c.key === value;
              return (
                <button
                  key={c.key}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => onSelect(c)}
                  className={cn(
                    "relative flex h-full flex-col rounded-xl border bg-white p-4 text-left transition-all hover:border-blue-300 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                    active ? "border-blue-500 ring-1 ring-blue-500" : "border-slate-200",
                  )}
                >
                  {active && <CircleCheck className="absolute right-3 top-3 h-5 w-5 text-blue-600" aria-hidden />}
                  <span className="pr-6 font-semibold text-slate-900">{c.label}</span>
                  <span className="mt-1 text-sm text-slate-500">{c.description}</span>
                  <span className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs font-medium text-slate-600">
                    <span>
                      {fmtNumber(c.min_words)}–{fmtNumber(c.max_words)} words
                    </span>
                    <span>
                      {c.min_parts}–{c.max_parts} {plural(c.part_label).toLowerCase()}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
