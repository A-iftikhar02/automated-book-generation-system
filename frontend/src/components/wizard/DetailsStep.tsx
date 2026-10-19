"use client";

import type { Catalog, Category } from "@/lib/api";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { SetField, WizardState } from "./types";

function RadioCards({
  name,
  options,
  value,
  onChange,
}: {
  name: string;
  options: [string, string][];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div role="radiogroup" aria-label={name} className="grid gap-2 sm:grid-cols-2">
      {options.map(([k, label]) => {
        const [title, ...rest] = label.split(": ");
        return (
          <button
            key={k}
            type="button"
            role="radio"
            aria-checked={value === k}
            onClick={() => onChange(k)}
            className={cn(
              "rounded-lg border bg-white px-3 py-2 text-left text-sm transition-colors hover:border-blue-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
              value === k ? "border-blue-500 bg-blue-50/50 ring-1 ring-blue-500" : "border-slate-200",
            )}
          >
            <span className="font-medium text-slate-900">{title}</span>
            {rest.length > 0 && <span className="mt-0.5 block text-xs text-slate-500">{rest.join(": ")}</span>}
          </button>
        );
      })}
    </div>
  );
}

export function DetailsStep({
  catalog,
  category,
  state,
  set,
}: {
  catalog: Catalog;
  category: Category;
  state: WizardState;
  set: SetField;
}) {
  const genres = Object.entries(category.fiction ? catalog.fiction_genres : catalog.nonfiction_genres);
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="genre">Genre</Label>
        <Select id="genre" value={state.genre} onChange={(e) => set("genre", e.target.value)} required>
          <option value="" disabled>
            Choose a {category.fiction ? "fiction" : "non-fiction"} genre…
          </option>
          {genres.map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="audience">Audience</Label>
        <Select id="audience" value={state.audience} onChange={(e) => set("audience", e.target.value)}>
          {category.allowed_audiences.map((a) => (
            <option key={a} value={a}>
              {catalog.audiences[a]?.label || a}
            </option>
          ))}
        </Select>
        <p className="text-xs text-slate-500">Sets the target reading level checked during QA.</p>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium text-slate-700">Content rating</p>
        <RadioCards name="Content rating" options={Object.entries(catalog.content_ratings)} value={state.content_rating} onChange={(v) => set("content_rating", v)} />
      </div>

      {category.fiction && (
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="pov">Point of view</Label>
            <Select id="pov" value={state.pov} onChange={(e) => set("pov", e.target.value)}>
              {Object.entries(catalog.povs).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="tense">Tense</Label>
            <Select id="tense" value={state.tense} onChange={(e) => set("tense", e.target.value)}>
              {Object.entries(catalog.tenses).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
          </div>
        </div>
      )}
    </div>
  );
}
