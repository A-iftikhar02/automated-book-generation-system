"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSWRConfig } from "swr";
import { ArrowLeft, ArrowRight, Check, Sparkles } from "lucide-react";
import { api, errorMessage, paths, type Category } from "@/lib/api";
import { useAction, useCatalog } from "@/lib/hooks";
import { PageHeader } from "@/components/PageHeader";
import { SetupBanner } from "@/components/SetupBanner";
import { CategoryStep } from "@/components/wizard/CategoryStep";
import { DetailsStep } from "@/components/wizard/DetailsStep";
import { StoryStep } from "@/components/wizard/StoryStep";
import { INITIAL, type SetField, type WizardState } from "@/components/wizard/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const STEPS = ["Format", "Genre & audience", "Story & settings"];

export default function NewBookPage() {
  const router = useRouter();
  const { mutate } = useSWRConfig();
  const { data: catalog, error, isLoading } = useCatalog();
  const { run, busy } = useAction();
  const [step, setStep] = useState(0);
  const [state, setState] = useState<WizardState>(INITIAL);

  const set: SetField = (key, value) => setState((s) => ({ ...s, [key]: value }));
  const category = catalog?.categories.find((c) => c.key === state.category);

  const selectCategory = (c: Category) => {
    setState((s) => {
      const genres = c.fiction ? catalog!.fiction_genres : catalog!.nonfiction_genres;
      return {
        ...s,
        category: c.key,
        genre: s.genre in genres ? s.genre : "",
        audience: c.allowed_audiences.includes(s.audience) ? s.audience : c.allowed_audiences.includes("adult") ? "adult" : c.allowed_audiences[0],
        target_word_count: c.default_words,
        target_chapter_count: c.default_parts,
      };
    });
  };

  const valid = [
    !!category,
    !!state.genre && !!state.audience,
    state.title.trim().length > 0 &&
      state.premise.trim().length >= 20 &&
      !!category &&
      state.target_chapter_count >= category.min_parts &&
      state.target_chapter_count <= category.max_parts,
  ];

  const submit = async () => {
    if (!category) return;
    const book = await run("create", () =>
      api.createBook({
        title: state.title.trim(),
        subtitle: state.subtitle.trim() || null,
        author_name: state.author_name.trim(),
        category: state.category,
        genre: state.genre,
        audience: state.audience,
        content_rating: state.content_rating,
        ...(category.fiction ? { pov: state.pov, tense: state.tense } : {}),
        tone: state.tone.trim() || null,
        premise: state.premise.trim(),
        style_notes: state.style_notes.trim() || null,
        target_word_count: state.target_word_count,
        target_chapter_count: state.target_chapter_count,
        review_mode: state.review_mode,
        writer_model: state.writer_model || null,
        editor_model: state.editor_model || null,
      }),
      "Book created. Planning has started.",
    );
    if (book) {
      mutate(paths.books);
      router.push(`/books/${book.id}`);
    }
  };

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="New book" description="Choose a format, set the direction, and BookPilot will plan an outline for your review." />
      <SetupBanner compact />

      <ol className="mb-6 flex flex-wrap gap-2" aria-label="Steps">
        {STEPS.map((s, i) => {
          const done = i < step;
          const current = i === step;
          const reachable = i <= step || valid.slice(0, i).every(Boolean);
          return (
            <li key={s}>
              <button
                type="button"
                onClick={() => reachable && setStep(i)}
                disabled={!reachable}
                aria-current={current ? "step" : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed",
                  current ? "border-blue-600 bg-blue-600 text-white" : done ? "border-blue-200 bg-blue-50 text-blue-700" : "border-slate-200 bg-white text-slate-500",
                )}
              >
                <span className={cn("flex h-5 w-5 items-center justify-center rounded-full text-xs", current ? "bg-white/20" : "bg-slate-100")}>
                  {done ? <Check className="h-3 w-3" /> : i + 1}
                </span>
                {s}
              </button>
            </li>
          );
        })}
      </ol>

      {error ? (
        <EmptyState title="Could not load the catalog">{errorMessage(error)}</EmptyState>
      ) : isLoading || !catalog ? (
        <Skeleton className="h-96" />
      ) : (
        <form
          onKeyDown={(e) => {
            // Enter in a text field (e.g. the model search) shouldn't submit the wizard.
            if (e.key === "Enter" && (e.target as HTMLElement).tagName === "INPUT") e.preventDefault();
          }}
          onSubmit={(e) => {
            e.preventDefault();
            if (step < 2 && valid[step]) setStep(step + 1);
            else if (step === 2 && valid.every(Boolean)) submit();
          }}
        >
          <Card className="p-4 sm:p-6">
            {step === 0 && <CategoryStep categories={catalog.categories} value={state.category} onSelect={selectCategory} />}
            {step === 1 && category && <DetailsStep catalog={catalog} category={category} state={state} set={set} />}
            {step === 2 && category && <StoryStep category={category} state={state} set={set} />}
          </Card>

          <div className="mt-6 flex items-center justify-between gap-3">
            <Button type="button" variant="outline" onClick={() => setStep((s) => s - 1)} disabled={step === 0 || busy}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            {step < 2 ? (
              <Button type="submit" disabled={!valid[step]}>
                Continue <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button type="submit" disabled={!valid.every(Boolean)} loading={busy}>
                {!busy && <Sparkles className="h-4 w-4" />} Create & plan book
              </Button>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
