import React from "react";
import { priorityColor } from "@/utils/civic";

export default function PriorityBadge({ priority }) {
  if (!priority) return null;
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${priorityColor(priority)}`}>{priority}</span>;
}