"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, LayoutDashboard, PlusCircle, Library, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();

  const links = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
    { href: "/books", label: "All Books", icon: Library, exact: true },
    { href: "/books/new", label: "Create Book", icon: PlusCircle, exact: false },
  ];

  return (
    <aside className="w-64 border-r border-slate-200 bg-white/80 backdrop-blur-md min-h-screen flex flex-col shadow-sm z-20 shrink-0">
      <div className="h-16 flex items-center px-6 border-b border-slate-100">
        <div className="flex items-center gap-3 font-bold text-xl text-slate-900 tracking-tight">
          <div className="bg-blue-600 rounded-lg p-1.5 flex items-center justify-center shadow-sm">
            <BookOpen className="w-5 h-5 text-white" />
          </div>
          <span className="flex items-center">BookPilot <span className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded text-[10px] uppercase font-bold tracking-widest ml-1.5">AI</span></span>
        </div>
      </div>
      <div className="flex-1 py-8 px-4 space-y-2">
        <div className="px-2 pb-3 text-xs font-bold text-slate-400 uppercase tracking-wider">
          Menu
        </div>
        {links.map((link) => {
          const isActive = link.exact 
            ? pathname === link.href 
            : pathname.startsWith(link.href);

          return (
            <Link 
              key={link.href} 
              href={link.href} 
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 group",
                isActive 
                  ? "bg-blue-50 text-blue-700 border border-blue-100 shadow-sm" 
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 border border-transparent"
              )}
            >
              <link.icon className={cn("w-5 h-5 transition-colors", isActive ? "text-blue-600" : "text-slate-400 group-hover:text-slate-600")} />
              {link.label}
            </Link>
          );
        })}
      </div>
      
      <div className="p-4 mt-auto">
        <div className="bg-gradient-to-br from-slate-50 to-slate-100/50 rounded-2xl p-4 border border-slate-200/60 shadow-sm">
          <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            Workflow System
          </h4>
          <div className="flex items-center justify-between text-[10px] font-bold text-slate-500 uppercase tracking-wide">
            <span>Outline</span>
            <span className="text-slate-300">→</span>
            <span>Chapters</span>
            <span className="text-slate-300">→</span>
            <span>Final</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
