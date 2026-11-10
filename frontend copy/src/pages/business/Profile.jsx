import React, { useEffect, useState } from "react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import Loading from "@/components/common/Loading";
import * as businessesApi from "@/services/api/businesses";

export default function BusinessProfile() {
  const [business, setBusiness] = useState(null);
  const [form, setForm] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => { businessesApi.listBusinesses().then(b => { setBusiness(b[0]); setForm(b[0] || {}); }).finally(() => setLoading(false)); }, []);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const submit = async (e) => { e.preventDefault(); setSaving(true); setSaved(false); try { await businessesApi.updateBusiness(form.id, form); setSaved(true); } finally { setSaving(false); } };

  if (loading) return <div className="px-5 py-8 sm:px-8"><Loading /></div>;

  return <div className="mx-auto max-w-3xl px-5 py-8 sm:px-8">
    <PageHeader eyebrow="Business" title="Business profile" description="View and maintain registered business information." />
    <SectionCard title="Business details">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Business name" value={form.name} onChange={v => set("name", v)} />
          <Field label="Owner name" value={form.owner_name} onChange={v => set("owner_name", v)} />
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Type</label><input value={form.type || ""} onChange={e => set("type", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>
          <Field label="GSTIN" value={form.gstin} onChange={v => set("gstin", v)} />
          <Field label="License number" value={form.license_number} onChange={v => set("license_number", v)} />
          <Field label="Address" value={form.address} onChange={v => set("address", v)} />
        </div>
        {saved && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">Business profile updated.</p>}
        <button type="submit" disabled={saving} className="rounded-xl bg-cyan-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{saving ? "Saving…" : "Save changes"}</button>
      </form>
    </SectionCard>
  </div>;
}

function Field({ label, value, onChange }) {
  return <div><label className="mb-1.5 block text-sm font-medium text-slate-700">{label}</label><input value={value || ""} onChange={e => onChange(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>;
}