"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, Lock, Plus, Save, Trash2 } from "lucide-react";
import { useSWRConfig } from "swr";
import { api, paths, type Outline } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { fmtNumber, plural } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useBookCtx } from "./context";

interface DraftPart {
  key: number;
  title: string;
  synopsis: string;
  beats: string;
  target_words: number;
  locked: boolean;
}

/** Edit synopsis and parts. Parts that are already written are locked (the API rejects changing them). */
export function OutlineEditor({ outline, onDone }: { outline: Outline; onDone: () => void }) {
  const { book, partLabel, refresh } = useBookCtx();
  const { mutate } = useSWRConfig();
  const { run, busy } = useAction();
  const written = new Set(book.chapters.map((c) => c.number));
  const [synopsis, setSynopsis] = useState(outline.synopsis);
  const [nextKey, setNextKey] = useState(outline.chapters.length + 1);
  const [parts, setParts] = useState<DraftPart[]>(() =>
    outline.chapters.map((c, i) => ({
      key: i + 1,
      title: c.title,
      synopsis: c.synopsis || "",
      beats: (c.beats || []).join("\n"),
      target_words: c.target_words || 1000,
      locked: written.has(c.number),
    })),
  );
  const firstEditable = parts.findIndex((p) => !p.locked);
  const total = parts.reduce((s, p) => s + (p.target_words || 0), 0);

  const update = (key: number, patch: Partial<DraftPart>) => setParts((ps) => ps.map((p) => (p.key === key ? { ...p, ...patch } : p)));
  const move = (i: number, dir: -1 | 1) =>
    setParts((ps) => {
      const j = i + dir;
      if (j < 0 || j >= ps.length || ps[i].locked || ps[j].locked) return ps;
      const copy = [...ps];
      [copy[i], copy[j]] = [copy[j], copy[i]];
      return copy;
    });
  const add = () => {
    const avg = parts.length ? Math.round(total / parts.length) : 1000;
    setParts((ps) => [...ps, { key: nextKey, title: "", synopsis: "", beats: "", target_words: avg, locked: false }]);
    setNextKey((k) => k + 1);
  };

  const save = async () => {
    const result = await run(
      "save",
      () =>
        api.saveOutline(book.id, {
          synopsis,
          chapters: parts.map((p) => ({
            title: p.title.trim(),
            synopsis: p.synopsis.trim(),
            beats: p.beats.split("\n").map((b) => b.trim()).filter(Boolean),
            target_words: p.target_words,
          })),
        }),
      "Outline saved",
    );
    if (result) {
      await Promise.all([mutate(paths.outlines(book.id)), refresh()]);
      onDone();
    }
  };

  const missingTitle = parts.some((p) => !p.title.trim());

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="outline-synopsis">Synopsis</Label>
        <Textarea id="outline-synopsis" rows={5} value={synopsis} onChange={(e) => setSynopsis(e.target.value)} />
      </div>
      <ol className="space-y-3">
        {parts.map((p, i) => (
          <li key={p.key}>
            <Card className={p.locked ? "bg-slate-50 p-4" : "p-4"}>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-semibold text-slate-700">
                  {partLabel} {i + 1}
                  {p.locked && (
                    <span className="ml-2 inline-flex items-center gap-1 text-xs font-normal text-slate-500">
                      <Lock className="h-3 w-3" /> written, read-only
                    </span>
                  )}
                </span>
                {!p.locked && (
                  <div className="flex gap-1">
                    <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => move(i, -1)} disabled={i <= firstEditable} aria-label={`Move ${partLabel} ${i + 1} up`}>
                      <ArrowUp className="h-4 w-4" />
                    </Button>
                    <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => move(i, 1)} disabled={i === parts.length - 1} aria-label={`Move ${partLabel} ${i + 1} down`}>
                      <ArrowDown className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 text-red-600 hover:bg-red-50"
                      onClick={() => setParts((ps) => ps.filter((x) => x.key !== p.key))}
                      disabled={parts.length <= 1}
                      aria-label={`Remove ${partLabel} ${i + 1}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>
              <div className="grid gap-3 sm:grid-cols-[1fr_9rem]">
                <div className="space-y-1">
                  <Label htmlFor={`t-${p.key}`} className="text-xs">
                    Title
                  </Label>
                  <Input id={`t-${p.key}`} value={p.title} disabled={p.locked} onChange={(e) => update(p.key, { title: e.target.value })} aria-invalid={!p.title.trim()} />
                </div>
                <div className="space-y-1">
                  <Label htmlFor={`w-${p.key}`} className="text-xs">
                    Target words
                  </Label>
                  <Input
                    id={`w-${p.key}`}
                    type="number"
                    min={100}
                    step={100}
                    value={p.target_words}
                    disabled={p.locked}
                    onChange={(e) => update(p.key, { target_words: Number(e.target.value) })}
                  />
                </div>
                <div className="space-y-1 sm:col-span-2">
                  <Label htmlFor={`s-${p.key}`} className="text-xs">
                    Synopsis
                  </Label>
                  <Textarea id={`s-${p.key}`} rows={3} value={p.synopsis} disabled={p.locked} onChange={(e) => update(p.key, { synopsis: e.target.value })} />
                </div>
                <div className="space-y-1 sm:col-span-2">
                  <Label htmlFor={`b-${p.key}`} className="text-xs">
                    Beats (one per line)
                  </Label>
                  <Textarea id={`b-${p.key}`} rows={3} value={p.beats} disabled={p.locked} onChange={(e) => update(p.key, { beats: e.target.value })} />
                </div>
              </div>
            </Card>
          </li>
        ))}
      </ol>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Button variant="outline" onClick={add}>
          <Plus className="h-4 w-4" /> Add {partLabel.toLowerCase()}
        </Button>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-slate-500">
            {parts.length} {plural(partLabel, parts.length).toLowerCase()} · {fmtNumber(total)} words
          </span>
          <Button variant="ghost" onClick={onDone} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={save} loading={busy} disabled={missingTitle}>
            {!busy && <Save className="h-4 w-4" />} Save outline
          </Button>
        </div>
      </div>
      {missingTitle && <p className="text-right text-xs text-red-600">Every {partLabel.toLowerCase()} needs a title.</p>}
    </div>
  );
}
