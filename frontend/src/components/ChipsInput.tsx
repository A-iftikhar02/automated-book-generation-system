"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/** Editable list of short strings ("chips") with per-item length and count limits. */
export function ChipsInput({
  id,
  value,
  onChange,
  max,
  maxLength,
  placeholder,
}: {
  id: string;
  value: string[];
  onChange: (v: string[]) => void;
  max: number;
  maxLength: number;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");
  const full = value.length >= max;
  const add = () => {
    const v = draft.trim();
    if (!v || full || v.length > maxLength || value.includes(v)) return;
    onChange([...value, v]);
    setDraft("");
  };
  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {value.map((chip, i) => (
            <li
              key={`${chip}-${i}`}
              className={cn(
                "flex max-w-full items-center gap-1.5 rounded-full border py-1 pl-3 pr-1 text-sm",
                chip.length > maxLength ? "border-red-300 bg-red-50 text-red-800" : "border-slate-200 bg-slate-50 text-slate-800",
              )}
            >
              <span className="truncate">{chip}</span>
              <span className="shrink-0 text-[10px] tabular-nums text-slate-400">
                {chip.length}/{maxLength}
              </span>
              <button
                type="button"
                onClick={() => onChange(value.filter((_, j) => j !== i))}
                className="rounded-full p-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                aria-label={`Remove ${chip}`}
              >
                <X className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex items-center gap-2">
        <Input
          id={id}
          value={draft}
          disabled={full}
          maxLength={maxLength}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              add();
            }
          }}
          onBlur={add}
          placeholder={full ? `Maximum of ${max} reached` : placeholder}
        />
        <span className="w-24 shrink-0 text-right text-xs tabular-nums text-slate-500">
          {value.length}/{max} · {draft.length}/{maxLength}
        </span>
      </div>
    </div>
  );
}
