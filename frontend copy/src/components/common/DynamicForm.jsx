import React, { useState } from "react";

// Renders a service's requirements dynamically from the API. The frontend never
// hardcodes service requirements — fields come from the service definition.
export default function DynamicForm({ fields = [], onSubmit, submitLabel = "Submit", loading, beforeFields, initialValues = {}, formError = "" }) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});

  const set = (key, value) => setValues(v => ({ ...v, [key]: value }));
  const validate = () => {
    const errs = {};
    fields.forEach(field => {
      const value = values[field.key];
      const missing = value === undefined || value === null || value === "";
      if (field.required && missing) errs[field.key] = `${field.label} is required`;
      if (field.type === "file" && value instanceof File) {
        const extension = value.name.split(".").pop()?.toLowerCase();
        const allowedTypes = field.allowed_file_types || [];
        if (allowedTypes.length && !allowedTypes.includes(extension)) {
          errs[field.key] = `Choose a ${allowedTypes.join(", ")} file`;
        } else if (field.max_file_size && value.size > field.max_file_size) {
          errs[field.key] = `File must be smaller than ${(field.max_file_size / 1048576).toFixed(2)} MB`;
        }
      }
    });
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const submit = (e) => { e.preventDefault(); if (validate()) onSubmit(values); };

  return <form onSubmit={submit} className="space-y-5">
    {beforeFields}
    {formError && <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{formError}</p>}
    {fields.map(f => <div key={f.key}>
      <label className="mb-1.5 block text-sm font-medium text-slate-700">{f.label}{f.required && <span className="text-rose-500"> *</span>}</label>
      {f.type === "textarea" && <textarea required={f.required} value={values[f.key] || ""} onChange={e => set(f.key, e.target.value)} rows={3} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none" />}
      {f.type === "select" && <select value={values[f.key] || ""} onChange={e => set(f.key, e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none">
        <option value="">Select…</option>{(f.options || []).map(o => <option key={o} value={o}>{o}</option>)}
      </select>}
      {f.type === "date" && <input type="date" required={f.required} value={values[f.key] || ""} onChange={e => set(f.key, e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none" />}
      {f.type === "file" && <input type="file" required={f.required} accept={(f.allowed_file_types || []).map(ext => `.${ext}`).join(",")} onChange={e => set(f.key, e.target.files[0] || null)} className="w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2" />}
      {(f.type === "text" || f.type === "number") && <input type={f.type} required={f.required} min={f.min} max={f.max} value={values[f.key] ?? ""} onChange={e => set(f.key, e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none" />}
      {errors[f.key] && <p className="mt-1 text-xs text-rose-500">{errors[f.key]}</p>}
    </div>)}
    <button type="submit" disabled={loading} className="rounded-xl bg-cyan-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{loading ? "Submitting…" : submitLabel}</button>
  </form>;
}