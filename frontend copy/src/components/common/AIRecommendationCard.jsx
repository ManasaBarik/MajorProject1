// AIRecommendationCard placeholder
import React from "react";
import { Sparkles, ShieldAlert, Info, Copy, CheckCircle2 } from "lucide-react";
import { statusLabel } from "@/utils/civic";

// AI information is advisory only. Officers review and override before any
// official decision is recorded. This card must never imply a final decision.
export default function AIRecommendationCard({ ai, onOverride, canOverride, onAccept, accepting }) {
  if (!ai) return <p className="text-sm text-slate-500">AI analysis is not available for this complaint yet.</p>;
  const similar = Array.isArray(ai.similar_complaints) ? ai.similar_complaints : [];
  return <div className="rounded-2xl border border-indigo-200 bg-indigo-50/60 p-5">
    <div className="flex items-center gap-2">
      <Sparkles className="h-5 w-5 text-indigo-600" />
      <h3 className="font-semibold text-indigo-900">AI Recommendation</h3>
      {ai.requires_manual_review && (
        <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800">Needs manual review</span>
      )}
      <span className="ml-auto rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">{Math.round((ai.confidence || 0) * 100)}% confidence</span>
    </div>
    <div className="mt-1 flex items-start gap-1.5 text-xs text-indigo-700">
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <p>Advisory only. An officer reviews this before any official action.</p>
    </div>
    <dl className="mt-4 grid gap-3 sm:grid-cols-3">
      <div><dt className="text-xs font-medium text-slate-500">Recommended category</dt><dd className="mt-1 font-medium text-slate-900">{ai.category || "—"}</dd></div>
      <div><dt className="text-xs font-medium text-slate-500">Recommended priority</dt><dd className="mt-1 font-medium text-slate-900">{ai.priority || "—"}</dd></div>
      <div><dt className="text-xs font-medium text-slate-500">Recommended department</dt><dd className="mt-1 font-medium text-slate-900">{ai.department || "—"}</dd></div>
    </dl>
    {ai.summary && <p className="mt-4 text-sm leading-6 text-slate-700">{ai.summary}</p>}
    {ai.reason && <p className="mt-2 text-xs leading-5 text-slate-500">Reasoning: {ai.reason}</p>}
    {similar.length > 0 && <div className="mt-4 border-t border-indigo-200 pt-4">
      <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase text-indigo-700"><Copy className="h-3.5 w-3.5" /> Possible duplicates</p>
      <ul className="space-y-1.5">
        {similar.map(item => <li key={item.id} className="flex items-center justify-between gap-2 rounded-lg bg-white/70 px-3 py-2 text-xs text-slate-600">
          <span className="truncate"><span className="font-medium text-slate-800">{item.complaint_number || `#${item.id}`}</span> · {item.title}</span>
          <span className="shrink-0 text-slate-500">{statusLabel(item.status)} · {Math.round((item.similarity || 0) * 100)}%{item.distance_km != null ? ` · ${item.distance_km} km` : ""}</span>
        </li>)}
      </ul>
    </div>}
    {canOverride && onOverride && <div className="mt-4 flex items-center gap-2 border-t border-indigo-200 pt-4">
      <ShieldAlert className="h-4 w-4 text-indigo-600" />
      <button onClick={onOverride} className="rounded-lg border border-indigo-300 bg-white px-3 py-1.5 text-sm font-semibold text-indigo-700 hover:bg-indigo-50">Review / override</button>
    </div>}
    {onAccept && <div className="mt-4 flex items-center gap-2 border-t border-indigo-200 pt-4">
      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
      <button onClick={onAccept} disabled={accepting} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">{accepting ? "Accepting…" : "Accept recommendation"}</button>
    </div>}
  </div>;
}