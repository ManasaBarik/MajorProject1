import React, { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Users } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import Modal from "@/components/common/Modal";
import Loading from "@/components/common/Loading";
import * as servicesApi from "@/services/api/services";

export default function AdminDepartments() {
  const [departments, setDepartments] = useState([]);
  const [staff, setStaff] = useState({});
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({ name: "", code: "", description: "" });
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    servicesApi.listDepartments().then(async (d) => {
      setDepartments(d);
      const map = {};
      await Promise.all(d.map(async (dep) => { map[dep.id] = await servicesApi.getDepartmentStaff(dep.id); }));
      setStaff(map);
    }).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const save = async (e) => {
    e.preventDefault(); setSaving(true);
    try { if (modal === "edit") await servicesApi.updateDepartment(form.id, form); else await servicesApi.createDepartment(form); setModal(null); load(); } finally { setSaving(false); }
  };
  const remove = async (d) => { if (confirm(`Delete ${d.name}?`)) { await servicesApi.deleteDepartment(d.id); load(); } };

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Administration" title="Departments" description="Manage municipal departments and review their staff." action={
      <button onClick={() => { setForm({ name: "", code: "", description: "" }); setModal("create"); }} className="inline-flex items-center gap-2 rounded-xl bg-cyan-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800"><Plus className="h-4 w-4" /> New department</button>} />
    {loading ? <Loading /> : <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
      {departments.map(d => <SectionCard key={d.id} title={d.name} description={d.description} actions={
        <div className="flex gap-1"><button onClick={() => { setForm(d); setModal("edit"); }} className="rounded-lg p-1.5 hover:bg-slate-100"><Pencil className="h-4 w-4 text-slate-500" /></button><button onClick={() => remove(d)} className="rounded-lg p-1.5 hover:bg-rose-50"><Trash2 className="h-4 w-4 text-rose-500" /></button></div>}>
        <div className="flex items-center gap-2 text-sm text-slate-500"><span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-semibold">{d.code}</span><span className="flex items-center gap-1"><Users className="h-3.5 w-3.5" /> {(staff[d.id] || []).length} staff</span></div>
        {(staff[d.id] || []).length > 0 && <ul className="mt-3 space-y-1.5">{(staff[d.id] || []).map(s => <li key={s.id} className="text-sm text-slate-700">{s.name} <span className="text-xs text-slate-400">· {s.role.toLowerCase()}</span></li>)}</ul>}
      </SectionCard>)}
    </div>}

    <Modal open={modal === "create" || modal === "edit"} onClose={() => setModal(null)} title={modal === "edit" ? "Edit department" : "New department"} footer={<><button onClick={() => setModal(null)} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button onClick={save} disabled={saving} className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{saving ? "Saving…" : "Save"}</button></>}>
      <form onSubmit={save} className="space-y-3">
        <div><label className="mb-1 block text-sm font-medium text-slate-700">Name</label><input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
        <div><label className="mb-1 block text-sm font-medium text-slate-700">Code</label><input value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
        <div><label className="mb-1 block text-sm font-medium text-slate-700">Description</label><textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={3} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
      </form>
    </Modal>
  </div>;
}