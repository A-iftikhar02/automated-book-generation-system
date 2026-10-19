"use client";

import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BookOpen, FileDown, Gauge, LayoutDashboard, ListTree, Rocket, ScrollText } from "lucide-react";
import { errorMessage } from "@/lib/api";
import { useBook, useBookJobs, useCatalog, useJobsFinished, useRefreshBook, useSystemStatus } from "@/lib/hooks";
import { findCategory } from "@/lib/format";
import { FailedJob, JobProgress } from "@/components/JobProgress";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabPanel, type TabItem } from "@/components/ui/tabs";
import { BookHeader } from "./BookHeader";
import { BookProvider, type BookContextValue, type TabId } from "./context";
import { OverviewTab } from "./OverviewTab";
import { OutlineTab } from "./OutlineTab";
import { ManuscriptTab } from "./ManuscriptTab";
import { QualityTab } from "./QualityTab";
import { PublishTab } from "./PublishTab";
import { ExportTab } from "./ExportTab";

const TABS: TabItem<TabId>[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "outline", label: "Outline", icon: ListTree },
  { id: "manuscript", label: "Manuscript", icon: ScrollText },
  { id: "quality", label: "Quality", icon: Gauge },
  { id: "publish", label: "Publish", icon: Rocket },
  { id: "export", label: "Export", icon: FileDown },
];
const TAB_IDS = TABS.map((t) => t.id);

export function WorkspaceSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex gap-4">
        <Skeleton className="h-36 w-24" />
        <div className="flex-1 space-y-3">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-80 w-full" />
    </div>
  );
}

export function BookWorkspace({ id }: { id: string }) {
  const params = useSearchParams();
  const { data: book, error, isLoading } = useBook(id);
  const { data: catalog } = useCatalog();
  const { data: status } = useSystemStatus();
  const { data: jobHistory } = useBookJobs(id);
  const refresh = useRefreshBook(id);
  const [dismissed, setDismissed] = useState<string | null>(null);

  const tabParam = params.get("tab") as TabId | null;
  const tab: TabId = tabParam && TAB_IDS.includes(tabParam) ? tabParam : "overview";
  const partParam = Number(params.get("part")) || null;
  const [selectedPart, setSelectedPartState] = useState<number | null>(partParam);

  const writeUrl = useCallback((t: TabId, part: number | null) => {
    const sp = new URLSearchParams();
    if (t !== "overview") sp.set("tab", t);
    if (part && t === "manuscript") sp.set("part", String(part));
    const s = sp.toString();
    window.history.replaceState(null, "", s ? `?${s}` : window.location.pathname);
  }, []);

  const goTo = useCallback(
    (t: TabId, part?: number) => {
      const p = part ?? selectedPart;
      if (part !== undefined) setSelectedPartState(part);
      writeUrl(t, p);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [selectedPart, writeUrl],
  );

  const setSelectedPart = useCallback(
    (n: number | null) => {
      setSelectedPartState(n);
      writeUrl(tab, n);
    },
    [tab, writeUrl],
  );

  // When a job finishes, refresh everything that may depend on it (chapters, QA, exports, cover...).
  useJobsFinished(book?.jobs, () => {
    refresh();
  });

  const failed = useMemo(() => {
    if (!jobHistory) return null;
    const f = jobHistory.find((j) => j.status === "failed");
    if (!f || f.id === dismissed) return null;
    // Hide if a newer job of the same type has since been queued (e.g. after Retry).
    const superseded = jobHistory.some(
      (j) => j.type === f.type && j.created_at > f.created_at && JSON.stringify(j.payload) === JSON.stringify(f.payload),
    );
    return superseded ? null : f;
  }, [jobHistory, dismissed]);

  const category = book ? findCategory(catalog, book.category) : undefined;
  const ctx = useMemo<BookContextValue | null>(
    () =>
      book
        ? {
            book,
            catalog,
            category,
            partLabel: category?.part_label || "Part",
            aiReady: status ? status.ai.configured : true,
            refresh,
            goTo,
            selectedPart,
            setSelectedPart,
            coverVersion: String(book.cover_version ?? 0),
          }
        : null,
    [book, catalog, category, status, refresh, goTo, selectedPart, setSelectedPart],
  );

  if (error && !book) {
    return (
      <EmptyState
        icon={BookOpen}
        title={(error as { status?: number }).status === 404 ? "Book not found" : "Could not load this book"}
        action={<LinkButton href="/books" variant="outline">Back to library</LinkButton>}
      >
        {errorMessage(error)}
      </EmptyState>
    );
  }
  if (isLoading || !ctx || !book) return <WorkspaceSkeleton />;

  return (
    <BookProvider value={ctx}>
      <BookHeader />

      {book.jobs.length > 0 && (
        <Card className="mb-4 space-y-4 border-blue-200 bg-blue-50/40 p-4" aria-live="polite">
          {book.jobs.map((j) => (
            <JobProgress key={j.id} job={j} partLabel={ctx.partLabel} onChange={refresh} />
          ))}
        </Card>
      )}
      {failed && (
        <div className="mb-4">
          <FailedJob job={failed} partLabel={ctx.partLabel} onRetry={refresh} onDismiss={() => setDismissed(failed.id)} />
        </div>
      )}
      {!ctx.aiReady && (
        <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          OpenRouter not configured: AI writing, revision, listing and cover actions will fail until OPENROUTER_API_KEY is set. QA (without AI),
          auto-fix, typographic covers and exports still work.
        </p>
      )}

      <Tabs tabs={TABS} value={tab} onChange={(t) => goTo(t)} label="Book sections" />
      <div className="mt-6">
        <TabPanel id={tab}>
          {tab === "overview" && <OverviewTab />}
          {tab === "outline" && <OutlineTab />}
          {tab === "manuscript" && <ManuscriptTab />}
          {tab === "quality" && <QualityTab />}
          {tab === "publish" && <PublishTab />}
          {tab === "export" && <ExportTab />}
        </TabPanel>
      </div>
    </BookProvider>
  );
}
