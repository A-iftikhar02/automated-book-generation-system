"use client";

import { useState } from "react";
import { BookOpen, CircleCheck, Download, FileText, FileType, Package, Printer, Trash2, TriangleAlert } from "lucide-react";
import { useSWRConfig } from "swr";
import { api, apiUrl, paths, type ExportFormat, type ExportItem, type ExportValidation } from "@/lib/api";
import { useAction, useExports } from "@/lib/hooks";
import { EXPORT_LABELS, fmtBytes, fmtDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button, buttonClasses } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useBookCtx } from "./context";

const FORMATS: { id: ExportFormat; icon: React.ComponentType<{ className?: string }>; blurb: string }[] = [
  { id: "epub", icon: BookOpen, blurb: "Reflowable ebook for Kindle, Apple Books, Kobo and Google Play." },
  { id: "print_pdf", icon: Printer, blurb: "Typeset paperback interior with KDP margins and embedded fonts." },
  { id: "cover_wrap_pdf", icon: Package, blurb: "Back + spine + front cover sized from the page count, with bleed." },
  { id: "docx", icon: FileType, blurb: "Word manuscript for editors, beta readers or Draft2Digital." },
  { id: "txt", icon: FileText, blurb: "Plain text of the whole book." },
];

function FormatCard({ id, icon: Icon, blurb }: (typeof FORMATS)[number]) {
  const { book, catalog, refresh } = useBookCtx();
  const { run, busy } = useAction();
  const [trim, setTrim] = useState("6x9");
  const [paper, setPaper] = useState<"white" | "cream">("cream");
  const [largePrint, setLargePrint] = useState(false);
  const running = book.jobs.some((j) => j.type === "export" && j.payload?.format === id);
  const print = id === "print_pdf" || id === "cover_wrap_pdf";

  return (
    <Card className="flex flex-col p-4">
      <div className="flex items-start gap-3">
        <span className="rounded-lg bg-blue-50 p-2 text-blue-600">
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-900">{EXPORT_LABELS[id]}</h3>
          <p className="text-xs text-slate-500">{blurb}</p>
        </div>
      </div>
      {print && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="space-y-1">
            <Label htmlFor={`trim-${id}`} className="text-xs">
              Trim size
            </Label>
            <Select id={`trim-${id}`} value={trim} onChange={(e) => setTrim(e.target.value)} className="h-9">
              {Object.entries(catalog?.trim_sizes || { "6x9": { width: 6, height: 9 } }).map(([k, v]) => (
                <option key={k} value={k}>
                  {v.width}&quot; × {v.height}&quot;
                </option>
              ))}
            </Select>
          </div>
          {id === "cover_wrap_pdf" && (
            <div className="space-y-1">
              <Label htmlFor={`paper-${id}`} className="text-xs">
                Paper
              </Label>
              <Select id={`paper-${id}`} value={paper} onChange={(e) => setPaper(e.target.value as "white" | "cream")} className="h-9">
                {(catalog?.paper_types || ["white", "cream"]).map((p) => (
                  <option key={p} value={p}>
                    {p[0].toUpperCase() + p.slice(1)}
                  </option>
                ))}
              </Select>
            </div>
          )}
          <Checkbox
            id={`lp-${id}`}
            checked={largePrint}
            onChange={setLargePrint}
            label="Large print"
            description={id === "cover_wrap_pdf" ? "Match the interior's setting (affects spine width)" : undefined}
            className="sm:col-span-2"
          />
        </div>
      )}
      <div className="mt-auto pt-4">
        <Button
          className="w-full"
          variant="outline"
          loading={busy || running}
          onClick={() =>
            run(
              "export",
              () => api.createExport(book.id, { format: id, ...(print ? { trim_size: trim, large_print: largePrint } : {}), ...(id === "cover_wrap_pdf" ? { paper } : {}) }),
              `Exporting ${EXPORT_LABELS[id]}…`,
            ).then(refresh)
          }
        >
          {running ? "Exporting…" : `Export ${EXPORT_LABELS[id]}`}
        </Button>
      </div>
    </Card>
  );
}

function Validation({ v, format }: { v: ExportValidation; format: ExportFormat }) {
  const warnings = Array.isArray(v.warnings) ? v.warnings : [];
  const facts: string[] = [];
  if (v.trim_size) facts.push(`Trim ${v.trim_size}`);
  if (v.paper) facts.push(`${v.paper} paper`);
  if (typeof v.spine_width_in === "number") facts.push(`spine ${v.spine_width_in.toFixed(3)}"`);
  if (typeof v.full_width_in === "number" && typeof v.full_height_in === "number") facts.push(`full wrap ${v.full_width_in}" × ${v.full_height_in}"`);
  if (typeof v.inside_margin_in === "number")
    facts.push(`inside margin ${v.inside_margin_in.toFixed(3)}"${typeof v.kdp_min_inside_margin_in === "number" ? ` (KDP min ${v.kdp_min_inside_margin_in}")` : ""}`);
  if (v.fonts_embedded) facts.push("fonts embedded");

  return (
    <div className="mt-2 space-y-1.5 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        {format === "epub" && v.tool === "epubcheck" ? (
          v.valid ? (
            <Badge variant="success">
              <CircleCheck className="h-3 w-3" /> epubcheck valid
            </Badge>
          ) : v.valid === false ? (
            <Badge variant="destructive">
              epubcheck: {v.errors ?? 0} error(s), {typeof v.warnings === "number" ? v.warnings : 0} warning(s)
            </Badge>
          ) : (
            <Badge variant="warning">epubcheck failed to run</Badge>
          )
        ) : v.valid === true ? (
          <Badge variant="success">
            <CircleCheck className="h-3 w-3" /> Valid
          </Badge>
        ) : v.valid === false ? (
          <Badge variant="warning">Needs attention</Badge>
        ) : (
          <Badge variant="secondary">Not validated</Badge>
        )}
        {facts.length > 0 && <span className="text-slate-500">{facts.join(" · ")}</span>}
      </div>
      {v.note && <p className="text-slate-500">{v.note}</p>}
      {v.error && <p className="text-red-600">{v.error}</p>}
      {warnings.map((w, i) => (
        <p key={i} className="flex gap-1.5 text-amber-800">
          <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" /> {w}
        </p>
      ))}
      {v.messages && v.messages.length > 0 && (
        <details className="rounded-md border border-slate-200 bg-slate-50 p-2">
          <summary className="cursor-pointer font-medium text-slate-700">{v.messages.length} epubcheck message(s)</summary>
          <ul className="mt-2 space-y-1">
            {v.messages.map((m, i) => (
              <li key={i} className="break-words">
                <span className={m.severity === "ERROR" || m.severity === "FATAL" ? "font-semibold text-red-700" : "font-semibold text-amber-700"}>{m.severity}</span>{" "}
                <span className="font-mono text-slate-500">{m.id}</span> {m.message}
                {m.location && <span className="text-slate-400"> ({m.location})</span>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function ExportRow({ e, onDelete }: { e: ExportItem; onDelete: (e: ExportItem) => void }) {
  const opts = [e.options.trim_size, e.options.paper, e.options.large_print ? "large print" : null].filter(Boolean).join(", ");
  return (
    <li className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-semibold text-slate-900">{EXPORT_LABELS[e.format] || e.format}</span>
          {opts && <span className="text-slate-500">({opts})</span>}
        </p>
        <p className="mt-0.5 break-all text-xs text-slate-500">
          {e.file_name} · {fmtBytes(e.file_size)}
          {e.page_count ? ` · ${e.page_count} pages` : ""} · {fmtDate(e.created_at)}
        </p>
        <Validation v={e.validation || {}} format={e.format} />
      </div>
      <div className="flex shrink-0 gap-2">
        <a href={apiUrl(paths.download(e.id))} download={e.file_name} className={buttonClasses({ size: "sm" })}>
          <Download className="h-3.5 w-3.5" /> Download
        </a>
        <Button size="sm" variant="ghost" className="text-red-600 hover:bg-red-50" onClick={() => onDelete(e)} aria-label={`Delete ${e.file_name}`}>
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </li>
  );
}

export function ExportTab() {
  const { book } = useBookCtx();
  const { mutate } = useSWRConfig();
  const { data: exports, isLoading } = useExports(book.id);
  const { run, busy } = useAction();
  const [toDelete, setToDelete] = useState<ExportItem | null>(null);

  return (
    <div className="space-y-8">
      {book.parts_written === 0 && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Nothing has been written yet, so exports will be empty.</p>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {FORMATS.map((f) => (
          <FormatCard key={f.id} {...f} />
        ))}
      </div>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Files</h2>
        {isLoading ? (
          <Skeleton className="h-32" />
        ) : !exports?.length ? (
          <EmptyState icon={Download} title="No exports yet">
            Exported files appear here with validation results.
          </EmptyState>
        ) : (
          <Card>
            <ul className="divide-y divide-slate-100">
              {exports.map((e) => (
                <ExportRow key={e.id} e={e} onDelete={setToDelete} />
              ))}
            </ul>
          </Card>
        )}
      </section>

      <ConfirmDialog
        open={!!toDelete}
        onClose={() => setToDelete(null)}
        title="Delete this export?"
        description={toDelete ? `${toDelete.file_name} will be removed from the server.` : undefined}
        confirmLabel="Delete"
        destructive
        pending={busy}
        onConfirm={async () => {
          if (!toDelete) return;
          const id = toDelete.id;
          const ok = await run("del", () => api.deleteExport(id).then(() => true), "Export deleted");
          if (ok) {
            mutate<ExportItem[]>(paths.exports(book.id), (list) => (list || []).filter((x) => x.id !== id), { revalidate: true });
            mutate(paths.readiness(book.id));
          }
        }}
      />
    </div>
  );
}
