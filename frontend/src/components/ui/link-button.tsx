import Link from "next/link";
import { buttonClasses, type ButtonProps } from "./button";

/** A Next.js <Link> styled as a button (avoids nesting <button> inside <a>). */
export function LinkButton({
  href,
  variant,
  size,
  className,
  children,
}: {
  href: string;
  variant?: ButtonProps["variant"];
  size?: ButtonProps["size"];
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <Link href={href} className={buttonClasses({ variant, size, className })}>
      {children}
    </Link>
  );
}
