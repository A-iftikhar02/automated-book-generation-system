"use client";

import { Suspense } from "react";
import { useParams } from "next/navigation";
import { BookWorkspace, WorkspaceSkeleton } from "@/components/book/BookWorkspace";

export default function BookPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <Suspense fallback={<WorkspaceSkeleton />}>
      <BookWorkspace key={id} id={id} />
    </Suspense>
  );
}
