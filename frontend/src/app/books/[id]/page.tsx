"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { 
  fetchBookDetails, Book, Outline, Chapter, FinalDraft,
  reviewOutline, regenerateOutline, generateChapter, reviewChapter, regenerateChapter, reviewBook, compileBook
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

import { Loader2, CheckCircle, FileText, PenTool, Download, ChevronDown, ChevronUp, RefreshCw, Check } from "lucide-react";
import { cn } from "@/lib/utils";

// Minimal Toast Implementation for this page
function Toast({ message, type, onClose }: { message: string, type: 'success' | 'error', onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  if (!message) return null;
  return (
    <div className={cn(
      "fixed bottom-6 right-6 px-4 py-3 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2 z-50 animate-in slide-in-from-bottom-5",
      type === 'success' ? "bg-green-600 text-white" : "bg-red-600 text-white"
    )}>
      {type === 'success' ? <Check className="w-4 h-4" /> : <Loader2 className="w-4 h-4" />}
      {message}
    </div>
  );
}

export default function BookDetail() {
  const params = useParams();
  const bookId = params.id as string;
  
  const [data, setData] = useState<{ book?: Book, outline?: Outline, chapters: Chapter[], finalDraft?: FinalDraft } | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Outline Review State
  const [outlineNotes, setOutlineNotes] = useState("");
  const [outlineSubmitting, setOutlineSubmitting] = useState(false);

  // Chapters State
  const [chapterNotes, setChapterNotes] = useState<Record<number, string>>({});
  const [chapterSubmitting, setChapterSubmitting] = useState<Record<number, boolean>>({});
  const [expandedChapters, setExpandedChapters] = useState<Record<number, boolean>>({});
  const [nextChapterNum, setNextChapterNum] = useState(1);

  // Final Compile State
  const [finalNotes, setFinalNotes] = useState("");
  const [finalSubmitting, setFinalSubmitting] = useState(false);

  // Toast state
  const [toast, setToast] = useState<{ message: string, type: 'success'|'error' } | null>(null);

  const loadData = () => {
    fetchBookDetails(bookId)
      .then((res) => {
        setData(res);
        if (res.chapters && res.chapters.length > 0) {
          const max = Math.max(...res.chapters.map(c => c.chapter_number));
          setNextChapterNum(max + 1);
        } else {
          setNextChapterNum(1);
        }
      })
      .catch((err) => {
        console.error(err);
        setToast({ message: "Failed to load book details.", type: "error" });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId, refreshTrigger]);

  const refresh = () => setRefreshTrigger(prev => prev + 1);
  const showToast = (message: string, type: 'success'|'error' = 'success') => setToast({ message, type });

  // -- Handlers --
  const handleOutlineReview = async (status: string) => {
    try {
      setOutlineSubmitting(true);
      await reviewOutline(bookId, status, outlineNotes);
      showToast(status === 'no_notes_needed' ? "Outline approved!" : "Feedback submitted.");
      refresh();
    } catch (e) {
      showToast("Failed to update outline review", "error");
    } finally {
      setOutlineSubmitting(false);
    }
  };

  const handleOutlineRegenerate = async () => {
    try {
      setOutlineSubmitting(true);
      await regenerateOutline(bookId);
      showToast("Outline regenerated successfully.");
      refresh();
    } catch (e) {
      showToast("Failed to regenerate outline", "error");
    } finally {
      setOutlineSubmitting(false);
    }
  };

  const handleGenerateNextChapter = async () => {
    try {
      setChapterSubmitting(prev => ({...prev, [nextChapterNum]: true}));
      await generateChapter(bookId, nextChapterNum);
      showToast(`Chapter ${nextChapterNum} generated!`);
      setExpandedChapters(prev => ({...prev, [nextChapterNum]: true}));
      refresh();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      showToast(err.response?.data?.detail || "Error generating chapter", "error");
    } finally {
      setChapterSubmitting(prev => ({...prev, [nextChapterNum]: false}));
    }
  };

  const handleChapterReview = async (chapterNum: number, status: string) => {
    try {
      setChapterSubmitting(prev => ({...prev, [chapterNum]: true}));
      await reviewChapter(bookId, chapterNum, status, chapterNotes[chapterNum]);
      showToast(`Chapter ${chapterNum} reviewed successfully.`);
      refresh();
    } catch (e) {
      showToast("Error updating chapter review", "error");
    } finally {
      setChapterSubmitting(prev => ({...prev, [chapterNum]: false}));
    }
  };

  const handleChapterRegenerate = async (chapterNum: number) => {
    try {
      setChapterSubmitting(prev => ({...prev, [chapterNum]: true}));
      await regenerateChapter(bookId, chapterNum);
      showToast(`Chapter ${chapterNum} regenerated!`);
      refresh();
    } catch (e) {
      showToast("Error regenerating chapter", "error");
    } finally {
      setChapterSubmitting(prev => ({...prev, [chapterNum]: false}));
    }
  };

  const handleFinalCompile = async () => {
    try {
      setFinalSubmitting(true);
      if (finalNotes) {
        await reviewBook(bookId, "yes", finalNotes);
      } else {
        await reviewBook(bookId, "no_notes_needed");
      }
      await compileBook(bookId);
      showToast("Final draft compiled successfully!");
      refresh();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      showToast(err.response?.data?.detail || "Error compiling book", "error");
    } finally {
      setFinalSubmitting(false);
    }
  };

  const toggleChapter = (num: number) => {
    setExpandedChapters(prev => ({ ...prev, [num]: !prev[num] }));
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-8">
        <Skeleton className="h-10 w-64 mb-8" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!data?.book) {
    return <div className="p-8 text-slate-500">Book not found or failed to load.</div>;
  }

  const { book, outline, chapters, finalDraft } = data;
  const outlineApproved = outline?.status_outline_notes === "no_notes_needed";
  const allChaptersApproved = chapters.length > 0 && chapters.every(c => c.chapter_notes_status === "no_notes_needed");
  
  // Progress Steps
  const currentStep = book.status === "completed" ? 3 : (allChaptersApproved ? 2 : (outlineApproved ? 1 : 0));
  const steps = [
    { label: "Outline", active: currentStep === 0, completed: currentStep > 0 },
    { label: "Chapters", active: currentStep === 1, completed: currentStep > 1 },
    { label: "Final", active: currentStep === 2 || currentStep === 3, completed: currentStep === 3 }
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">{book.title}</h1>
        <StatusBadge status={book.status} />
      </div>
          
          {/* Progress Indicator */}
          <div className="flex items-center justify-between max-w-2xl mx-auto mb-8 relative">
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-slate-200 rounded-full z-0"></div>
            {steps.map((step, idx) => (
              <div key={idx} className="relative z-10 flex flex-col items-center">
                <div className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm border-2 transition-colors",
                  step.completed ? "bg-blue-600 border-blue-600 text-white" : 
                  step.active ? "bg-white border-blue-600 text-blue-600" : "bg-white border-slate-300 text-slate-400"
                )}>
                  {step.completed ? <Check className="w-5 h-5" /> : idx + 1}
                </div>
                <span className={cn(
                  "absolute -bottom-6 text-sm font-medium whitespace-nowrap",
                  step.active || step.completed ? "text-slate-900" : "text-slate-400"
                )}>
                  {step.label}
                </span>
              </div>
            ))}
          </div>

          <div className="h-4"></div> {/* Spacer */}

          {/* Section A: Outline Review */}
          <Card className="border-slate-200 shadow-sm overflow-hidden">
            <CardHeader className={cn(
              "border-b border-slate-100 transition-colors",
              !outlineApproved ? "bg-blue-50/50" : "bg-white"
            )}>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <FileText className="w-5 h-5 text-blue-600" />
                  Outline Review
                </CardTitle>
                {outline && <StatusBadge status={outline.status_outline_notes} />}
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              {outline ? (
                <>
                  <div className="bg-slate-50 p-5 rounded-lg border border-slate-200 whitespace-pre-wrap text-sm text-slate-700 max-h-96 overflow-y-auto font-medium">
                    {outline.outline_text}
                  </div>

                  {!outlineApproved && (
                    <div className="space-y-4 pt-4 border-t border-slate-100">
                      <div className="space-y-2">
                        <Label className="text-slate-700">Editor Notes (Optional for approval, required for revisions)</Label>
                        <Textarea 
                          placeholder="What needs to change in this outline?"
                          value={outlineNotes}
                          onChange={(e) => setOutlineNotes(e.target.value)}
                          disabled={outlineSubmitting}
                          className="bg-white"
                        />
                      </div>
                      <div className="flex flex-wrap gap-3 items-center">
                        <Button 
                          className="bg-green-600 hover:bg-green-700 text-white"
                          onClick={() => handleOutlineReview("no_notes_needed")}
                          disabled={outlineSubmitting}
                        >
                          {outlineSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                          Approve Outline
                        </Button>
                        <Button 
                          variant="outline" 
                          onClick={() => handleOutlineReview("yes")}
                          disabled={outlineSubmitting || !outlineNotes}
                        >
                          Request Changes
                        </Button>
                        {outline.status_outline_notes === "yes" && (
                          <Button 
                            variant="ghost"
                            className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                            onClick={handleOutlineRegenerate}
                            disabled={outlineSubmitting}
                          >
                            <RefreshCw className={cn("w-4 h-4 mr-2", outlineSubmitting && "animate-spin")} />
                            Regenerate
                          </Button>
                        )}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2 text-slate-300" />
                  Generating initial outline...
                </div>
              )}
            </CardContent>
          </Card>

          {/* Section B: Chapters Section */}
          <Card className={cn("border-slate-200 shadow-sm overflow-hidden transition-opacity", !outlineApproved && "opacity-50 pointer-events-none")}>
            <CardHeader className={cn(
              "border-b border-slate-100 transition-colors",
              outlineApproved && !allChaptersApproved ? "bg-indigo-50/50" : "bg-white"
            )}>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <PenTool className="w-5 h-5 text-indigo-600" />
                  Chapters
                </CardTitle>
                <Badge variant="secondary" className="font-mono">{chapters.length} generated</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-4 bg-slate-50/50">
              {chapters.length === 0 && outlineApproved && (
                <div className="text-center py-6 text-slate-500 italic">No chapters generated yet. Ready to start.</div>
              )}

              <div className="space-y-4">
                {chapters.map((chapter) => {
                  const isApproved = chapter.chapter_notes_status === "no_notes_needed";
                  const needsRevision = chapter.chapter_notes_status === "yes";
                  const isSubmitting = chapterSubmitting[chapter.chapter_number];
                  const isExpanded = expandedChapters[chapter.chapter_number] || false;

                  return (
                    <div key={chapter.id} className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden transition-all hover:border-slate-300">
                      <div 
                        className="px-5 py-4 flex items-center justify-between cursor-pointer hover:bg-slate-50 transition-colors"
                        onClick={() => toggleChapter(chapter.chapter_number)}
                      >
                        <div className="flex items-center gap-3">
                          <h4 className="font-semibold text-slate-900">
                            Ch {chapter.chapter_number}: {chapter.chapter_title}
                          </h4>
                          <StatusBadge status={chapter.chapter_notes_status} />
                        </div>
                        <div className="text-slate-400">
                          {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                        </div>
                      </div>
                      
                      {isExpanded && (
                        <div className="p-5 border-t border-slate-100 bg-white">
                          <div className="max-h-80 overflow-y-auto bg-slate-50 p-4 rounded-md border border-slate-100 text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                            {chapter.content || <span className="italic text-slate-400">Content preview not available</span>}
                          </div>

                          {!isApproved && (
                            <div className="space-y-4 pt-6">
                              <div className="space-y-2">
                                <Label className="text-slate-700">Chapter Editor Notes</Label>
                                <Textarea 
                                  placeholder="Revisions for this chapter..."
                                  value={chapterNotes[chapter.chapter_number] || ""}
                                  onChange={(e) => setChapterNotes(prev => ({...prev, [chapter.chapter_number]: e.target.value}))}
                                  disabled={isSubmitting}
                                  className="bg-white"
                                />
                              </div>
                              <div className="flex flex-wrap gap-3 items-center">
                                <Button 
                                  size="sm"
                                  className="bg-green-600 hover:bg-green-700 text-white"
                                  onClick={() => handleChapterReview(chapter.chapter_number, "no_notes_needed")}
                                  disabled={isSubmitting}
                                >
                                  {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                                  Approve
                                </Button>
                                <Button 
                                  size="sm"
                                  variant="outline" 
                                  onClick={() => handleChapterReview(chapter.chapter_number, "yes")}
                                  disabled={isSubmitting || !chapterNotes[chapter.chapter_number]}
                                >
                                  Request Changes
                                </Button>
                                {needsRevision && (
                                  <Button 
                                    size="sm"
                                    variant="ghost"
                                    className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                                    onClick={() => handleChapterRegenerate(chapter.chapter_number)}
                                    disabled={isSubmitting}
                                  >
                                    <RefreshCw className={cn("w-4 h-4 mr-2", isSubmitting && "animate-spin")} />
                                    Regenerate
                                  </Button>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {outlineApproved && (
                <div className="pt-4 flex justify-center">
                  <Button 
                    className="shadow-sm bg-indigo-600 hover:bg-indigo-700" 
                    onClick={handleGenerateNextChapter}
                    disabled={chapterSubmitting[nextChapterNum]}
                  >
                    {chapterSubmitting[nextChapterNum] ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <PenTool className="w-4 h-4 mr-2" />}
                    Generate Chapter {nextChapterNum}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Section C: Final Compilation */}
          <Card className={cn("border-slate-200 shadow-sm overflow-hidden transition-opacity", !allChaptersApproved && "opacity-50 pointer-events-none")}>
            <CardHeader className={cn(
              "border-b border-slate-100 transition-colors",
              allChaptersApproved && book.status !== "completed" ? "bg-green-50/50" : "bg-white"
            )}>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  Final Draft
                </CardTitle>
                {book.status === "completed" && <StatusBadge status="compiled" />}
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              {book.status !== "completed" ? (
                <>
                  <div className="space-y-2">
                    <Label className="text-slate-700">Final Global Review Notes (Optional)</Label>
                    <Textarea 
                      placeholder="Any final adjustments before compiling..."
                      value={finalNotes}
                      onChange={(e) => setFinalNotes(e.target.value)}
                      disabled={finalSubmitting}
                      className="bg-white"
                    />
                  </div>
                  <Button 
                    onClick={handleFinalCompile}
                    disabled={finalSubmitting || chapters.length === 0}
                    className="w-full sm:w-auto"
                  >
                    {finalSubmitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                    Compile Final Draft
                  </Button>
                </>
              ) : (
                <div className="flex flex-col sm:flex-row items-center gap-4 bg-green-50/50 p-6 rounded-xl border border-green-200/50 shadow-sm">
                  <div className="flex-1 w-full text-center sm:text-left">
                    <h4 className="font-bold text-green-900 mb-1">Compilation Successful</h4>
                    <p className="text-sm text-green-800 font-medium">
                      Final draft is ready.
                    </p>
                    <p className="text-xs text-green-700/80 break-all font-mono mt-2 bg-green-100/50 inline-block px-2 py-1 rounded">
                      {finalDraft?.output_file_path ? finalDraft.output_file_path.split(/[/\\]/).pop() : "compiled.txt"}
                    </p>
                  </div>
                  <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto mt-4 sm:mt-0">
                    <a 
                      href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/books/${book.id}/download`} 
                      download
                      className="inline-flex w-full sm:w-auto"
                    >
                      <Button variant="outline" className="w-full bg-white hover:bg-green-50 border-green-200 text-green-700 hover:text-green-800 whitespace-nowrap shadow-sm">
                        <Download className="w-4 h-4 mr-2" />
                        Download TXT
                      </Button>
                    </a>
                    <a 
                      href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/books/${book.id}/download/pdf`} 
                      download
                      className="inline-flex w-full sm:w-auto"
                    >
                      <Button className="w-full bg-rose-600 hover:bg-rose-700 text-white whitespace-nowrap shadow-sm border-0">
                        <Download className="w-4 h-4 mr-2" />
                        Download PDF
                      </Button>
                    </a>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
      {/* Toast Notification */}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
