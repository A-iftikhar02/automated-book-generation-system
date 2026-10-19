"use client";

import { useRef, useState } from "react";
import { ImageIcon, Sparkles, Trash2, Type, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { BookCover } from "@/components/BookCover";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { activeJobs, useBookCtx } from "./context";

export function CoverSection() {
  const { book, refresh, coverVersion } = useBookCtx();
  const { run, pending } = useAction();
  const [prompt, setPrompt] = useState("");
  const [aiOpen, setAiOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [finished, setFinished] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);
  const job = activeJobs(book, ["cover"])[0];
  const busy = !!job || pending !== null;

  const upload = async () => {
    if (!file) return;
    const ok = await run("upload", () => api.uploadCover(book.id, file, finished), (r) =>
      r.warnings?.length ? `Cover uploaded. ${r.warnings.join(" ")}` : "Cover uploaded",
    );
    if (ok) {
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      refresh();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Cover</CardTitle>
        <p className="text-xs text-slate-500">KDP and Apple Books want at least 1600 × 2560 px (1:1.6). The paperback wrap PDF is built from this front cover.</p>
      </CardHeader>
      <CardContent className="flex flex-col gap-5 sm:flex-row">
        <div className="relative mx-auto w-40 shrink-0 sm:mx-0">
          <BookCover bookId={book.id} hasCover={book.has_cover} version={coverVersion} title={book.title} className="w-40" />
          {job && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 rounded-md bg-white/80 text-center text-xs font-medium text-blue-700">
              <Spinner className="h-5 w-5" />
              {job.message || "Generating…"}
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="accent" disabled={busy} onClick={() => setAiOpen(true)}>
              <Sparkles className="h-3.5 w-3.5" /> Generate with AI
            </Button>
            <Button
              size="sm"
              variant="outline"
              loading={pending === "typo"}
              disabled={busy}
              onClick={() => run("typo", () => api.generateCover(book.id, false), "Building a typographic cover").then(refresh)}
            >
              {pending !== "typo" && <Type className="h-3.5 w-3.5" />} Typographic cover (no AI)
            </Button>
            {book.has_cover && (
              <Button size="sm" variant="ghost" className="text-red-600 hover:bg-red-50" disabled={busy} onClick={() => setConfirmDelete(true)}>
                <Trash2 className="h-3.5 w-3.5" /> Delete
              </Button>
            )}
          </div>

          <fieldset className="space-y-3 rounded-lg border border-slate-200 p-3">
            <legend className="px-1 text-sm font-medium text-slate-700">Upload your own</legend>
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              aria-label="Cover image file"
              className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-800 hover:file:bg-slate-200"
            />
            <div role="radiogroup" aria-label="What is this image?" className="grid gap-2 sm:grid-cols-2">
              {(
                [
                  [true, "Finished design", "Already has the title and author on it."],
                  [false, "Artwork only", "BookPilot adds the title and author text."],
                ] as const
              ).map(([v, title, body]) => (
                <label
                  key={title}
                  className={cn(
                    "cursor-pointer rounded-md border p-2 text-xs has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-blue-500",
                    finished === v ? "border-blue-500 bg-blue-50/50" : "border-slate-200",
                  )}
                >
                  <input type="radio" name="finished-design" className="sr-only" checked={finished === v} onChange={() => setFinished(v)} />
                  <span className="block text-sm font-semibold text-slate-900">{title}</span>
                  {body}
                </label>
              ))}
            </div>
            <Button size="sm" onClick={upload} disabled={!file || busy} loading={pending === "upload"}>
              {pending !== "upload" && <Upload className="h-3.5 w-3.5" />} Upload cover
            </Button>
          </fieldset>
          {!book.has_cover && !job && (
            <p className="flex items-center gap-2 text-xs text-amber-700">
              <ImageIcon className="h-3.5 w-3.5" /> Stores require a cover before you can publish.
            </p>
          )}
        </div>
      </CardContent>

      <Dialog
        open={aiOpen}
        onClose={() => setAiOpen(false)}
        title="Generate a cover with AI"
        description="The image model paints artwork from your book's genre and story; BookPilot then sets the title and author."
        footer={
          <>
            <Button variant="outline" onClick={() => setAiOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={pending === "ai"}
              onClick={async () => {
                const j = await run("ai", () => api.generateCover(book.id, true, prompt.trim() || undefined), "Generating cover…");
                if (j) {
                  setAiOpen(false);
                  refresh();
                }
              }}
            >
              Generate
            </Button>
          </>
        }
      >
        <Label htmlFor="cover-prompt">Art direction (optional)</Label>
        <Textarea
          id="cover-prompt"
          className="mt-2"
          rows={4}
          maxLength={1500}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. A lone lighthouse in a storm, warm lantern glow, painterly, deep teal palette"
        />
        <p className="mt-1 text-right text-xs text-slate-500">{prompt.length}/1500</p>
      </Dialog>
      <ConfirmDialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Delete the cover?"
        description="The cover image files are removed. Existing exports keep their embedded cover."
        confirmLabel="Delete cover"
        destructive
        pending={pending === "delete"}
        onConfirm={() =>
          run("delete", () => api.deleteCover(book.id), "Cover deleted").then(() => refresh())
        }
      />
    </Card>
  );
}
