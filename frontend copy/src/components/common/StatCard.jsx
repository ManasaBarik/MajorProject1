import React from "react";

export default function StatCard({ label, value, hint, icon: Icon, tone = "slate" }) {
  const tones = { slate: "text-slate-500", cyan: "text-cyan-700", emerald: "text-emerald-600", amber: "text-amber-600", rose: "text-rose-600" };
  return <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex items-center justify-between">
      <p className="text-sm text-slate-500">{label}</p>
      {Icon && <Icon className={`h-5 w-5 ${tones[tone]}`} />}
    </div>
    <p className="mt-3 text-2xl font-semibold text-slate-900">{value}</p>
    {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
  </div>;
}