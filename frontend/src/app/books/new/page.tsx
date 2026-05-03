"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { generateOutline } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

import { Loader2, Sparkles, AlertCircle } from "lucide-react";

import { BookOpen } from "lucide-react";

export default function CreateBook() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !notes) {
      setError("Please provide both a title and notes.");
      return;
    }
    
    setLoading(true);
    setError("");
    try {
      const result = await generateOutline(title, notes);
      if (result.book_id) {
        router.push(`/books/${result.book_id}`);
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }, message?: string };
      setError(error.response?.data?.detail || error.message || "Failed to generate outline.");
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="mb-10 text-center max-w-2xl mx-auto pt-4">
        <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-inner border border-blue-200/50">
          <BookOpen className="w-8 h-8 text-blue-600" />
        </div>
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-slate-900 mb-4">Create a New AI Book</h1>
        <p className="text-slate-500 text-lg">Provide direction once, then control outline, chapter, and final draft generation through review gates.</p>
      </div>

      <div className="grid lg:grid-cols-[1fr_300px] gap-8 max-w-5xl mx-auto items-start">
        <Card className="border-slate-200 shadow-xl rounded-3xl bg-white/95 backdrop-blur overflow-hidden">
          <div className="h-2 w-full bg-gradient-to-r from-blue-600 to-indigo-600" />
          <CardHeader className="pb-4 border-b border-slate-100 px-8 pt-8">
            <CardTitle className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-500" />
              Book Configuration
            </CardTitle>
            <CardDescription className="text-base mt-1">
              Define the core concept and AI will generate a structured outline.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-6 pt-8 px-8">
              {error && (
                <div className="flex items-start gap-3 p-4 bg-red-50 text-red-700 rounded-xl text-sm border border-red-200">
                  <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                  <div className="font-medium">{error}</div>
                </div>
              )}
              
              <div className="space-y-2.5">
                <Label htmlFor="title" className="text-slate-700 font-semibold text-sm">Book Title</Label>
                <Input
                  id="title"
                  placeholder="e.g. The Art of Agentic AI"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={loading}
                  className="max-w-md rounded-xl bg-slate-50 border-slate-200 h-11 focus-visible:ring-blue-500"
                />
              </div>
              
              <div className="space-y-2.5">
                <Label htmlFor="notes" className="text-slate-700 font-semibold text-sm">Direction & Notes for Outline</Label>
                <Textarea
                  id="notes"
                  placeholder="Describe the target audience, tone, key themes, and overall structure you want..."
                  rows={6}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  disabled={loading}
                  className="resize-y rounded-xl bg-slate-50 border-slate-200 p-4 focus-visible:ring-blue-500"
                />
              </div>
            </CardContent>
            <CardFooter className="bg-slate-50/50 p-8 border-t border-slate-100 flex justify-end">
              <Button 
                type="submit" 
                disabled={loading} 
                className="w-full sm:w-auto bg-gradient-to-r from-blue-600 to-indigo-600 hover:opacity-90 text-white shadow-md hover:shadow-lg transition-all rounded-xl h-12 px-8 font-semibold text-base border-0"
              >
                {loading ? (
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                ) : (
                  <Sparkles className="mr-2 h-5 w-5" />
                )}
                {loading ? "Generating Outline..." : "Create Book & Generate Outline"}
              </Button>
            </CardFooter>
          </form>
        </Card>

        <Card className="border-slate-200 shadow-sm rounded-2xl bg-gradient-to-br from-indigo-50 to-blue-50/50 sticky top-8">
          <CardContent className="p-6">
            <h3 className="font-bold text-indigo-900 mb-3 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-indigo-600" />
              Pro Tips
            </h3>
            <p className="text-sm text-indigo-800/80 leading-relaxed">
              Better prompts lead to better books. When writing your direction, be sure to include:
            </p>
            <ul className="mt-4 space-y-3">
              <li className="flex items-start gap-2 text-sm text-indigo-900 font-medium">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 shrink-0" />
                Target audience
              </li>
              <li className="flex items-start gap-2 text-sm text-indigo-900 font-medium">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 shrink-0" />
                Desired tone (e.g. professional, conversational)
              </li>
              <li className="flex items-start gap-2 text-sm text-indigo-900 font-medium">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 shrink-0" />
                Key themes or chapters you absolutely need
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
