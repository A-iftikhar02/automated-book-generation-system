"use client";

import { useState } from "react";
import { Eye, Save, Sparkles } from "lucide-react";
import { useSWRConfig } from "swr";
import { api, paths, type BookDetail, type BookUpdate } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { ChipsInput } from "@/components/ChipsInput";
import { SafeHtml } from "@/components/SafeHtml";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { activeJobs, useBookCtx } from "./context";

const TEXT_FIELDS = [
  "title",
  "subtitle",
  "author_name",
  "series_name",
  "edition",
  "publisher",
  "copyright_holder",
  "isbn_ebook",
  "isbn_print",
  "description",
  "back_cover_copy",
  "dedication",
  "acknowledgments",
  "author_bio",
] as const;
const NUMBER_FIELDS = ["series_number", "publication_year"] as const;

type TextField = (typeof TEXT_FIELDS)[number];
type NumberField = (typeof NUMBER_FIELDS)[number];
type Form = Record<TextField | NumberField, string> & { keywords: string[]; store_categories: string[] };

function fromBook(b: BookDetail): Form {
  const f = {} as Form;
  for (const k of TEXT_FIELDS) f[k] = (b[k] as string | null) ?? "";
  for (const k of NUMBER_FIELDS) f[k] = b[k] === null || b[k] === undefined ? "" : String(b[k]);
  f.keywords = [...(b.keywords || [])];
  f.store_categories = [...(b.store_categories || [])];
  return f;
}

/** Only the fields that differ from the saved book, converted to API types. */
function diff(form: Form, base: Form): BookUpdate {
  const out: Record<string, unknown> = {};
  for (const k of TEXT_FIELDS) {
    if (form[k] !== base[k]) out[k] = k === "title" ? form[k].trim() : form[k].trim() || null;
  }
  for (const k of NUMBER_FIELDS) if (form[k] !== base[k]) out[k] = form[k] === "" ? null : Number(form[k]);
  if (JSON.stringify(form.keywords) !== JSON.stringify(base.keywords)) out.keywords = form.keywords;
  if (JSON.stringify(form.store_categories) !== JSON.stringify(base.store_categories)) out.store_categories = form.store_categories;
  return out as BookUpdate;
}

function Field({
  id,
  label,
  hint,
  className,
  children,
}: {
  id: string;
  label: string;
  hint?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {children}
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export function MetadataForm() {
  const { book, refresh } = useBookCtx();
  const { mutate } = useSWRConfig();
  const { run, pending } = useAction();
  const [base, setBase] = useState(() => fromBook(book));
  const [form, setForm] = useState(base);
  const [syncedAt, setSyncedAt] = useState(book.updated_at);
  const [preview, setPreview] = useState(false);
  const [overwrite, setOverwrite] = useState(false);
  const changes = diff(form, base);
  const dirty = Object.keys(changes).length > 0;

  // Pull in server-side changes (e.g. AI listing finished) unless the user has unsaved edits.
  if (book.updated_at !== syncedAt) {
    setSyncedAt(book.updated_at);
    if (!dirty) {
      const fresh = fromBook(book);
      setBase(fresh);
      setForm(fresh);
    }
  }

  const set = <K extends keyof Form>(k: K, v: Form[K]) => setForm((f) => ({ ...f, [k]: v }));
  const text = (k: TextField) => ({
    id: `meta-${k}`,
    value: form[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => set(k, e.target.value),
  });
  const metaJob = activeJobs(book, ["metadata"]).length > 0;
  const descLen = form.description.length;

  const save = async () => {
    const updated = await run("save", () => api.updateBook(book.id, changes), "Listing saved");
    if (updated) {
      const fresh = fromBook(updated);
      setBase(fresh);
      setForm(fresh);
      setSyncedAt(updated.updated_at);
      mutate(paths.book(book.id), updated, { revalidate: false });
      mutate(paths.readiness(book.id));
      mutate(paths.books);
    }
  };

  return (
    <Card>
      <CardHeader className="flex-col gap-3 space-y-0 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle className="text-base">Store listing &amp; book details</CardTitle>
          <p className="mt-1 text-xs text-slate-500">Used on the title page, copyright page, EPUB metadata and your store listings.</p>
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <Button
            variant="accent"
            size="sm"
            loading={pending === "gen" || metaJob}
            onClick={() => run("gen", () => api.generateMetadata(book.id, overwrite), "Writing the listing…").then(refresh)}
          >
            {pending !== "gen" && !metaJob && <Sparkles className="h-3.5 w-3.5" />} Generate listing with AI
          </Button>
          <Checkbox id="meta-overwrite" checked={overwrite} onChange={setOverwrite} label="Overwrite filled-in fields" className="text-xs" />
        </div>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (dirty) save();
          }}
          className="space-y-8"
        >
          <section className="grid gap-4 sm:grid-cols-2" aria-label="Title and author">
            <Field id="meta-title" label="Title" className="sm:col-span-2">
              <Input {...text("title")} required maxLength={200} />
            </Field>
            <Field id="meta-subtitle" label="Subtitle">
              <Input {...text("subtitle")} maxLength={200} />
            </Field>
            <Field id="meta-author_name" label="Author / pen name">
              <Input {...text("author_name")} maxLength={200} />
            </Field>
            <Field id="meta-series_name" label="Series name">
              <Input {...text("series_name")} />
            </Field>
            <Field id="meta-series_number" label="Number in series">
              <Input id="meta-series_number" type="number" min={1} value={form.series_number} onChange={(e) => set("series_number", e.target.value)} />
            </Field>
          </section>

          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Publication details">
            <Field id="meta-edition" label="Edition">
              <Input {...text("edition")} placeholder="e.g. First edition" />
            </Field>
            <Field id="meta-publisher" label="Publisher / imprint">
              <Input {...text("publisher")} />
            </Field>
            <Field id="meta-copyright_holder" label="Copyright holder">
              <Input {...text("copyright_holder")} />
            </Field>
            <Field id="meta-publication_year" label="Publication year">
              <Input id="meta-publication_year" type="number" min={1900} max={2200} value={form.publication_year} onChange={(e) => set("publication_year", e.target.value)} />
            </Field>
            <Field id="meta-isbn_ebook" label="ISBN (ebook)" hint="Optional for KDP ebooks.">
              <Input {...text("isbn_ebook")} inputMode="numeric" placeholder="978-…" />
            </Field>
            <Field id="meta-isbn_print" label="ISBN (paperback)" hint="Leave empty to use a free KDP ISBN.">
              <Input {...text("isbn_print")} inputMode="numeric" placeholder="978-…" />
            </Field>
          </section>

          <section className="space-y-4" aria-label="Marketing copy">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <Label htmlFor="meta-description">Description</Label>
                <button
                  type="button"
                  onClick={() => setPreview((p) => !p)}
                  aria-pressed={preview}
                  className="inline-flex items-center gap-1 rounded text-xs font-medium text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  <Eye className="h-3.5 w-3.5" /> {preview ? "Hide preview" : "Preview"}
                </button>
              </div>
              <Textarea {...text("description")} rows={8} aria-describedby="desc-help" aria-invalid={descLen > 4000} />
              <p id="desc-help" className="flex justify-between gap-2 text-xs text-slate-500">
                <span>
                  Allowed HTML: &lt;p&gt; &lt;b&gt; &lt;i&gt; &lt;em&gt; &lt;strong&gt; &lt;br&gt; &lt;ul&gt; &lt;ol&gt; &lt;li&gt;
                </span>
                <span className={cn("tabular-nums", descLen > 4000 && "font-semibold text-red-600")}>{descLen}/4000</span>
              </p>
              {preview && (
                <SafeHtml
                  html={form.description || "<p><i>No description yet.</i></p>"}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-relaxed text-slate-800 [&_li]:ml-5 [&_ol]:list-decimal [&_p]:mb-2 [&_ul]:list-disc"
                />
              )}
            </div>
            <Field id="meta-back_cover_copy" label="Back cover copy" hint="Printed on the back of the paperback cover wrap. Plain text; blank lines separate paragraphs.">
              <Textarea {...text("back_cover_copy")} rows={4} />
            </Field>
            <Field id="meta-keywords" label="Keywords" hint="KDP allows 7 keyword phrases of up to 50 characters. Press Enter to add.">
              <ChipsInput id="meta-keywords" value={form.keywords} onChange={(v) => set("keywords", v)} max={7} maxLength={50} placeholder="e.g. cozy fantasy mystery" />
            </Field>
            <Field id="meta-store_categories" label="Store categories" hint="Up to 3 browse categories, e.g. “Fiction / Fantasy / Epic”.">
              <ChipsInput id="meta-store_categories" value={form.store_categories} onChange={(v) => set("store_categories", v)} max={3} maxLength={120} placeholder="Fiction / Mystery & Detective / Cozy" />
            </Field>
          </section>

          <section className="grid gap-4 lg:grid-cols-3" aria-label="Front and back matter">
            <Field id="meta-dedication" label="Dedication">
              <Textarea {...text("dedication")} rows={3} />
            </Field>
            <Field id="meta-acknowledgments" label="Acknowledgments">
              <Textarea {...text("acknowledgments")} rows={3} />
            </Field>
            <Field id="meta-author_bio" label="About the author">
              <Textarea {...text("author_bio")} rows={3} />
            </Field>
          </section>

          <div className="sticky bottom-0 -mx-6 -mb-6 flex flex-wrap items-center justify-end gap-3 rounded-b-xl border-t border-slate-100 bg-white/95 px-6 py-3 backdrop-blur">
            {dirty && <span className="mr-auto text-xs text-amber-700">Unsaved changes</span>}
            <Button type="button" variant="ghost" disabled={!dirty || pending === "save"} onClick={() => setForm(base)}>
              Discard
            </Button>
            <Button type="submit" loading={pending === "save"} disabled={!dirty || !form.title.trim() || descLen > 4000}>
              {pending !== "save" && <Save className="h-4 w-4" />} Save listing
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
