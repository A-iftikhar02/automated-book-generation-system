"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, LayoutDashboard, Library, Menu, CirclePlus, Settings, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSystemStatus } from "@/lib/hooks";

const LINKS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, match: (p: string) => p === "/" },
  {
    href: "/books",
    label: "Library",
    icon: Library,
    match: (p: string) => p === "/books" || (p.startsWith("/books/") && p !== "/books/new"),
  },
  { href: "/books/new", label: "New Book", icon: CirclePlus, match: (p: string) => p === "/books/new" },
  { href: "/settings", label: "Settings", icon: Settings, match: (p: string) => p.startsWith("/settings") },
];

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-3 rounded-lg text-xl font-bold tracking-tight text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
      <span className="flex items-center justify-center rounded-lg bg-blue-600 p-1.5 shadow-sm">
        <BookOpen className="h-5 w-5 text-white" aria-hidden />
      </span>
      <span className="flex items-center">
        BookPilot
        <span className="ml-1.5 rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-blue-700">AI</span>
      </span>
    </Link>
  );
}

function StatusDot() {
  const { data, error } = useSystemStatus(60_000);
  const ok = data && data.database && data.ai.configured;
  const label = error
    ? "API unreachable"
    : !data
      ? "Checking API…"
      : !data.database
        ? "Database down"
        : !data.ai.configured
          ? "No AI provider configured"
          : "All systems ready";
  return (
    <Link
      href="/settings"
      className="flex items-center gap-2 rounded-xl border border-slate-200/70 bg-slate-50 px-3 py-2.5 text-xs font-medium text-slate-600 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <span
        className={cn(
          "h-2 w-2 shrink-0 rounded-full",
          error || (data && !data.database) ? "bg-red-500" : ok ? "bg-green-500" : data ? "bg-amber-500" : "bg-slate-300",
        )}
        aria-hidden
      />
      <span className="truncate">{label}</span>
      {data && <span className="ml-auto text-slate-400">v{data.version}</span>}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // Close the mobile drawer on navigation.
  const [lastPath, setLastPath] = useState(pathname);
  if (lastPath !== pathname) {
    setLastPath(pathname);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const nav = (
    <nav aria-label="Main" className="flex-1 space-y-1.5 px-4 py-6">
      <div className="px-2 pb-2 text-xs font-bold uppercase tracking-wider text-slate-400">Menu</div>
      {LINKS.map((link) => {
        const active = link.match(pathname);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "group flex items-center gap-3 rounded-xl border px-3 py-2.5 text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
              active
                ? "border-blue-100 bg-blue-50 text-blue-700 shadow-sm"
                : "border-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )}
          >
            <link.icon className={cn("h-5 w-5", active ? "text-blue-600" : "text-slate-400 group-hover:text-slate-600")} aria-hidden />
            {link.label}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <>
      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur-md lg:hidden">
        <Logo />
        <button
          onClick={() => setOpen(true)}
          className="rounded-md p-2 text-slate-600 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          aria-label="Open menu"
          aria-expanded={open}
          aria-controls="mobile-nav"
        >
          <Menu className="h-5 w-5" />
        </button>
      </header>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" id="mobile-nav">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setOpen(false)} aria-hidden />
          <aside className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-white shadow-xl">
            <div className="flex h-14 items-center justify-between border-b border-slate-100 px-4">
              <Logo />
              <button
                onClick={() => setOpen(false)}
                className="rounded-md p-2 text-slate-500 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            {nav}
            <div className="p-4">
              <StatusDot />
            </div>
          </aside>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-slate-200 bg-white/80 shadow-sm backdrop-blur-md lg:flex">
        <div className="flex h-16 items-center border-b border-slate-100 px-6">
          <Logo />
        </div>
        {nav}
        <div className="space-y-3 p-4">
          <div className="rounded-2xl border border-slate-200/60 bg-gradient-to-br from-slate-50 to-slate-100/50 p-4 shadow-sm">
            <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-900">Workflow</h4>
            <p className="text-[11px] font-semibold uppercase leading-relaxed tracking-wide text-slate-500">
              Plan <span className="text-slate-300">→</span> Outline <span className="text-slate-300">→</span> Write{" "}
              <span className="text-slate-300">→</span> QA <span className="text-slate-300">→</span> Publish
            </p>
          </div>
          <StatusDot />
        </div>
      </aside>
    </>
  );
}
