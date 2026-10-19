/**
 * Typed client for the BookPilot FastAPI backend. Types mirror `app/schemas.py`.
 * Every endpoint lives under `/api`; errors come back as `{ detail }`.
 */

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

// ---------- catalog ----------

export type Structure = "chapters" | "scenes" | "stories" | "poems";

export interface Category {
  key: string;
  label: string;
  description: string;
  fiction: boolean;
  structure: Structure;
  min_words: number;
  max_words: number;
  default_words: number;
  min_parts: number;
  max_parts: number;
  default_parts: number;
  part_label: string;
  writing_notes: string;
  allowed_audiences: string[];
}

export interface Catalog {
  categories: Category[];
  fiction_genres: Record<string, string>;
  nonfiction_genres: Record<string, string>;
  audiences: Record<string, { label: string; max_grade: number; max_avg_sentence: number }>;
  content_ratings: Record<string, string>;
  povs: Record<string, string>;
  tenses: Record<string, string>;
  trim_sizes: Record<string, { width: number; height: number }>;
  paper_types: string[];
  export_formats: Record<string, string>;
}

// ---------- books ----------

export type BookStatus = "planning" | "outline_review" | "writing" | "editing";
export type ReviewMode = "manual" | "autopilot";

export interface BookSummary {
  id: string;
  title: string;
  subtitle: string | null;
  author_name: string;
  category: string;
  genre: string;
  audience: string;
  status: BookStatus;
  review_mode: ReviewMode;
  target_word_count: number;
  target_chapter_count: number;
  cost_usd: number;
  created_at: string;
  updated_at: string;
  words_written: number;
  parts_written: number;
  parts_approved: number;
  has_cover: boolean;
  /** Changes whenever the cover file changes; used to bust the image cache. */
  cover_version: number | null;
  quality_score: number | null;
  active_job: string | null;
}

export interface OutlinePart {
  number: number;
  title: string;
  synopsis: string;
  beats: string[];
  target_words: number;
}

export interface Outline {
  id: string;
  version: number;
  synopsis: string;
  chapters: OutlinePart[];
  status: "pending_review" | "approved" | "changes_requested" | string;
  feedback: string | null;
  created_at: string;
}

export type ChapterStatus = "pending_review" | "approved" | "changes_requested" | string;

export interface ChapterBrief {
  number: number;
  title: string;
  summary: string;
  word_count: number;
  status: ChapterStatus;
  feedback: string | null;
  revision: number;
  updated_at: string;
}

export interface Chapter extends ChapterBrief {
  content: string;
}

export interface Revision {
  id: string;
  revision: number;
  title: string;
  reason: string;
  created_at: string;
  word_count: number;
}

export interface RevisionDetail {
  revision: number;
  title: string;
  content: string;
  reason: string;
  created_at: string;
}

export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface Job {
  id: string;
  book_id: string | null;
  type: string;
  payload: Record<string, unknown>;
  status: JobStatus;
  progress: number;
  message: string | null;
  error: string | null;
  result: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export type StoryBible = Record<string, unknown>;

export interface BookDetail extends BookSummary {
  tone: string | null;
  language: string;
  content_rating: string;
  pov: string;
  tense: string;
  premise: string;
  style_notes: string | null;
  writer_model: string | null;
  editor_model: string | null;
  story_bible: StoryBible;
  description: string | null;
  back_cover_copy: string | null;
  keywords: string[];
  store_categories: string[];
  series_name: string | null;
  series_number: number | null;
  edition: string | null;
  publisher: string | null;
  copyright_holder: string | null;
  publication_year: number | null;
  isbn_ebook: string | null;
  isbn_print: string | null;
  dedication: string | null;
  acknowledgments: string | null;
  author_bio: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  outline: Outline | null;
  chapters: ChapterBrief[];
  jobs: Job[];
  next_part: number | null;
}

export interface BookCreate {
  title: string;
  subtitle?: string | null;
  author_name?: string;
  category: string;
  genre: string;
  audience?: string;
  content_rating?: string;
  pov?: string;
  tense?: string;
  tone?: string | null;
  language?: string;
  premise: string;
  style_notes?: string | null;
  target_word_count?: number | null;
  target_chapter_count?: number | null;
  review_mode?: ReviewMode;
  writer_model?: string | null;
  editor_model?: string | null;
}

export type BookUpdate = Partial<
  Pick<
    BookDetail,
    | "title"
    | "subtitle"
    | "author_name"
    | "tone"
    | "style_notes"
    | "review_mode"
    | "writer_model"
    | "editor_model"
    | "language"
    | "description"
    | "back_cover_copy"
    | "keywords"
    | "store_categories"
    | "series_name"
    | "series_number"
    | "edition"
    | "publisher"
    | "copyright_holder"
    | "publication_year"
    | "isbn_ebook"
    | "isbn_print"
    | "dedication"
    | "acknowledgments"
    | "author_bio"
  >
>;

// ---------- QA ----------

export type Severity = "critical" | "major" | "minor" | "info";
export type IssueStatus = "open" | "fixed" | "ignored" | "superseded";
export type IssueSource = "rule" | "languagetool" | "ai";

export interface Issue {
  id: string;
  chapter_number: number | null;
  category: string;
  check: string;
  severity: Severity;
  source: IssueSource;
  message: string;
  excerpt: string | null;
  suggestion: string | null;
  offset: number | null;
  length: number | null;
  /** Exact flagged text at `offset` when the check ran. */
  matched: string | null;
  replacements: string[];
  status: IssueStatus;
  created_at: string;
}

export interface ChapterStats {
  score?: number;
  words?: number;
  issues?: number;
  fk_grade?: number;
  sentences?: number;
  paragraphs?: number;
  reading_ease?: number;
  passive_ratio?: number;
  dialogue_ratio?: number;
  reading_minutes?: number;
  adverbs_per_1000?: number;
  fillers_per_1000?: number;
  avg_sentence_words?: number;
  sentence_length_stdev?: number;
}

export interface QARun {
  id: string;
  chapter_numbers: number[];
  include_ai: boolean;
  status: string;
  score: number | null;
  stats?: Record<string, unknown>;
  warnings: string[];
  created_at: string;
  completed_at: string | null;
}

export interface QAOverview {
  score: number | null;
  grade: string | null;
  latest_run: QARun | null;
  book_review: { verdict?: string | null; summary?: string | null } | null;
  chapter_scores: Record<string, number>;
  chapter_stats: Record<string, ChapterStats>;
  open_issues: number;
  auto_fixable: number;
  by_severity: Record<Severity, number>;
  by_category: Record<string, number>;
  by_chapter: Record<string, number>;
  runs: QARun[];
}

export interface IssueFilters {
  status?: IssueStatus | "all";
  severity?: string;
  category?: string;
  chapter?: number;
  book_level?: boolean;
  source?: string;
  limit?: number;
  offset?: number;
}

// ---------- publishing ----------

export type CheckStatus = "pass" | "warn" | "fail" | "info";

export interface ReadinessItem {
  key: string;
  label: string;
  status: CheckStatus;
  detail: string;
  store: "all" | "kdp" | string;
}

export interface Readiness {
  ready: boolean;
  blocking: number;
  items: ReadinessItem[];
}

export type ExportFormat = "epub" | "print_pdf" | "cover_wrap_pdf" | "docx" | "txt";

export interface ExportValidation {
  valid?: boolean | null;
  tool?: string | null;
  note?: string;
  error?: string;
  errors?: number;
  warnings?: string[] | number;
  messages?: { severity: string; id: string; message: string; location: string | null }[];
  page_count?: number;
  trim_size?: string;
  paper?: string;
  spine_width_in?: number;
  full_width_in?: number;
  full_height_in?: number;
  inside_margin_in?: number;
  kdp_min_inside_margin_in?: number;
  fonts_embedded?: boolean;
  barcode_area?: string;
  [key: string]: unknown;
}

export interface ExportItem {
  id: string;
  format: ExportFormat;
  options: { trim_size?: string; large_print?: boolean; paper?: string };
  file_size: number;
  page_count: number | null;
  validation: ExportValidation;
  created_at: string;
  file_name: string;
}

export interface ExportRequest {
  format: ExportFormat;
  trim_size?: string;
  paper?: "white" | "cream";
  large_print?: boolean;
}

// ---------- system ----------

export interface SystemStatus {
  version: string;
  database: boolean;
  ai: {
    /** True when the writer and editor chains each have at least one configured provider. */
    configured: boolean;
    writer_models: string[];
    editor_models: string[];
    image_model: string;
    image_configured: boolean;
    providers: ProviderStatus[];
  };
  languagetool: { url: string; available: boolean };
  slack: { enabled: boolean; configured: boolean; active: boolean };
  epubcheck: { available: boolean };
  worker: { in_process: boolean; last_heartbeat: string | null; queued_jobs: number };
}

export interface ProviderStatus {
  name: string;
  label: string;
  configured: boolean;
  key_url: string;
  free_tier: string;
  env_var: string;
  link_label: string;
}

export interface ModelInfo {
  /** "provider:model" (no prefix = OpenRouter); use as-is in model fields. */
  id: string;
  provider: string;
  /** OpenRouter price is zero, or another provider used on its free tier. */
  free: boolean;
  name: string;
  context_length: number | null;
  prompt_price_per_million: number | null;
  completion_price_per_million: number | null;
  output_modalities: string[];
}

export interface ModelCatalog {
  models: ModelInfo[];
  /** Providers whose model list couldn't be loaded, with the reason. */
  errors: Record<string, string>;
}

// ---------- transport ----------

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

interface ValidationDetail {
  loc?: (string | number)[];
  msg?: string;
}

/** Turn a FastAPI `detail` (string or 422 list) into a readable sentence. */
export function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: ValidationDetail) => {
        const field = (d.loc || []).filter((p) => p !== "body" && p !== "query" && p !== "path").join(".");
        const msg = (d.msg || "Invalid value").replace(/^Value error, /, "");
        return field ? `${field.replace(/_/g, " ")}: ${msg}` : msg;
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return "Request failed";
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof TypeError) return `Cannot reach the API at ${API_URL}. Is the backend running?`;
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

export function apiUrl(path: string): string {
  return `${API_URL}${path}`;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, headers: {} };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    init.body = JSON.stringify(body);
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  const res = await fetch(apiUrl(path), init);
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data && "detail" in data) message = formatDetail(data.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

/** SWR fetcher: keys are API paths. */
export const fetcher = <T,>(path: string) => request<T>("GET", path);

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") search.set(k, String(v));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

// ---------- paths (also used as SWR keys) ----------

export const paths = {
  catalog: "/api/catalog",
  status: "/api/system/status",
  models: "/api/system/models",
  books: "/api/books",
  book: (id: string) => `/api/books/${id}`,
  outlines: (id: string) => `/api/books/${id}/outlines`,
  chapter: (id: string, n: number) => `/api/books/${id}/chapters/${n}`,
  revisions: (id: string, n: number) => `/api/books/${id}/chapters/${n}/revisions`,
  qa: (id: string) => `/api/books/${id}/qa`,
  issues: (id: string, f: IssueFilters = {}) => `/api/books/${id}/qa/issues${qs({ ...f })}`,
  readiness: (id: string) => `/api/books/${id}/readiness`,
  exports: (id: string) => `/api/books/${id}/exports`,
  jobs: (p: { book_id?: string; active?: boolean; limit?: number } = {}) => `/api/jobs${qs(p)}`,
  cover: (id: string, version?: string | number | null) => `/api/books/${id}/cover${version ? qs({ v: String(version) }) : ""}`,
  download: (exportId: string) => `/api/exports/${exportId}/download`,
};

// ---------- mutations ----------

export const api = {
  createBook: (data: BookCreate) => request<BookDetail>("POST", "/api/books", data),
  updateBook: (id: string, data: BookUpdate) => request<BookDetail>("PATCH", paths.book(id), data),
  deleteBook: (id: string) => request<void>("DELETE", paths.book(id)),
  replan: (id: string) => request<Job>("POST", `${paths.book(id)}/replan`),
  saveStoryBible: (id: string, story_bible: StoryBible) =>
    request<BookDetail>("PUT", `${paths.book(id)}/story-bible`, { story_bible }),

  saveOutline: (id: string, data: { synopsis?: string | null; chapters: Partial<OutlinePart>[] }) =>
    request<Outline>("PUT", `${paths.book(id)}/outline`, data),
  approveOutline: (id: string) => request<BookDetail>("POST", `${paths.book(id)}/outline/approve`),
  reviseOutline: (id: string, feedback: string) =>
    request<Job>("POST", `${paths.book(id)}/outline/revise`, { feedback }),

  saveChapter: (id: string, n: number, data: { title?: string; content?: string }) =>
    request<Chapter>("PUT", paths.chapter(id, n), data),
  writeChapter: (id: string, n: number, notes?: string) =>
    request<Job>("POST", `${paths.chapter(id, n)}/write`, { notes: notes || null }),
  writeAll: (id: string) => request<Job>("POST", `${paths.book(id)}/write-all`),
  approveChapter: (id: string, n: number, continue_writing: boolean) =>
    request<BookDetail>("POST", `${paths.chapter(id, n)}/approve`, { continue_writing }),
  reviseChapter: (id: string, n: number, instructions: string, mode: "revise" | "rewrite") =>
    request<Job>("POST", `${paths.chapter(id, n)}/revise`, { instructions, mode }),
  getRevision: (id: string, n: number, revId: string) =>
    request<RevisionDetail>("GET", `${paths.revisions(id, n)}/${revId}`),
  restoreRevision: (id: string, n: number, revId: string) =>
    request<Chapter>("POST", `${paths.revisions(id, n)}/${revId}/restore`),

  runQa: (id: string, chapters: number[] | null, include_ai: boolean) =>
    request<Job>("POST", paths.qa(id), { chapters, include_ai }),
  autofix: (id: string, chapters: number[] | null = null) =>
    request<Job>("POST", `${paths.qa(id)}/autofix`, { chapters }),
  aiFix: (id: string, n: number, issue_ids: string[] | null = null) =>
    request<Job>("POST", `${paths.chapter(id, n)}/ai-fix`, { issue_ids }),
  updateIssue: (issueId: string, status: "open" | "ignored" | "fixed") =>
    request<Issue>("PATCH", `/api/qa/issues/${issueId}`, { status }),
  applyIssue: (issueId: string, replacement: string | null) =>
    request<Issue>("POST", `/api/qa/issues/${issueId}/apply`, { replacement }),

  generateMetadata: (id: string, overwrite: boolean) =>
    request<Job>("POST", `${paths.book(id)}/metadata/generate`, { overwrite }),
  generateCover: (id: string, use_ai: boolean, prompt?: string) =>
    request<Job>("POST", `${paths.book(id)}/cover/generate`, { use_ai, prompt: prompt || null }),
  uploadCover: (id: string, file: File, finishedDesign: boolean) => {
    const form = new FormData();
    form.append("file", file);
    form.append("finished_design", String(finishedDesign));
    return request<{ width: number; height: number; warnings: string[] }>("POST", `${paths.book(id)}/cover`, form);
  },
  deleteCover: (id: string) => request<void>("DELETE", `${paths.book(id)}/cover`),

  createExport: (id: string, data: ExportRequest) => request<Job>("POST", paths.exports(id), data),
  deleteExport: (exportId: string) => request<void>("DELETE", `/api/exports/${exportId}`),

  cancelJob: (jobId: string) => request<Job>("POST", `/api/jobs/${jobId}/cancel`),
  retryJob: (jobId: string) => request<Job>("POST", `/api/jobs/${jobId}/retry`),
  testNotification: () => request<{ sent: boolean; reason: string | null }>("POST", "/api/system/test-notification"),
};
