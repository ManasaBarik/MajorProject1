import React, { useState } from "react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import { useCivicAuth } from "@/contexts/CivicAuthContext";
import { roleLabel } from "@/utils/civic";

export default function OfficerProfile() {
  const { user, updateMe } = useCivicAuth();
  const [form, setForm] = useState({ name: user?.name || "", email: user?.email || "", phone: "", department: "" });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const submit = async (e) => { e.preventDefault(); setSaving(true); setSaved(false); try { await updateMe(form); setSaved(true); } finally { setSaving(false); } };

  return <div className="mx-auto max-w-3xl px-5 py-8 sm:px-8">
    <PageHeader eyebrow="Account" title="Officer profile" description="Review your municipal staff account information." />
    <SectionCard title="Account details">
      <div className="mb-5 flex items-center gap-3"><div className="flex h-14 w-14 items-center justify-center rounded-full bg-cyan-100 text-lg font-bold text-cyan-700">{(user?.name || "U").charAt(0).toUpperCase()}</div><div><p className="font-semibold text-slate-900">{user?.name}</p><p className="text-sm text-slate-500">{roleLabel(user?.role)}</p></div></div>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Full name</label><input value={form.name} onChange={e => set("name", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Email</label><input type="email" value={form.email} onChange={e => set("email", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Phone</label><input value={form.phone} onChange={e => set("phone", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Department</label><input value={form.department} onChange={e => set("department", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>
        </div>
        {saved && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">Profile updated.</p>}
        <button type="submit" disabled={saving} className="rounded-xl bg-cyan-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{saving ? "Saving…" : "Save changes"}</button>
      </form>
    </SectionCard>
  </div>;
}