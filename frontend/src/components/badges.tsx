import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { BOOK_STATUS_LABELS, humanize, capitalize, scoreTone } from "@/lib/format";
import type { Severity } from "@/lib/api";

const BOOK_STATUS: Record<string, BadgeVariant> = {
  planning: "secondary",
  outline_review: "warning",
  writing: "info",
  editing: "purple",
};

export function BookStatusBadge({ status }: { status: string }) {
  return <Badge variant={BOOK_STATUS[status] || "secondary"}>{BOOK_STATUS_LABELS[status] || capitalize(humanize(status))}</Badge>;
}

const PART_STATUS: Record<string, { variant: BadgeVariant; label: string }> = {
  approved: { variant: "success", label: "Approved" },
  pending_review: { variant: "warning", label: "Needs review" },
  changes_requested: { variant: "info", label: "Revising" },
  not_written: { variant: "outline", label: "Not written" },
};

export function PartStatusBadge({ status }: { status: string }) {
  const s = PART_STATUS[status] || { variant: "secondary" as BadgeVariant, label: capitalize(humanize(status)) };
  return <Badge variant={s.variant}>{s.label}</Badge>;
}

const SEVERITY: Record<Severity, BadgeVariant> = {
  critical: "destructive",
  major: "warning",
  minor: "info",
  info: "secondary",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge variant={SEVERITY[severity] || "secondary"} className="uppercase tracking-wide">
      {severity}
    </Badge>
  );
}

export function ScoreBadge({ score, className }: { score: number | null | undefined; className?: string }) {
  if (score === null || score === undefined) return null;
  return (
    <Badge variant={scoreTone(score)} className={className} title="Latest quality score">
      QA {Math.round(score)}
    </Badge>
  );
}
