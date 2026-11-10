import React from "react";

export default function Loading({ label = "Loading…" }) {
  return <div className="flex min-h-52 items-center justify-center">
    <div className="flex items-center gap-3 text-slate-500"><span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-cyan-700" />{label}</div>
  </div>;
}
