import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, UserPlus, RefreshCw, GitBranch, CheckCircle2, XCircle, Sparkles } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import StatusBadge from "@/components/common/StatusBadge";
import PriorityBadge from "@/components/common/PriorityBadge";
import AIRecommendationCard from "@/components/common/AIRecommendationCard";
import Timeline from "@/components/common/Timeline";
import MapView from "@/components/common/MapView";
import Modal from "@/components/common/Modal";
import Loading from "@/components/common/Loading";
import ErrorState from "@/components/common/ErrorState";
import { formatDate, getNextStatuses, statusLabel } from "@/utils/civic";
import * as complaintsApi from "@/services/api/complaints";
import * as servicesApi from "@/services/api/services";

export default function OfficerComplaintDetail() {
  const { id } = useParams();
  const [complaint, setComplaint] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [ai, setAi] = useState(null);
  const [engineers, setEngineers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modal, setModal] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  const load = () => {
    setLoading(true); setError("");
    Promise.all([complaintsApi.getComplaint(id), complaintsApi.getComplaintTimeline(id), complaintsApi.getComplaintAI(id)])
      .then(async ([c, t, a]) => {
        setComplaint(c); setTimeline(t); setAi(a);
        try { setEngineers(await servicesApi.getDepartmentStaff(c.department.id)); } catch { setEngineers([]); }
        try { setDepartments(await servicesApi.listDepartments()); } catch { setDepartments([]); }
      }).catch(e => setError(e.message)).finally(() => setLoading(false));
  };
  useEffect(load, [id]);

  const run = async (fn, modalName) => {
    setActionLoading(true);
    try { await fn(); setModal(null); load(); } catch (e) { setError(e.message); } finally { setActionLoading(false); }
  };

  if (loading) return <div className="px-5 py-8 sm:px-8"><Loading /></div>;
  if (error && !complaint) return <div className="px-5 py-8 sm:px-8"><ErrorState message={error} onRetry={load} /></div>;
  if (!complaint) return <div className="px-5 py-8 sm:px-8"><ErrorState message="Complaint not found." /></div>;

  const nextStatuses = getNextStatuses(complaint.status);
  const canAssign = ["CLASSIFIED","ASSIGNED"].includes(complaint.status);
  const canResolve = ["IN_PROGRESS","ON_HOLD"].includes(complaint.status);
  const canVerify = complaint.status === "VERIFICATION_PENDING";
  const aiPending = !!ai && ["SUBMITTED","AI_PROCESSING"].includes(complaint.status) && !!ai.category && !!ai.department_id && !ai.is_overridden;
  const canOverrideAI = !!ai && !["CLOSED","REJECTED"].includes(complaint.status);

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <Link to="/officer/complaints" className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="h-4 w-4" /> Back to queue</Link>
    <PageHeader eyebrow={`Complaint #${complaint.id}`} title={complaint.title} description={`Reported by ${complaint.citizen_name} on ${formatDate(complaint.created_at)}`} action={<div className="flex gap-2"><PriorityBadge priority={complaint.priority} /><StatusBadge status={complaint.status} /></div>} />
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <div className="space-y-6">
        <SectionCard title="Description"><p className="text-sm leading-7 text-slate-700">{complaint.description}</p></SectionCard>
        <AIRecommendationCard ai={ai} canOverride={canOverrideAI} onOverride={() => setModal("ai")} onAccept={aiPending ? () => run(() => complaintsApi.acceptComplaintAI(id)) : undefined} accepting={actionLoading} />
        {complaint.latitude && <SectionCard title="Location"><MapView points={[{ id: complaint.id, latitude: complaint.latitude, longitude: complaint.longitude, priority: complaint.priority, category: complaint.category, ward: complaint.ward, status: complaint.status }]} center={[complaint.latitude, complaint.longitude]} height={280} /></SectionCard>}
        <SectionCard title="Officer actions">
          <div className="flex flex-wrap gap-2">
            {canAssign && <button onClick={() => setModal("assign")} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"><UserPlus className="h-4 w-4" /> {complaint.assigned_engineer ? "Reassign" : "Assign"}</button>}
            {nextStatuses.length > 0 && <button onClick={() => setModal("status")} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"><GitBranch className="h-4 w-4" /> Update status</button>}
            {canResolve && <button onClick={() => setModal("resolution")} className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700"><RefreshCw className="h-4 w-4" /> Submit resolution</button>}
            {canVerify && <>
              <button onClick={() => setModal("verify-approve")} className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"><CheckCircle2 className="h-4 w-4" /> Approve</button>
              <button onClick={() => setModal("verify-reject")} className="inline-flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700"><XCircle className="h-4 w-4" /> Reject</button>
            </>}
            {nextStatuses.length === 0 && !canAssign && !canResolve && !canVerify && <p className="text-sm text-slate-500">No further actions available for this status.</p>}
          </div>
        </SectionCard>
      </div>
      <div className="space-y-6">
        <SectionCard title="Details">
          <dl className="space-y-2 text-sm">
            {[["Department", complaint.department?.name], ["Category", complaint.category], ["Ward", complaint.ward], ["Assigned to", complaint.assigned_engineer?.name || "Unassigned"], ["Updated", formatDate(complaint.updated_at)]].map(([k, v]) => <div key={k} className="flex justify-between border-b border-slate-100 pb-2 last:border-0"><dt className="text-slate-500">{k}</dt><dd className="font-medium text-slate-800">{v || "—"}</dd></div>)}
          </dl>
        </SectionCard>
        <SectionCard title="Timeline"><Timeline events={timeline} /></SectionCard>
      </div>
    </div>

    <AssignModal open={modal === "assign"} onClose={() => setModal(null)} engineers={engineers} loading={actionLoading} onSubmit={eid => run(() => (complaint.assigned_engineer ? complaintsApi.reassignComplaint(id, eid) : complaintsApi.assignComplaint(id, eid)))} />
    <StatusModal open={modal === "status"} onClose={() => setModal(null)} nextStatuses={nextStatuses} loading={actionLoading} onSubmit={(s, r) => run(() => complaintsApi.updateComplaintStatus(id, s, r))} />
    <ResolutionModal open={modal === "resolution"} onClose={() => setModal(null)} loading={actionLoading} onSubmit={data => run(() => complaintsApi.submitResolution(id, data))} />
    <VerifyModal open={modal === "verify-approve" || modal === "verify-reject"} approved={modal === "verify-approve"} onClose={() => setModal(null)} loading={actionLoading} onSubmit={(approved, remarks) => run(() => complaintsApi.verifyResolution(id, approved, remarks))} />
    <AIReviewModal open={modal === "ai"} onClose={() => setModal(null)} ai={ai} departments={departments} loading={actionLoading} onSubmit={data => run(() => complaintsApi.reviewAI(id, data))} />
  </div>;
}

function AssignModal({ open, onClose, engineers, loading, onSubmit }) {
  const [eid, setEid] = useState("");
  return <Modal open={open} onClose={onClose} title="Assign engineer" footer={<><button onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button disabled={loading || !eid} onClick={() => onSubmit(Number(eid))} className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{loading ? "Assigning…" : "Assign"}</button></>}>
    <select value={eid} onChange={e => setEid(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm"><option value="">Select engineer…</option>{engineers.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}</select>
  </Modal>;
}

function StatusModal({ open, onClose, nextStatuses, loading, onSubmit }) {
  const [status, setStatus] = useState("");
  const [remarks, setRemarks] = useState("");
  return <Modal open={open} onClose={onClose} title="Update status" footer={<><button onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button disabled={loading || !status} onClick={() => { onSubmit(status, remarks); setStatus(""); setRemarks(""); }} className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{loading ? "Updating…" : "Update"}</button></>}>
    <div className="space-y-3">
      <select value={status} onChange={e => setStatus(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm"><option value="">Select next status…</option>{nextStatuses.map(s => <option key={s} value={s}>{statusLabel(s)}</option>)}</select>
      <textarea value={remarks} onChange={e => setRemarks(e.target.value)} rows={3} placeholder="Remarks" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
    </div>
  </Modal>;
}

function ResolutionModal({ open, onClose, loading, onSubmit }) {
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  return <Modal open={open} onClose={onClose} title="Submit resolution" footer={<><button onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button disabled={loading || !description} onClick={() => { const fd = new FormData(); fd.append("description", description); if (file) fd.append("evidence", file); onSubmit(fd); setDescription(""); setFile(null); }} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60">{loading ? "Submitting…" : "Submit"}</button></>}>
    <div className="space-y-3">
      <textarea value={description} onChange={e => setDescription(e.target.value)} rows={4} placeholder="Describe the resolution work done" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
      <input type="file" onChange={e => setFile(e.target.files[0])} className="w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2" />
    </div>
  </Modal>;
}

function VerifyModal({ open, approved, onClose, loading, onSubmit }) {
  const [remarks, setRemarks] = useState("");
  return <Modal open={open} onClose={onClose} title={approved ? "Approve resolution" : "Reject resolution"} footer={<><button onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button disabled={loading} onClick={() => { onSubmit(approved, remarks); setRemarks(""); }} className={`rounded-lg px-4 py-2 text-sm font-semibold text-white ${approved ? "bg-emerald-600 hover:bg-emerald-700" : "bg-rose-600 hover:bg-rose-700"} disabled:opacity-60`}>{loading ? "Verifying…" : approved ? "Approve" : "Reject"}</button></>}>
    <textarea value={remarks} onChange={e => setRemarks(e.target.value)} rows={3} placeholder="Verification remarks" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
  </Modal>;
}

function AIReviewModal({ open, onClose, ai, departments = [], loading, onSubmit }) {
  const [form, setForm] = useState({ category: "", priority: "MEDIUM", department_id: "" });
  useEffect(() => {
    if (open) setForm({
      category: ai?.category || "",
      priority: ai?.priority || "MEDIUM",
      department_id: ai?.department_id ? String(ai.department_id) : "",
    });
  }, [open, ai]);
  const submit = () => {
    const payload = { category: form.category, priority: form.priority };
    if (form.department_id) payload.department_id = Number(form.department_id);
    onSubmit(payload);
  };
  return <Modal open={open} onClose={onClose} title="Review / override AI recommendation" footer={<><button onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button disabled={loading} onClick={submit} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"><Sparkles className="h-4 w-4" /> {loading ? "Saving…" : "Save override"}</button></>}>
    <p className="mb-3 text-xs text-slate-500">Override the AI recommendation with the officer's decision. This records the official classification.</p>
    <div className="space-y-3">
      <div><label className="mb-1 block text-sm font-medium text-slate-700">Category</label><input value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
      <div><label className="mb-1 block text-sm font-medium text-slate-700">Priority</label><select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">{["LOW","MEDIUM","HIGH","CRITICAL"].map(p => <option key={p} value={p}>{p}</option>)}</select></div>
      <div><label className="mb-1 block text-sm font-medium text-slate-700">Department</label><select value={form.department_id} onChange={e => setForm(f => ({ ...f, department_id: e.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="">— keep current —</option>{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
    </div>
  </Modal>;
}