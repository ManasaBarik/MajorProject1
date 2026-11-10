import React from "react";
import { statusLabel, formatDateTime } from "@/utils/civic";

export default function Timeline({ events }) {
  if (!events?.length) return <p className="text-sm text-slate-500">No timeline events yet.</p>;
  return <ol className="relative space-y-5 border-l-2 border-slate-100 pl-5">
    {events.map((e, i) => <li key={i} className="relative">
      <span className="absolute -left-[27px] top-1 h-3 w-3 rounded-full border-2 border-cyan-600 bg-white" />
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">{statusLabel(e.status)}</span>
        <span className="text-xs text-slate-400">{formatDateTime(e.timestamp)}</span>
      </div>
      <p className="mt-1 text-sm text-slate-700">{e.remarks}</p>
      <p className="text-xs text-slate-400">by {e.actor}</p>
    </li>)}
  </ol>;
}