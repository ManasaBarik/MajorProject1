import React from "react";
import { statusLabel, statusColor } from "@/utils/civic";

export default function StatusBadge({ status }) {
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${statusColor(status)}`}>{statusLabel(status)}</span>;
}