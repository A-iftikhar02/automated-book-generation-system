import * as React from "react";
import { LoaderCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link" | "accent";
  size?: "default" | "sm" | "lg" | "icon";
  /** Shows a spinner and disables the button. */
  loading?: boolean;
  ref?: React.Ref<HTMLButtonElement>;
}

const variants = {
  default: "bg-blue-600 text-white hover:bg-blue-700 shadow-md shadow-blue-500/20",
  accent: "bg-indigo-600 text-white hover:bg-indigo-700 shadow-md shadow-indigo-500/20",
  destructive: "bg-red-600 text-white hover:bg-red-700 shadow-md shadow-red-500/20",
  outline: "border border-slate-200 bg-white hover:bg-slate-50 text-slate-900",
  secondary: "bg-slate-100 text-slate-900 hover:bg-slate-200",
  ghost: "text-slate-700 hover:bg-slate-100 hover:text-slate-900",
  link: "text-blue-600 underline-offset-4 hover:underline",
};
const sizes = {
  default: "h-10 px-4 py-2",
  sm: "h-8 rounded-md px-3 text-xs",
  lg: "h-11 rounded-md px-6",
  icon: "h-9 w-9",
};

export function buttonClasses({
  variant = "default",
  size = "default",
  className,
}: { variant?: ButtonProps["variant"]; size?: ButtonProps["size"]; className?: string } = {}) {
  return cn(
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:shrink-0",
    variants[variant],
    sizes[size],
    className,
  );
}

function Button({
  className,
  variant = "default",
  size = "default",
  loading = false,
  disabled,
  children,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClasses({ variant, size, className })}
      {...props}
    >
      {loading && <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
}

export { Button };
