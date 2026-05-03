import React from "react";
import { cn } from "@/lib/utils";

interface HeaderProps {
  title: React.ReactNode;
  rightContent?: React.ReactNode;
}

export function Header({ title, rightContent }: HeaderProps) {
  return (
    <header className="h-16 flex items-center justify-between px-8 bg-white border-b border-slate-200 shrink-0">
      <h1 className="text-xl font-bold tracking-tight text-slate-900">{title}</h1>
      <div className="flex items-center gap-4">
        {rightContent}
      </div>
    </header>
  );
}
