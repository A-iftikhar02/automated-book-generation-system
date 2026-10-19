"use client";

import Link from "next/link";
import { TriangleAlert } from "lucide-react";
import { useSystemStatus } from "@/lib/hooks";

/** Lists configuration problems from /api/system/status. Renders nothing when everything is fine. */
export function SetupBanner({ compact = false }: { compact?: boolean }) {
  const { data, error } = useSystemStatus();
  const problems: string[] = [];
  if (error) problems.push("The API is unreachable. Start the backend and check NEXT_PUBLIC_API_URL.");
  if (data) {
    if (!data.database) problems.push("The database is down.");
    if (!data.ai.configured)
      problems.push(
        "No AI provider configured for the writer/editor models: planning, writing and AI checks are disabled. Add an API key (OpenRouter, Gemini, Groq, Cerebras or Mistral) to .env.",
      );
    if (!data.languagetool.available)
      problems.push(`LanguageTool unavailable at ${data.languagetool.url}: spelling and grammar checks will be skipped.`);
  }
  if (!problems.length) return null;
  return (
    <div role="status" className="mb-6 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
      <TriangleAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" aria-hidden />
      <div className="min-w-0">
        <p className="font-semibold">Setup needed</p>
        {compact ? (
          <p className="mt-0.5">{problems[0]}</p>
        ) : (
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {problems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        )}
        <Link href="/settings" className="mt-1 inline-block font-semibold text-amber-800 underline underline-offset-2 hover:text-amber-950">
          Open settings
        </Link>
      </div>
    </div>
  );
}
