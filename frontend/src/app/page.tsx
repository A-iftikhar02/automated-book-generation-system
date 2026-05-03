"use client";

import { useEffect, useState } from "react";
import { fetchBooks, Book } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { BookCard, computeProgress } from "@/components/BookCard";
import Link from "next/link";
import { Book as BookIcon, Library, CheckCircle, Clock, BarChart, Plus, ArrowRight } from "lucide-react";

export default function Dashboard() {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBooks()
      .then((data) => setBooks(data || []))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const totalBooks = books.length;
  const completedBooks = books.filter(b => b.status === "completed").length;
  const inProgressBooks = books.filter(b => b.status !== "completed" && b.status !== "pending").length;
  const avgProgress = totalBooks > 0 
    ? Math.round(books.reduce((acc, book) => acc + computeProgress(book.status), 0) / totalBooks)
    : 0;

  const recentBooks = [...books]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 3);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Hero Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-3xl text-white p-8 md:p-10 shadow-lg relative overflow-hidden flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="relative z-10 max-w-2xl">
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-3">AI Book Generation Dashboard</h1>
          <p className="text-blue-100 text-lg font-medium">Track outlines, chapters, approvals, and final drafts from one workflow control panel.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 relative z-10 shrink-0">
          <Link href="/books">
            <Button variant="outline" className="w-full sm:w-auto bg-transparent border-blue-200/40 text-white hover:bg-white/10 hover:text-white backdrop-blur-sm">
              <Library className="w-4 h-4 mr-2" />
              View All Books
            </Button>
          </Link>
          <Link href="/books/new">
            <Button className="w-full sm:w-auto bg-white text-blue-700 hover:bg-slate-50 border-0 shadow-sm">
              <Plus className="w-4 h-4 mr-2" />
              Create Book
            </Button>
          </Link>
        </div>
      </div>
          
      {loading ? (
        <div className="space-y-8">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map(i => (
              <Card key={i}><CardContent className="p-6"><Skeleton className="h-16 w-full" /></CardContent></Card>
            ))}
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {[1, 2, 3].map(i => (
              <Card key={i} className="p-6">
                <Skeleton className="h-6 w-2/3 mb-4" />
                <Skeleton className="h-2 w-full mb-6" />
                <Skeleton className="h-8 w-full" />
              </Card>
            ))}
          </div>
        </div>
      ) : books.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-white rounded-2xl border border-dashed border-gray-300 shadow-sm">
          <BookIcon className="w-12 h-12 text-slate-300 mb-4" />
          <h3 className="text-xl font-semibold text-slate-900 mb-2">No books yet</h3>
          <p className="text-slate-500 max-w-sm mb-6">
            Start your first human-in-the-loop book generation workflow.
          </p>
          <Link href="/books/new">
            <Button>Create Book</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Stats Overview */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card className="rounded-2xl bg-white/90 shadow-sm border border-slate-200 hover:-translate-y-1 hover:shadow-md transition-all duration-300">
              <CardContent className="p-6">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                    <Library className="w-6 h-6 text-blue-600" />
                  </div>
                  <div className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Total Books</div>
                </div>
                <div className="text-4xl font-bold text-slate-900 tracking-tight">{totalBooks}</div>
              </CardContent>
            </Card>
            <Card className="rounded-2xl bg-white/90 shadow-sm border border-slate-200 hover:-translate-y-1 hover:shadow-md transition-all duration-300">
              <CardContent className="p-6">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  </div>
                  <div className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Completed</div>
                </div>
                <div className="text-4xl font-bold text-slate-900 tracking-tight">{completedBooks}</div>
              </CardContent>
            </Card>
            <Card className="rounded-2xl bg-white/90 shadow-sm border border-slate-200 hover:-translate-y-1 hover:shadow-md transition-all duration-300">
              <CardContent className="p-6">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center shrink-0">
                    <Clock className="w-6 h-6 text-amber-600" />
                  </div>
                  <div className="text-sm font-semibold text-slate-500 uppercase tracking-wider">In Progress</div>
                </div>
                <div className="text-4xl font-bold text-slate-900 tracking-tight">{inProgressBooks}</div>
              </CardContent>
            </Card>
            <Card className="rounded-2xl bg-white/90 shadow-sm border border-slate-200 hover:-translate-y-1 hover:shadow-md transition-all duration-300">
              <CardContent className="p-6">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center shrink-0">
                    <BarChart className="w-6 h-6 text-indigo-600" />
                  </div>
                  <div className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Avg Progress</div>
                </div>
                <div className="text-4xl font-bold text-slate-900 tracking-tight">{avgProgress}%</div>
              </CardContent>
            </Card>
          </div>

          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-900">Recent Books</h2>
            <Link href="/books" className="text-sm font-medium text-blue-600 hover:text-blue-700 flex items-center">
              View all <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {recentBooks.map((book) => (
              <BookCard key={book.id} book={book} variant="compact" />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
