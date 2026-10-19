"use client";

import { CircleCheck, CircleX, Info, TriangleAlert } from "lucide-react";
import { errorMessage, type CheckStatus } from "@/lib/api";
import { useReadiness } from "@/lib/hooks";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useBookCtx } from "./context";
import { CoverSection } from "./CoverSection";
import { MetadataForm } from "./MetadataForm";

const ICONS: Record<CheckStatus, { icon: React.ComponentType<{ className?: string }>; className: string; label: string }> = {
  pass: { icon: CircleCheck, className: "text-green-600", label: "Pass" },
  warn: { icon: TriangleAlert, className: "text-amber-500", label: "Warning" },
  fail: { icon: CircleX, className: "text-red-600", label: "Fail" },
  info: { icon: Info, className: "text-blue-500", label: "Info" },
};

function Readiness() {
  const { book } = useBookCtx();
  const { data, error, isLoading } = useReadiness(book.id);
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">Readiness checklist</CardTitle>
          {data && (
            <Badge variant={data.ready ? "success" : "destructive"}>{data.ready ? "Ready" : `${data.blocking} blocking`}</Badge>
          )}
        </div>
        <p className="text-xs text-slate-500">Amazon KDP and Apple Books requirements.</p>
      </CardHeader>
      <CardContent>
        {error ? (
          <p className="text-sm text-red-600">{errorMessage(error)}</p>
        ) : isLoading || !data ? (
          <Skeleton className="h-64" />
        ) : (
          <ul className="space-y-3">
            {data.items.map((item) => {
              const s = ICONS[item.status] || ICONS.info;
              return (
                <li key={item.key} className="flex gap-2.5">
                  <s.icon className={`mt-0.5 h-4 w-4 shrink-0 ${s.className}`} aria-label={s.label} />
                  <div className="min-w-0 text-sm">
                    <p className="font-medium text-slate-900">
                      {item.label}
                      {item.store === "kdp" && (
                        <Badge variant="outline" className="ml-2 px-1.5 py-0 text-[10px]">
                          KDP
                        </Badge>
                      )}
                    </p>
                    {item.detail && <p className="break-words text-xs text-slate-500">{item.detail}</p>}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          <p className="font-semibold">Disclose AI-generated content</p>
          <p className="mt-1">
            Amazon KDP asks you to declare AI-generated text, images and translations when you publish or update a title. Answer
            &quot;yes&quot; for text written by BookPilot and for AI covers, even if you edited them. Check each store&apos;s current policy.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export function PublishTab() {
  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_22rem]">
      <div className="min-w-0 space-y-6">
        <CoverSection />
        <MetadataForm />
      </div>
      <div className="xl:sticky xl:top-6 xl:self-start">
        <Readiness />
      </div>
    </div>
  );
}
