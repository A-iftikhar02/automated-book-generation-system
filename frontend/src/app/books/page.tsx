"use client";

import { useEffect, useState, useMemo } from "react";
import { fetchBooks, Book } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { BookCard } from "@/components/BookCard";
import Link from "next/link";
import { Book as BookIcon, Search, Filter } from "lucide-react";

export default function BooksPage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    fetchBooks()
      .then((data) => setBooks(data || []))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const filteredBooks = useMemo(() => {
    return books.filter((book) => {
      // Search matching
      const matchesSearch = book.title.toLowerCase().includes(searchQuery.toLowerCase());
      
      // Status matching
      let matchesStatus = true;
      if (statusFilter === "completed") {
        matchesStatus = book.status === "completed";
      } else if (statusFilter === "in_progress") {
        matchesStatus = book.status !== "completed" && book.status !== "pending";
      } else if (statusFilter === "pending") {
        matchesStatus = book.status === "pending";
      }

      return matchesSearch && matchesStatus;
    }).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [books, searchQuery, statusFilter]);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Book Library</h1>
          <p className="text-slate-500 mt-1 text-lg">Search, filter, and manage every generated book project.</p>
        </div>
        <Link href="/books/new">
          <Button className="shadow-sm bg-blue-600 hover:bg-blue-700 text-white">Create Book</Button>
        </Link>
      </div>

      <div className="bg-white/90 backdrop-blur-sm p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-4 items-center">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input 
            placeholder="Search books by title..." 
            className="pl-10 rounded-xl bg-slate-50/50 border-slate-200 focus-visible:ring-blue-500"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-3 w-full sm:w-72">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <select 
            className="flex h-10 w-full items-center justify-between rounded-xl border border-slate-200 bg-slate-50/50 px-3 py-2 text-sm ring-offset-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50 transition-all font-medium text-slate-700"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="in_progress">In Progress</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      </div>
          
      {loading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-6">
              <Skeleton className="h-6 w-2/3 mb-4" />
              <Skeleton className="h-4 w-1/3 mb-6" />
              <Skeleton className="h-3 w-full mb-6" />
              <Skeleton className="h-10 w-full" />
            </Card>
          ))}
        </div>
      ) : filteredBooks.length === 0 ? (
        <Card className="flex flex-col items-center justify-center py-20 text-center border-dashed border-gray-300 shadow-sm rounded-2xl">
          <BookIcon className="w-12 h-12 text-slate-300 mb-4" />
          <h3 className="text-xl font-semibold text-slate-900 mb-2">
            {books.length === 0 ? "No books yet" : "No books found"}
          </h3>
          <p className="text-slate-500 max-w-sm mb-6">
            {books.length === 0 
              ? "Start your first human-in-the-loop book generation workflow."
              : "Try adjusting your search or filters to find what you're looking for."}
          </p>
          {books.length === 0 && (
            <Link href="/books/new">
              <Button>Create Book</Button>
            </Link>
          )}
        </Card>
      ) : (
        <div className="space-y-4">
          <div className="text-sm font-medium text-slate-500">
            Showing {filteredBooks.length} {filteredBooks.length === 1 ? 'book' : 'books'}
          </div>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {filteredBooks.map((book) => (
              <BookCard key={book.id} book={book} variant="full" />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
