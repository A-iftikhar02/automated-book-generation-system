import React from "react";
import { Badge } from "@/components/ui/badge";

type StatusType = "pending" | "generated" | "waiting_for_notes" | "approved" | "error" | "compiled" | string;

export function StatusBadge({ status }: { status: StatusType }) {
  const normalize = (s: string) => s.toLowerCase().replace(/_/g, " ");

  let variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" = "secondary";
  
  if (status.includes("pending") || status.includes("phase")) variant = "secondary"; // gray
  if (status.includes("generated")) variant = "info"; // blue
  if (status.includes("waiting") || status.includes("yes") || status.includes("notes") || status.includes("revision")) variant = "warning"; // yellow
  if (status.includes("approved") || status.includes("no_notes_needed") || status.includes("completed")) variant = "success"; // green
  if (status.includes("error") || status.includes("failed")) variant = "destructive"; // red
  if (status.includes("compiled")) variant = "purple" as any; // we'll add purple to badge

  return (
    <Badge variant={variant} className="capitalize whitespace-nowrap">
      {normalize(status)}
    </Badge>
  );
}
