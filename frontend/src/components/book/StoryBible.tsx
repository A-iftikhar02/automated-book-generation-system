"use client";

import { useState } from "react";
import { Braces, Save } from "lucide-react";
import { useSWRConfig } from "swr";
import { api, paths, type StoryBible as Bible } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { capitalize, humanize } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty";
import { Textarea } from "@/components/ui/textarea";
import { useBookCtx } from "./context";

const PRIMARY_KEYS = ["name", "term", "fact", "title"];
const ORDER = ["logline", "synopsis", "characters", "settings", "glossary", "continuity_facts"];

function Value({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "") return <span className="text-slate-400">–</span>;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return <span className="whitespace-pre-wrap">{String(value)}</span>;
  }
  if (Array.isArray(value)) {
    if (value.every((v) => typeof v !== "object" || v === null)) {
      return <span>{value.map(String).join(", ")}</span>;
    }
    return (
      <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100">
        {value.map((item, i) => (
          <li key={i} className="px-3 py-2">
            <Entry item={item} />
          </li>
        ))}
      </ul>
    );
  }
  return <Entry item={value} />;
}

function Entry({ item }: { item: unknown }) {
  if (typeof item !== "object" || item === null) return <span>{String(item)}</span>;
  const obj = item as Record<string, unknown>;
  const pk = PRIMARY_KEYS.find((k) => typeof obj[k] === "string");
  const rest = Object.entries(obj).filter(([k]) => k !== pk);
  return (
    <div className="text-sm">
      {pk && <span className="font-semibold text-slate-900">{String(obj[pk])}</span>}
      {rest.length > 0 && (
        <dl className="mt-0.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-600">
          {rest.map(([k, v]) => (
            <div key={k} className="min-w-0">
              <dt className="inline font-medium text-slate-500">{humanize(k)}: </dt>
              <dd className="inline break-words">{typeof v === "object" && v !== null ? JSON.stringify(v) : String(v)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

export function StoryBible() {
  const { book } = useBookCtx();
  const { mutate } = useSWRConfig();
  const { run, busy } = useAction();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const bible = book.story_bible || {};
  const keys = [...ORDER.filter((k) => k in bible), ...Object.keys(bible).filter((k) => !ORDER.includes(k))];

  const startEdit = () => {
    setDraft(JSON.stringify(bible, null, 2));
    setParseError(null);
    setEditing(true);
  };
  const save = async () => {
    let parsed: Bible;
    try {
      parsed = JSON.parse(draft);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) throw new Error("The story bible must be a JSON object.");
    } catch (e) {
      setParseError(e instanceof Error ? e.message : "Invalid JSON");
      return;
    }
    const updated = await run("bible", () => api.saveStoryBible(book.id, parsed), "Story bible saved");
    if (updated) {
      mutate(paths.book(book.id), updated, { revalidate: false });
      setEditing(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
        <div>
          <CardTitle className="text-base">Story bible</CardTitle>
          <p className="mt-1 text-xs text-slate-500">The writer consults this for continuity in every part.</p>
        </div>
        {!editing ? (
          <Button size="sm" variant="outline" onClick={startEdit}>
            <Braces className="h-3.5 w-3.5" /> Edit as JSON
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={busy}>
              Cancel
            </Button>
            <Button size="sm" onClick={save} loading={busy}>
              {!busy && <Save className="h-3.5 w-3.5" />} Save
            </Button>
          </div>
        )}
      </CardHeader>
      <CardContent>
        {editing ? (
          <div className="space-y-2">
            <Textarea
              value={draft}
              onChange={(e) => {
                setDraft(e.target.value);
                setParseError(null);
              }}
              rows={22}
              spellCheck={false}
              className="font-mono text-xs"
              aria-label="Story bible JSON"
              aria-invalid={!!parseError}
            />
            {parseError && <p className="text-xs text-red-600">{parseError}</p>}
          </div>
        ) : keys.length === 0 ? (
          <EmptyState title="No story bible yet" className="py-8">
            It is created during planning. You can also write one yourself with “Edit as JSON”.
          </EmptyState>
        ) : (
          <dl className="space-y-4">
            {keys.map((k) => (
              <div key={k}>
                <dt className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{capitalize(humanize(k))}</dt>
                <dd className="text-sm text-slate-800">
                  <Value value={bible[k]} />
                </dd>
              </div>
            ))}
          </dl>
        )}
      </CardContent>
    </Card>
  );
}
