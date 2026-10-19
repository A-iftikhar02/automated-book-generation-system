import { BookOpen } from "lucide-react";
import { apiUrl, paths } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Cover thumbnail served by the API; `version` busts the browser cache when the cover changes. */
export function BookCover({
  bookId,
  hasCover,
  version,
  title,
  className,
}: {
  bookId: string;
  hasCover: boolean;
  version?: string | number | null;
  title: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative aspect-[2/3] shrink-0 overflow-hidden rounded-md border border-slate-200 bg-gradient-to-br from-slate-100 to-slate-200 shadow-sm",
        className,
      )}
    >
      {hasCover ? (
        // Plain <img>: the cover is served dynamically by the API (no Next image optimisation needed).
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={apiUrl(paths.cover(bookId, version))}
          alt={`Cover of ${title}`}
          className="h-full w-full object-cover"
          loading="lazy"
        />
      ) : (
        <div className="flex h-full w-full flex-col items-center justify-center gap-1 p-2 text-center text-slate-400">
          <BookOpen className="h-1/4 w-1/4 min-h-4 min-w-4" aria-hidden />
          <span className="sr-only">No cover yet</span>
        </div>
      )}
    </div>
  );
}
