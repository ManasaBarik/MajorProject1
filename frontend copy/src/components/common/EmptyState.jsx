import React from "react";
import { Inbox } from "lucide-react";

export default function EmptyState({ title = "No records to show", message = "This area is ready for backend data." }) {
  return <div className="flex min-h-52 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-6 py-10 text-center">
    <span className="rounded-2xl bg-white p-3 shadow-sm"><Inbox className="h-6 w-6 text-slate-400" /></span>
    <p className="mt-4 font-medium text-slate-700">{title}</p>
    <p className="mt-1 text-sm text-slate-500">{message}</p>
  </div>;
}