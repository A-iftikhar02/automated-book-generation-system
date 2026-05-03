import Link from "next/link";
import { Book } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Calendar, ArrowRight } from "lucide-react";

export function computeProgress(status: string) {
  if (status === "completed") return 100;
  if (status.includes("outline")) return 25;
  if (status.includes("chapter")) {
    const match = status.match(/chapter_(\d+)/);
    if (match) {
      return Math.min(25 + parseInt(match[1]) * 10, 90);
    }
    return 50;
  }
  return 10;
}

export function BookCard({ book, variant = "full" }: { book: Book, variant?: "compact" | "full" }) {
  const progress = computeProgress(book.status);
  const isCompact = variant === "compact";
  
  return (
    <Card className={`bg-white/90 backdrop-blur-sm rounded-3xl border border-slate-200 shadow-sm hover:shadow-xl transition-all duration-300 group flex flex-col hover:-translate-y-1.5 ${isCompact ? 'p-0' : ''}`}>
      <CardContent className={`${isCompact ? 'p-5' : 'p-7'} flex-1 flex flex-col`}>
        <div className="flex justify-between items-start mb-4">
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Book Project</span>
            <StatusBadge status={book.status} />
          </div>
          <span className="flex items-center text-xs font-medium text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">
            <Calendar className="w-3.5 h-3.5 mr-1.5 text-slate-400" />
            {new Date(book.created_at).toLocaleDateString()}
          </span>
        </div>
        
        <h3 className={`${isCompact ? 'text-lg' : 'text-xl'} font-bold text-slate-900 tracking-tight leading-snug line-clamp-2 mb-5 flex-1`} title={book.title}>
          {book.title}
        </h3>
        
        <div className="space-y-2 mb-6 bg-slate-50 p-3 rounded-2xl border border-slate-100">
          <div className="flex justify-between text-xs">
            <span className="text-slate-500 font-semibold">Generation Progress</span>
            <span className="text-indigo-700 font-bold">{progress}%</span>
          </div>
          <div className={`${isCompact ? 'h-2' : 'h-2.5'} w-full bg-slate-200 rounded-full overflow-hidden shadow-inner`}>
            <div 
              className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 transition-all duration-1000 ease-out rounded-full relative"
              style={{ width: `${progress}%` }}
            >
              <div className="absolute inset-0 bg-white/20 w-full h-full animate-[shimmer_2s_infinite]" />
            </div>
          </div>
        </div>
        
        <Link href={`/books/${book.id}`} className="mt-auto block">
          <Button 
            size={isCompact ? "sm" : "default"} 
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-md hover:shadow-lg transition-all duration-300 rounded-xl font-semibold border-0"
          >
            Open Workspace
            <ArrowRight className="w-4 h-4 ml-2 opacity-70 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
