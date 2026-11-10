import React, { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Clock, IndianRupee, X } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import Modal from "@/components/common/Modal";
import Loading from "@/components/common/Loading";
import * as servicesApi from "@/services/api/services";

const emptyForm = {
  name: "",
  code: "",
  description: "",
  service_type: "MUNICIPAL",
  eligibility: "",
  procedure: "",
  processing_time_days: 7,
  fee: 0,
  department_id: "",
  field_verification_required: false,
  requirements: [],
};

export default function AdminServices() {
  const [services, setServices] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    Promise.all([servicesApi.listServices(), servicesApi.listDepartments()])
      .then(([serviceRows, departmentRows]) => { setServices(serviceRows); setDepartments(departmentRows); })
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const save = async (e) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      const payload = { ...form, department_id: Number(form.department_id) };
      if (modal === "edit") await servicesApi.updateService(form.id, payload);
      else await servicesApi.createService(payload);
      setModal(null);
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const remove = async (s) => { if (confirm(`Delete ${s.name}?`)) { await servicesApi.deleteService(s.id); load(); } };
  const updateRequirement = (index, patch) => setForm(current => ({
    ...current,
    requirements: current.requirements.map((requirement, i) => i === index ? { ...requirement, ...patch } : requirement),
  }));
  const addRequirement = () => setForm(current => ({
    ...current,
    requirements: [...current.requirements, { key: "", label: "", type: "text", required: true }],
  }));
  const removeRequirement = (index) => setForm(current => ({
    ...current,
    requirements: current.requirements.filter((_, i) => i !== index),
  }));

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Administration" title="Service catalog" description="Manage municipal and business services, application requirements, and review steps." action={
      <button onClick={() => { setForm({ ...emptyForm, requirements: [] }); setError(""); setModal("create"); }} className="inline-flex items-center gap-2 rounded-xl bg-cyan-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800"><Plus className="h-4 w-4" /> New service</button>} />
    {loading ? <Loading /> : <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
      {services.map(s => <SectionCard key={s.id} title={s.name} description={s.description} actions={
        <div className="flex gap-1"><button onClick={() => { setForm(s); setModal("edit"); }} className="rounded-lg p-1.5 hover:bg-slate-100"><Pencil className="h-4 w-4 text-slate-500" /></button><button onClick={() => remove(s)} className="rounded-lg p-1.5 hover:bg-rose-50"><Trash2 className="h-4 w-4 text-rose-500" /></button></div>}>
        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500"><span className="rounded bg-cyan-50 px-2 py-0.5 font-semibold text-cyan-800">{s.service_type || "Unclassified"}</span><span className="rounded bg-slate-100 px-2 py-0.5 font-semibold">{s.code}</span><span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {s.processing_time_days}d</span><span className="flex items-center gap-1"><IndianRupee className="h-3.5 w-3.5" /> {s.fee || 0}</span><span>{s.requirements.length} fields</span>{s.field_verification_required && <span className="rounded bg-amber-50 px-2 py-0.5 font-medium text-amber-800">Field visit</span>}</div>
      </SectionCard>)}
    </div>}

    <Modal open={modal === "create" || modal === "edit"} onClose={() => setModal(null)} title={modal === "edit" ? "Edit service" : "New service"} footer={<><button onClick={() => setModal(null)} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button onClick={save} disabled={saving || !form.name || !form.code || !form.department_id} className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{saving ? "Saving…" : "Save"}</button></>}>
      <form onSubmit={save} className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
        {error && <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Service name" required value={form.name} onChange={value => setForm(f => ({ ...f, name: value }))} />
          <Field label="Service code" required value={form.code} onChange={value => setForm(f => ({ ...f, code: value }))} />
          <SelectField label="Service group" value={form.service_type || ""} onChange={value => setForm(f => ({ ...f, service_type: value }))} options={[["MUNICIPAL", "Municipal"], ["BUSINESS", "Business"]]} />
          <div><label className="mb-1 block text-sm font-medium text-slate-700">Department</label><select required value={form.department_id || ""} onChange={e => setForm(f => ({ ...f, department_id: e.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="">Select department</option>{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
          <Field label="Processing days" type="number" min="1" value={form.processing_time_days} onChange={value => setForm(f => ({ ...f, processing_time_days: Number(value) }))} />
          <Field label="Fee" type="number" min="0" step="0.01" value={form.fee} onChange={value => setForm(f => ({ ...f, fee: value }))} />
        </div>
        <TextAreaField label="Description" value={form.description} onChange={value => setForm(f => ({ ...f, description: value }))} />
        <TextAreaField label="Eligibility" value={form.eligibility} onChange={value => setForm(f => ({ ...f, eligibility: value }))} />
        <TextAreaField label="Procedure" value={form.procedure} onChange={value => setForm(f => ({ ...f, procedure: value }))} />
        <label className="flex items-center gap-2 text-sm font-medium text-slate-700"><input type="checkbox" checked={Boolean(form.field_verification_required)} onChange={e => setForm(f => ({ ...f, field_verification_required: e.target.checked }))} className="h-4 w-4 rounded border-slate-300 text-cyan-700" /> Field verification may be required</label>

        <section className="border-t border-slate-200 pt-4">
          <div className="mb-3 flex items-center justify-between gap-3"><div><h3 className="text-sm font-semibold text-slate-900">Application fields and documents</h3><p className="mt-1 text-xs text-slate-500">These appear on the applicant's form.</p></div><button type="button" onClick={addRequirement} className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"><Plus className="h-4 w-4" /> Add field</button></div>
          <div className="space-y-3">
            {form.requirements.map((requirement, index) => <div key={`${index}-${requirement.key}`} className="rounded-md border border-slate-200 p-3">
              <div className="mb-3 flex items-center justify-between"><span className="text-xs font-semibold uppercase text-slate-500">Field {index + 1}</span><button type="button" title="Remove field" aria-label={`Remove field ${index + 1}`} onClick={() => removeRequirement(index)} className="rounded p-1 text-slate-500 hover:bg-rose-50 hover:text-rose-700"><X className="h-4 w-4" /></button></div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Field key" required value={requirement.key} onChange={value => updateRequirement(index, { key: value.trim().toLowerCase().replace(/\s+/g, "_") })} />
                <Field label="Label" required value={requirement.label} onChange={value => updateRequirement(index, { label: value })} />
                <SelectField label="Field type" value={requirement.type} onChange={type => {
                  const patch = { type };
                  if (type !== "select") patch.options = undefined;
                  if (type !== "file") { patch.allowed_file_types = undefined; patch.max_file_size = undefined; }
                  updateRequirement(index, patch);
                }} options={[["text", "Short text"], ["textarea", "Long text"], ["number", "Number"], ["select", "Select list"], ["date", "Date"], ["file", "File upload"]]} />
                {requirement.type === "select" && <Field label="Options (comma-separated)" required value={(requirement.options || []).join(", ")} onChange={value => updateRequirement(index, { options: value.split(",").map(option => option.trim()).filter(Boolean) })} />}
                {requirement.type === "file" && <>
                  <Field label="Allowed extensions (comma-separated)" value={(requirement.allowed_file_types || []).join(", ")} onChange={value => updateRequirement(index, { allowed_file_types: value.split(",").map(ext => ext.trim().replace(/^\./, "").toLowerCase()).filter(Boolean) })} placeholder="pdf, jpg, png" />
                  <Field label="Maximum size (MB)" type="number" min="0.01" step="0.01" value={((requirement.max_file_size || 10485760) / 1048576).toFixed(2)} onChange={value => updateRequirement(index, { max_file_size: Math.max(1, Math.round(Number(value) * 1048576)) })} />
                </>}
              </div>
              <label className="mt-3 flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={requirement.required !== false} onChange={e => updateRequirement(index, { required: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-cyan-700" /> Required</label>
            </div>)}
            {!form.requirements.length && <p className="rounded-md bg-slate-50 px-3 py-4 text-sm text-slate-500">No application fields configured.</p>}
          </div>
        </section>
      </form>
    </Modal>
  </div>;
}

function Field({ label, value, onChange, type = "text", required = false, ...props }) {
  return <div><label className="mb-1 block text-sm font-medium text-slate-700">{label}{required && <span className="text-rose-600"> *</span>}</label><input type={type} required={required} value={value ?? ""} onChange={e => onChange(e.target.value)} {...props} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>;
}

function TextAreaField({ label, value, onChange }) {
  return <div><label className="mb-1 block text-sm font-medium text-slate-700">{label}</label><textarea value={value || ""} onChange={e => onChange(e.target.value)} rows={3} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>;
}

function SelectField({ label, value, onChange, options }) {
  return <div><label className="mb-1 block text-sm font-medium text-slate-700">{label}</label><select value={value} onChange={e => onChange(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">{options.map(([optionValue, optionLabel]) => <option key={optionValue} value={optionValue}>{optionLabel}</option>)}</select></div>;
}