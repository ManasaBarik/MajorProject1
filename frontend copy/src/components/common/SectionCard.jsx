import React from "react";

export default function SectionCard({ title, description, actions, children, className = "" }) {
  return <section className={`rounded-2xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}>
    {(title || actions) && <div className="mb-4 flex items-start justify-between gap-4">
      <div>{title && <h2 className="font-semibold text-slate-900">{title}</h2>}{description && <p className="mt-1 text-sm text-slate-500">{description}</p>}</div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>}
    {children}
  </section>;
}