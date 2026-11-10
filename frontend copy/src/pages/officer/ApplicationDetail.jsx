import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, FileText, CheckCircle2, XCircle, HelpCircle, Eye, Download, UserCog } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import StatusBadge from "@/components/common/StatusBadge";
import Timeline from "@/components/common/Timeline";
import Modal from "@/components/common/Modal";
import Loading from "@/components/common/Loading";
import ErrorState from "@/components/common/ErrorState";
import { formatDate } from "@/utils/civic";
import { useCivicAuth } from "@/contexts/CivicAuthContext";
import * as applicationsApi from "@/services/api/applications";
import * as servicesApi from "@/services/api/services";

export default function OfficerApplicationDetail() {
  const { id } = useParams();
  const { user } = useCivicAuth();
  const [application, setApplication] = useState(null);
  const [service, setService] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [eligibleEngineers, setEligibleEngineers] = useState([]);
  const [engineerProfileId, setEngineerProfileId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modal, setModal] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [clarification, setClarification] = useState("");

  const load = () => {
    setLoading(true);
    Promise.all([applicationsApi.getApplication(id), applicationsApi.getApplicationTimeline(id)])
      .then(async ([a, t]) => {
        setApplication(a); setTimeline(t);
        try { setService(await servicesApi.getService(a.service.id)); } catch {}
        if (user?.role === "OFFICER" && ["UNDER_REVIEW", "DOCUMENT_VERIFICATION", "ENGINEER_REVIEW", "FIELD_VERIFICATION"].includes(a.status)) {
          try { setEligibleEngineers(await applicationsApi.listEligibleApplicationEngineers(id)); } catch { setEligibleEngineers([]); }
        } else {
          setEligibleEngineers([]);
        }
      })
      .catch(e => setError(e.message)).finally(() => setLoading(false));
  };
  useEffect(load, [id, user?.role]);

  const run = async (fn) => { setActionLoading(true); try { await fn(); setModal(null); load(); } catch (e) { setError(e.message); } finally { setActionLoading(false); } };

  const download = async (fn, filename) => {
    try {
      const blob = await fn();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <div className="px-5 py-8 sm:px-8"><Loading /></div>;
  if (error && !application) return <div className="px-5 py-8 sm:px-8"><ErrorState message={error} onRetry={load} /></div>;
  if (!application) return <div className="px-5 py-8 sm:px-8"><ErrorState message="Application not found." /></div>;

  const open = !["APPROVED", "REJECTED", "COMPLETED", "CANCELLED"].includes(application.status);
  const isOfficer = user?.role === "OFFICER";
  const isAssignedEngineer = user?.role === "ENGINEER" && application.assigned_engineer?.user_id === user.id;
  const canStartReview = application.status === "SUBMITTED";
  const canRequestClarification = ["SUBMITTED", "UNDER_REVIEW", "DOCUMENT_VERIFICATION", "FIELD_VERIFICATION"].includes(application.status);
  const canAssignEngineer = isOfficer && ["UNDER_REVIEW", "DOCUMENT_VERIFICATION", "ENGINEER_REVIEW", "FIELD_VERIFICATION"].includes(application.status);
  const canCompleteEngineerReview = isAssignedEngineer && ["ENGINEER_REVIEW", "FIELD_VERIFICATION"].includes(application.status);
  const canComplete = application.status === "APPROVED";

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <Link to="/officer/applications" className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="h-4 w-4" /> Back to applications</Link>
    <PageHeader eyebrow={application.application_number} title={application.service.name} description={`${application.applicant_name}${application.business_name ? ` · ${application.business_name}` : ""} · Submitted ${formatDate(application.submitted_at)}`} action={<div className="flex flex-wrap items-center gap-2"><StatusBadge status={application.status} />{["APPROVED", "COMPLETED"].includes(application.status) && <button onClick={() => download(() => applicationsApi.downloadApplicationCertificate(id), `approval-${application.application_number}.pdf`)} aria-label="Download approval certificate" className="rounded-lg border border-slate-300 p-2 text-slate-700 hover:bg-slate-50"><Download className="h-4 w-4" /></button>}</div>} />
    {error && <p role="alert" className="mb-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <div className="space-y-6">
        <SectionCard title="Submitted information">
          <dl className="grid gap-3 sm:grid-cols-2">{service?.requirements.filter(r => r.type !== "file").map(r => <div key={r.key}><dt className="text-xs font-medium text-slate-500">{r.label}</dt><dd className="mt-0.5 break-words text-sm text-slate-800">{application.data?.[r.key] ?? "—"}</dd></div>)}</dl>
        </SectionCard>
        <SectionCard title="Documents">
          {application.documents?.length ? <ul className="space-y-2">{application.documents.map(d => <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2 text-sm"><span className="flex items-center gap-2"><FileText className="h-4 w-4 text-slate-400" /> {d.label} <span className="text-xs text-slate-500">{d.status}</span></span><div className="flex items-center gap-2"><span className="text-xs text-slate-400">{d.filename}</span><button onClick={() => download(() => applicationsApi.downloadApplicationDocument(id, d.id), d.filename || `${d.key}.file`)} aria-label={`Download ${d.label}`} className="rounded-md p-1.5 text-slate-600 hover:bg-slate-100"><Download className="h-4 w-4" /></button>{open && d.status === "PENDING" && <><button onClick={() => run(() => applicationsApi.verifyApplicationDocument(id, d.id, { status: "VERIFIED", remarks: "Document verified." }))} className="rounded-md px-2 py-1 text-xs font-semibold text-emerald-800 hover:bg-emerald-50">Verify</button><button onClick={() => run(() => applicationsApi.verifyApplicationDocument(id, d.id, { status: "REJECTED", remarks: "Please provide a clearer document." }))} className="rounded-md px-2 py-1 text-xs font-semibold text-rose-800 hover:bg-rose-50">Reject</button></>}</div></li>)}</ul> : <p className="text-sm text-slate-500">No documents.</p>}
        </SectionCard>
        {open && <SectionCard title="Officer actions" description="Review the application and record each decision in its timeline.">
          <div className="flex flex-wrap gap-2">
            {canStartReview && <button onClick={() => run(() => applicationsApi.reviewApplication(id, {}))} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"><Eye className="h-4 w-4" /> Mark under review</button>}
            {canAssignEngineer && <button onClick={() => { setEngineerProfileId(application.assigned_engineer?.id ? String(application.assigned_engineer.id) : ""); setModal("assign-engineer"); }} className="inline-flex items-center gap-2 rounded-lg border border-cyan-300 px-4 py-2 text-sm font-semibold text-cyan-900 hover:bg-cyan-50"><UserCog className="h-4 w-4" /> {application.assigned_engineer ? "Reassign engineer" : "Assign engineer"}</button>}
            {canRequestClarification && <button onClick={() => setModal("clarify")} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"><HelpCircle className="h-4 w-4" /> Request clarification</button>}
            {canCompleteEngineerReview && <button onClick={() => run(() => applicationsApi.completeEngineerReview(id, application.status === "FIELD_VERIFICATION" ? "Field verification completed." : "Engineer review completed."))} className="inline-flex items-center gap-2 rounded-lg border border-emerald-300 px-4 py-2 text-sm font-semibold text-emerald-800 hover:bg-emerald-50"><CheckCircle2 className="h-4 w-4" /> {application.status === "FIELD_VERIFICATION" ? "Complete field verification" : "Complete engineer review"}</button>}
            {canRequestClarification && <><button onClick={() => setModal("approve")} className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800"><CheckCircle2 className="h-4 w-4" /> Approve</button><button onClick={() => setModal("reject")} className="inline-flex items-center gap-2 rounded-lg bg-rose-700 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-800"><XCircle className="h-4 w-4" /> Reject</button></>}
            {canComplete && <button onClick={() => run(() => applicationsApi.updateApplicationStatus(id, "COMPLETED", "Service completed."))} className="inline-flex items-center gap-2 rounded-lg bg-cyan-800 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-900"><CheckCircle2 className="h-4 w-4" /> Mark completed</button>}
          </div>
        </SectionCard>}
      </div>
      <SectionCard title="Timeline"><Timeline events={timeline} /></SectionCard>
    </div>

    <Modal open={modal === "assign-engineer"} onClose={() => setModal(null)} title={application.assigned_engineer ? "Reassign engineer" : "Assign engineer"} footer={<><button onClick={() => setModal(null)} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button disabled={actionLoading || !engineerProfileId} onClick={() => run(() => applicationsApi.assignApplicationEngineer(id, Number(engineerProfileId)))} className="rounded-lg bg-cyan-800 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-900 disabled:opacity-60">{actionLoading ? "Assigning…" : "Assign"}</button></>}>
      {eligibleEngineers.length ? <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Engineer qualified for {application.service.name}</label><select value={engineerProfileId} onChange={e => setEngineerProfileId(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm"><option value="">Select engineer</option>{eligibleEngineers.map(engineer => <option key={engineer.id} value={engineer.id}>{engineer.name} · {engineer.specialization || "General"} · {engineer.workload} active</option>)}</select></div> : <p className="text-sm text-amber-900">No available engineer is qualified for this service. Ask an administrator to assign this service to an engineer in the department.</p>}
    </Modal>
    <Modal open={modal === "clarify"} onClose={() => setModal(null)} title="Request clarification" footer={<><button onClick={() => setModal(null)} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button disabled={actionLoading || !clarification} onClick={() => run(() => applicationsApi.requestClarification(id, { message: clarification }))} className="rounded-lg bg-cyan-800 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-900 disabled:opacity-60">{actionLoading ? "Sending…" : "Send request"}</button></>}>
      <textarea value={clarification} onChange={e => setClarification(e.target.value)} rows={4} placeholder="What additional information or document is required?" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
    </Modal>
    <Modal open={modal === "approve"} onClose={() => setModal(null)} title="Approve application" footer={<><button onClick={() => setModal(null)} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button disabled={actionLoading} onClick={() => run(() => applicationsApi.approveApplication(id, {}))} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">{actionLoading ? "Approving…" : "Confirm approval"}</button></>}>
      <p className="text-sm text-slate-600">Confirm approval of this application. The applicant will be notified.</p>
    </Modal>
    <Modal open={modal === "reject"} onClose={() => setModal(null)} title="Reject application" footer={<><button onClick={() => setModal(null)} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">Cancel</button><button disabled={actionLoading || !rejectReason} onClick={() => run(() => applicationsApi.rejectApplication(id, rejectReason))} className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700 disabled:opacity-60">{actionLoading ? "Rejecting…" : "Confirm rejection"}</button></>}>
      <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} rows={4} placeholder="Reason for rejection" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
    </Modal>
  </div>;
}