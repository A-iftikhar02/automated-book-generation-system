"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import type { ModelInfo } from "@/lib/api";
import { errorMessage } from "@/lib/api";
import { fmtPrice } from "@/lib/format";
import { useModels, useSystemStatus } from "@/lib/hooks";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export const PROVIDER_LABELS: Record<string, string> = {
  openrouter: "OpenRouter",
  gemini: "Gemini",
  groq: "Groq",
  cerebras: "Cerebras",
  mistral: "Mistral",
  ollama: "Ollama (local)",
};

export function filterModels(models: ModelInfo[], q: string): ModelInfo[] {
  const needle = q.trim().toLowerCase();
  if (!needle) return models;
  return models.filter((m) => m.id.toLowerCase().includes(needle) || m.name.toLowerCase().includes(needle));
}

export function ProviderBadge({ provider }: { provider: string }) {
  return (
    <Badge variant={provider === "openrouter" ? "secondary" : "info"} className="whitespace-nowrap">
      {PROVIDER_LABELS[provider] || provider}
    </Badge>
  );
}

export function ModelPrice({ m }: { m: ModelInfo }) {
  if (m.provider === "ollama") return <span className="whitespace-nowrap text-xs text-emerald-700">local · free · unlimited</span>;
  if (m.provider !== "openrouter") {
    return <span className="whitespace-nowrap text-xs text-emerald-700">free tier with your key</span>;
  }
  if (m.free) return <span className="whitespace-nowrap text-xs font-medium text-emerald-700">free (50/day)</span>;
  return (
    <span className="whitespace-nowrap text-xs text-slate-500">
      {fmtPrice(m.prompt_price_per_million)} in / {fmtPrice(m.completion_price_per_million)} out per M
    </span>
  );
}

/** Searchable model selector across every configured provider. Empty value = server default chain. */
export function ModelPicker({
  id,
  label,
  value,
  onChange,
  defaultHint,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  defaultHint?: string;
}) {
  const { data, error, isLoading } = useModels();
  const { data: status } = useSystemStatus();
  const [q, setQ] = useState("");
  const [provider, setProvider] = useState("all");
  const [freeOnly, setFreeOnly] = useState(false);
  const configured = useMemo(
    () => new Set((status?.ai.providers || []).filter((p) => p.configured).map((p) => p.name)),
    [status],
  );
  const textModels = useMemo(
    () =>
      (data?.models || []).filter(
        (m) => (m.output_modalities?.includes("text") ?? true) && (configured.size === 0 || configured.has(m.provider)),
      ),
    [data, configured],
  );
  const providers = useMemo(() => Array.from(new Set(textModels.map((m) => m.provider))), [textModels]);
  const list = useMemo(() => {
    let out = filterModels(textModels, q);
    if (provider !== "all") out = out.filter((m) => m.provider === provider);
    if (freeOnly) out = out.filter((m) => m.free);
    return out.slice(0, 80);
  }, [textModels, q, provider, freeOnly]);
  const selected = textModels.find((m) => m.id === value);

  return (
    <fieldset className="min-w-0 space-y-2">
      <legend className="text-sm font-medium text-slate-700">{label}</legend>
      <p className="text-xs text-slate-500">
        Selected: <span className="break-all font-mono text-slate-800">{value || `server default${defaultHint ? ` (${defaultHint})` : ""}`}</span>
        {selected && (
          <>
            {" "}
            · <ModelPrice m={selected} />
          </>
        )}
      </p>
      <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
          <Input
            id={id}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search models, e.g. llama, gemini, mistral"
            className="pl-9"
            aria-label={`Search ${label}`}
          />
        </div>
        <Select value={provider} onChange={(e) => setProvider(e.target.value)} aria-label={`${label} provider`} className="sm:w-40">
          <option value="all">All providers</option>
          {providers.map((p) => (
            <option key={p} value={p}>
              {PROVIDER_LABELS[p] || p}
            </option>
          ))}
        </Select>
      </div>
      <Checkbox id={`${id}-free`} label="Free only" checked={freeOnly} onChange={setFreeOnly} />
      {isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : error ? (
        <p className="text-xs text-red-600">{errorMessage(error)}</p>
      ) : (
        <ul role="listbox" aria-label={label} className="max-h-56 overflow-y-auto rounded-md border border-slate-200 bg-white text-sm">
          <li>
            <button
              type="button"
              role="option"
              aria-selected={!value}
              onClick={() => onChange("")}
              className={cn("w-full px-3 py-2 text-left hover:bg-slate-50 focus-visible:bg-blue-50 focus-visible:outline-none", !value && "bg-blue-50 font-semibold text-blue-700")}
            >
              Server default
            </button>
          </li>
          {list.map((m) => (
            <li key={m.id}>
              <button
                type="button"
                role="option"
                aria-selected={m.id === value}
                onClick={() => onChange(m.id)}
                className={cn(
                  "flex w-full flex-col gap-0.5 border-t border-slate-100 px-3 py-2 text-left hover:bg-slate-50 focus-visible:bg-blue-50 focus-visible:outline-none sm:flex-row sm:items-center sm:justify-between sm:gap-3",
                  m.id === value && "bg-blue-50",
                )}
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium text-slate-800">{m.name}</span>
                  <span className="block truncate font-mono text-xs text-slate-500">{m.id}</span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <ProviderBadge provider={m.provider} />
                  <ModelPrice m={m} />
                </span>
              </button>
            </li>
          ))}
          {!list.length && <li className="px-3 py-3 text-slate-500">No models match.</li>}
        </ul>
      )}
    </fieldset>
  );
}
