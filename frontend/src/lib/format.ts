import { formatDistanceToNowStrict } from "date-fns";
import type { Catalog, Category } from "./api";

export const fmtNumber = (n: number | null | undefined) => (n ?? 0).toLocaleString("en-US");

export function fmtCost(usd: number | null | undefined): string {
  const v = usd ?? 0;
  if (v === 0) return "$0.00";
  if (v < 0.01) return `$${v.toFixed(4)}`;
  return `$${v.toFixed(2)}`;
}

export function fmtBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function fmtAgo(iso: string | null | undefined): string {
  if (!iso) return "never";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${formatDistanceToNowStrict(d)} ago`;
}

/** Milliseconds since an ISO timestamp (null if missing). */
export function ageMs(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? null : Date.now() - t;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}

export function fmtPrice(perMillion: number | null | undefined): string {
  if (perMillion === null || perMillion === undefined) return "?";
  if (perMillion === 0) return "free";
  return `$${perMillion < 1 ? perMillion.toFixed(2) : perMillion.toFixed(perMillion < 10 ? 2 : 0)}`;
}

export const humanize = (s: string | null | undefined) =>
  (s || "").replace(/^lt:/, "").replace(/_/g, " ").replace(/\s+/g, " ").trim().toLowerCase();

export const capitalize = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);

export const BOOK_STATUS_LABELS: Record<string, string> = {
  planning: "Planning",
  outline_review: "Outline review",
  writing: "Writing",
  editing: "Editing & QA",
};

export const JOB_LABELS: Record<string, string> = {
  plan_book: "Planning the book",
  revise_outline: "Revising the outline",
  write_chapter: "Writing",
  write_book: "Autopilot writing",
  revise_chapter: "Revising",
  qa: "Quality check",
  autofix: "Auto-fixing issues",
  ai_fix: "AI fixing issues",
  metadata: "Writing store listing",
  cover: "Generating cover",
  export: "Exporting",
};

export function jobLabel(type: string, payload?: Record<string, unknown>, partLabel = "Part"): string {
  const base = JOB_LABELS[type] || capitalize(humanize(type));
  const n = payload?.number;
  if (typeof n === "number" && ["write_chapter", "revise_chapter", "ai_fix"].includes(type)) {
    return `${base} ${partLabel.toLowerCase()} ${n}`;
  }
  if (type === "export" && typeof payload?.format === "string") return `${base} ${EXPORT_LABELS[payload.format] || payload.format}`;
  return base;
}

export const EXPORT_LABELS: Record<string, string> = {
  epub: "EPUB",
  print_pdf: "Print PDF",
  cover_wrap_pdf: "Cover wrap PDF",
  docx: "DOCX",
  txt: "Plain text",
};

export function findCategory(catalog: Catalog | undefined, key: string): Category | undefined {
  return catalog?.categories.find((c) => c.key === key);
}

export function genreLabel(catalog: Catalog | undefined, key: string): string {
  return catalog?.fiction_genres[key] || catalog?.nonfiction_genres[key] || capitalize(humanize(key));
}

export function categoryLabel(catalog: Catalog | undefined, key: string): string {
  return findCategory(catalog, key)?.label || capitalize(humanize(key));
}

export function partLabelFor(catalog: Catalog | undefined, key: string): string {
  return findCategory(catalog, key)?.part_label || "Part";
}

export function plural(label: string, n?: number): string {
  if (n === 1) return label;
  if (label.endsWith("y")) return `${label.slice(0, -1)}ies`;
  return `${label}s`;
}

export function scoreTone(score: number | null | undefined): "success" | "info" | "warning" | "destructive" | "secondary" {
  if (score === null || score === undefined) return "secondary";
  if (score >= 90) return "success";
  if (score >= 80) return "info";
  if (score >= 65) return "warning";
  return "destructive";
}
