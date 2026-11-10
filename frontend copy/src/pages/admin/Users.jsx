import React, { useEffect, useState } from "react";
import { Plus, UserCog, ListChecks } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import StatusBadge from "@/components/common/StatusBadge";
import Loading from "@/components/common/Loading";
import Modal from "@/components/common/Modal";
import { roleLabel } from "@/utils/civic";
import * as usersApi from "@/services/api/users";
import * as servicesApi from "@/services/api/services";

export default function AdminUsers() {
  const [rows, setRows] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [serviceCatalog, setServiceCatalog] = useState([]);
  const [officers, setOfficers] = useState([]);
  const [engineers, setEngineers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [engineerModal, setEngineerModal] = useState(false);
  const [selectedEngineer, setSelectedEngineer] = useState(null);
  const [selectedServiceIds, setSelectedServiceIds] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "OFFICER",
    department_id: "",
    designation: "",
    specialization: "",
  });

  const load = () => {
    setLoading(true);
    Promise.all([
      usersApi.listUsers(),
      servicesApi.listDepartments(),
      servicesApi.listServices(),
      usersApi.listOfficers(),
      usersApi.listEngineers(),
    ]).then(([users, deps, serviceRows, officerRows, engineerRows]) => {
      setRows(users);
      setDepartments(deps);
      setServiceCatalog(serviceRows);
      setOfficers(officerRows);
      setEngineers(engineerRows);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = {
        ...form,
        department_id: Number(form.department_id),
        service_ids: form.role === "ENGINEER" ? form.service_ids : [],
      };
      if (payload.role === "OFFICER") {
        payload.designation = payload.designation || "Officer";
      }
      if (payload.role === "ENGINEER") {
        payload.specialization = payload.specialization || "General infrastructure";
      }
      await usersApi.createDepartmentStaff(payload);
      setModal(false);
      setForm({
        name: "",
        email: "",
        password: "",
        role: "OFFICER",
        department_id: "",
        designation: "",
        specialization: "",
        service_ids: [],
      });
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const saveEngineerServices = async (e) => {
    e.preventDefault();
    if (!selectedEngineer) return;
    setSaving(true); setError("");
    try {
      await usersApi.updateEngineer(selectedEngineer.id, { service_ids: selectedServiceIds });
      setEngineerModal(false);
      setSelectedEngineer(null);
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const toggleService = (id) => setForm(current => ({
    ...current,
    service_ids: current.service_ids.includes(id)
      ? current.service_ids.filter(serviceId => serviceId !== id)
      : [...current.service_ids, id],
  }));

  const departmentServices = serviceCatalog.filter(service => service.department_id === Number(form.department_id));

  const columns = [
    { key: "id", label: "ID", render: r => <span className="font-medium text-slate-500">#{r.id}</span> },
    { key: "name", label: "Name", render: r => <span className="font-medium text-slate-800">{r.name}</span> },
    { key: "email", label: "Email" },
    { key: "role", label: "Role", render: r => <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">{roleLabel(r.role)}</span> },
    { key: "department", label: "Department", render: r => r.department || "—" },
    { key: "status", label: "Status", render: r => <StatusBadge status={r.status} /> },
    { key: "services", label: "Qualified services", render: r => {
      const profile = engineers.find(engineer => engineer.user_id === r.id);
      return r.role === "ENGINEER" ? <div><span>{profile?.services?.join(", ") || "No service qualifications"}</span><button onClick={() => { setSelectedEngineer(profile); setSelectedServiceIds(profile?.service_ids || []); setError(""); setEngineerModal(true); }} disabled={!profile} className="ml-2 inline-flex items-center gap-1 text-xs font-semibold text-cyan-800 hover:underline disabled:opacity-50"><ListChecks className="h-3.5 w-3.5" /> Edit</button></div> : "—";
    } },
  ];

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Administration" title="Users" description="View platform users and assign new staff to departments." action={
      <button onClick={() => { setError(""); setModal(true); }} className="inline-flex items-center gap-2 rounded-xl bg-cyan-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800"><Plus className="h-4 w-4" /> Add staff</button>
    } />
    {loading ? <Loading /> : <DataTable columns={columns} rows={rows} emptyTitle="No users found" />}

    <Modal open={modal} onClose={() => setModal(false)} title="Assign department staff" footer={<>
      <button onClick={() => setModal(false)} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button>
      <button onClick={save} disabled={saving || !form.name || !form.email || !form.password || !form.department_id} className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{saving ? "Saving…" : "Save"}</button>
    </>}>
      <form onSubmit={save} className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
        {error && !engineerModal && <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
        <div><label className="mb-1 block text-sm font-medium text-slate-700">Name</label><input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
        <div><label className="mb-1 block text-sm font-medium text-slate-700">Email</label><input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
        <div><label className="mb-1 block text-sm font-medium text-slate-700">Password</label><input type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
        <div><label className="mb-1 block text-sm font-medium text-slate-700">Role</label><select value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="OFFICER">Officer</option><option value="ENGINEER">Engineer</option></select></div>
        <div><label className="mb-1 block text-sm font-medium text-slate-700">Department</label><select value={form.department_id} onChange={e => setForm(f => ({ ...f, department_id: e.target.value, service_ids: [] }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="">Select department</option>{departments.map(d => { const occupied = form.role === "OFFICER" && officers.some(o => o.department_id === d.id && o.available); return <option key={d.id} value={d.id} disabled={occupied}>{d.name}{occupied ? " · officer assigned" : ""}</option>; })}</select></div>
        {form.role === "OFFICER" && <div><label className="mb-1 block text-sm font-medium text-slate-700">Designation</label><input value={form.designation} onChange={e => setForm(f => ({ ...f, designation: e.target.value }))} placeholder="Assistant Engineer" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>}
        {form.role === "ENGINEER" && <>
          <div><label className="mb-1 block text-sm font-medium text-slate-700">Specialization</label><input value={form.specialization} onChange={e => setForm(f => ({ ...f, specialization: e.target.value }))} placeholder="Road maintenance" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
          <fieldset><legend className="mb-2 text-sm font-medium text-slate-700">Services this engineer handles</legend><div className="max-h-40 space-y-2 overflow-y-auto rounded-md border border-slate-200 p-3">{departmentServices.map(service => <label key={service.id} className="flex items-start gap-2 text-sm text-slate-700"><input type="checkbox" checked={form.service_ids.includes(service.id)} onChange={() => toggleService(service.id)} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-cyan-700" /><span>{service.name}</span></label>)}{!form.department_id && <p className="text-xs text-slate-500">Select a department first.</p>}{form.department_id && !departmentServices.length && <p className="text-xs text-slate-500">No active services in this department.</p>}</div></fieldset>
        </>}
      </form>
    </Modal>

    <Modal open={engineerModal} onClose={() => setEngineerModal(false)} title={`Service qualifications: ${selectedEngineer?.name || "Engineer"}`} footer={<><button onClick={() => setEngineerModal(false)} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button onClick={saveEngineerServices} disabled={saving || !selectedEngineer || !selectedServiceIds.length} className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{saving ? "Saving…" : "Save qualifications"}</button></>}>
      <form onSubmit={saveEngineerServices} className="space-y-3">
        {error && engineerModal && <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
        <p className="text-sm text-slate-600">Choose the services this engineer is qualified to handle in {selectedEngineer?.department_name || "their department"}.</p>
        <div className="max-h-64 space-y-2 overflow-y-auto rounded-md border border-slate-200 p-3">{serviceCatalog.filter(service => service.department_id === selectedEngineer?.department_id).map(service => <label key={service.id} className="flex items-start gap-2 text-sm text-slate-700"><input type="checkbox" checked={selectedServiceIds.includes(service.id)} onChange={() => setSelectedServiceIds(current => current.includes(service.id) ? current.filter(id => id !== service.id) : [...current, service.id])} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-cyan-700" /><span>{service.name}</span></label>)}</div>
      </form>
    </Modal>
  </div>;
}