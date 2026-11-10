import React, { useEffect, useState } from "react";
import { useParams, Link, useSearchParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Download, FileText } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import StatusBadge from "@/components/common/StatusBadge";
import Timeline from "@/components/common/Timeline";
import DynamicForm from "@/components/common/DynamicForm";
import Loading from "@/components/common/Loading";
import ErrorState from "@/components/common/ErrorState";
import Modal from "@/components/common/Modal";
import { formatDate } from "@/utils/civic";
import * as applicationsApi from "@/services/api/applications";
import * as servicesApi from "@/services/api/services";
import * as businessesApi from "@/services/api/businesses";

export default function ApplicationDetailPage({ basePath }) {
  const { id } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const isNew = id === "new";
  const [service, setService] = useState(null);
  const [application, setApplication] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [businesses, setBusinesses] = useState([]);
  const [businessId, setBusinessId] = useState("");
  const [loading, setLoading] = useState(!isNew);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [clarificationOpen, setClarificationOpen] = useState(false);

  useEffect(() => {
    let active = true;
    const initialize = async () => {
      setError("");
      if (isNew) {
        const sid = params.get("service");
        try {
          const [foundService, profiles] = await Promise.all([
            servicesApi.getService(sid),
            basePath === "/business" ? businessesApi.listBusinesses().catch(() => []) : Promise.resolve([]),
          ]);
          if (active) { setService(foundService); setBusinesses(profiles); }
        } catch (e) {
          if (active) setError(e.message);
        } finally {
          if (active) setLoading(false);
        }
        return;
      }

      setLoading(true);
      try {
        const [a, t] = await Promise.all([
          applicationsApi.getApplication(id),
          applicationsApi.getApplicationTimeline(id),
        ]);
        const foundService = await servicesApi.getService(a.service.id);
        if (active) { setApplication(a); setTimeline(t); setService(foundService); }
      } catch (e) {
        if (active) setError(e.message);
      } finally {
        if (active) setLoading(false);
      }
    };
    initialize();
    return () => { active = false; };
  }, [id, basePath, isNew, params]);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [a, t] = await Promise.all([
        applicationsApi.getApplication(id),
        applicationsApi.getApplicationTimeline(id),
      ]);
      const foundService = await servicesApi.getService(a.service.id);
      setApplication(a); setTimeline(t); setService(foundService);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const saveDownload = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  };

  const downloadDocument = async (documentItem) => {
    setActionError("");
    try {
      const blob = await applicationsApi.downloadApplicationDocument(id, documentItem.id);
      saveDownload(blob, documentItem.filename || `${documentItem.key}.file`);
    } catch (e) {
      setActionError(e.message);
    }
  };

  const submit = async (values) => {
    setSubmitting(true); setActionError("");
    try {
      const formData = new FormData();
      const data = {};
      formData.append("service_id", String(service.id));
      formData.append("draft", "true");
      if (businessId) formData.append("business_id", businessId);
      for (const [key, value] of Object.entries(values)) {
        if (typeof File !== "undefined" && value instanceof File) {
          formData.append(`document:${key}`, value);
        } else {
          data[key] = value;
        }
      }
      formData.append("data", JSON.stringify(data));
      const created = await applicationsApi.createApplication(formData);
      await applicationsApi.submitApplication(created.id);
      navigate(`${basePath}/applications/${created.id}`);
    }
    catch (e) { setActionError(e.message); } finally { setSubmitting(false); }
  };

  const respondToClarification = async (values) => {
    setSubmitting(true); setActionError("");
    try {
      const data = {};
      const uploads = [];
      for (const [key, value] of Object.entries(values)) {
        if (typeof File !== "undefined" && value instanceof File) uploads.push([key, value]);
        else data[key] = value;
      }
      await applicationsApi.updateApplication(id, { data });
      for (const [key, file] of uploads) {
        const requirement = service.requirements.find(field => field.key === key);
        const formData = new FormData();
        formData.append("key", key);
        formData.append("label", requirement?.label || key);
        formData.append("file", file);
        await applicationsApi.uploadApplicationDocument(id, formData);
      }
      await applicationsApi.submitApplication(id);
      setClarificationOpen(false);
      await load();
    } catch (e) {
      setActionError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="px-5 py-8 sm:px-8"><Loading /></div>;
  if (error && (!isNew || !service)) return <div className="px-5 py-8 sm:px-8"><ErrorState message={error} /></div>;

  if (isNew) return <div className="mx-auto max-w-3xl px-5 py-8 sm:px-8">
    <Link to={`${basePath}/services`} className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="h-4 w-4" /> Back to services</Link>
    <PageHeader eyebrow={service?.service_type || "New application"} title={service?.name} description={service?.description} />
    <SectionCard title="Application form" description={service?.eligibility || "Complete the service requirements below."}>
      {service ? <DynamicForm fields={service.requirements || []} beforeFields={basePath === "/business" && <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Link a business (optional)</label><select value={businessId} onChange={e => setBusinessId(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm"><option value="">Apply without linking a business</option>{businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div>} onSubmit={submit} submitLabel="Submit application" loading={submitting} formError={actionError} /> : <Loading />}
    </SectionCard>
  </div>;

  const clarificationStatuses = ["CLARIFICATION_REQUIRED", "CLARIFICATION_REQUESTED"];
  const responseFields = (service?.requirements || []).map(field => {
    const existing = application.documents?.some(documentItem => documentItem.key === field.key && documentItem.status !== "REJECTED");
    return field.type === "file" && existing ? { ...field, required: false } : field;
  });

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <Link to={`${basePath}/applications`} className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="h-4 w-4" /> Back to applications</Link>
    <PageHeader eyebrow={application.application_number} title={application.service.name} description={`${application.business_name ? `${application.business_name} · ` : ""}Submitted on ${formatDate(application.submitted_at)}`} action={<div className="flex flex-wrap items-center gap-2"><StatusBadge status={application.status} />{["APPROVED", "COMPLETED"].includes(application.status) && <button onClick={async () => { try { saveDownload(await applicationsApi.downloadApplicationCertificate(id), `approval-${application.application_number}.pdf`); } catch (e) { setActionError(e.message); } }} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"><Download className="h-4 w-4" /> Download certificate</button>}</div>} />
    {actionError && <p role="alert" className="mb-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{actionError}</p>}
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <div className="space-y-6">
        <SectionCard title="Submitted information">
          <dl className="grid gap-3 sm:grid-cols-2">{service?.requirements.filter(r => r.type !== "file").map(r => <div key={r.key}><dt className="text-xs font-medium text-slate-500">{r.label}</dt><dd className="mt-0.5 break-words text-sm text-slate-800">{application.data?.[r.key] ?? "—"}</dd></div>)}</dl>
        </SectionCard>
        <SectionCard title="Documents">
          {application.documents?.length ? <ul className="space-y-2">{application.documents.map(d => <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2 text-sm"><span className="flex items-center gap-2"><FileText className="h-4 w-4 text-slate-400" /> {d.label} <span className="text-xs text-slate-500">{d.status}</span></span><div className="flex items-center gap-3"><span className="text-xs text-slate-400">{d.filename}</span><button onClick={() => downloadDocument(d)} aria-label={`Download ${d.label}`} className="rounded-md p-1.5 text-slate-600 hover:bg-slate-100"><Download className="h-4 w-4" /></button></div></li>)}</ul> : <p className="text-sm text-slate-500">No documents.</p>}
        </SectionCard>
        {application.rejection_reason && <SectionCard title="Decision reason"><p className="text-sm leading-6 text-slate-700">{application.rejection_reason}</p></SectionCard>}
        {clarificationStatuses.includes(application.status) && <SectionCard title="More information requested" description="Update your information or upload additional documents, then resubmit for review."><button onClick={() => setClarificationOpen(true)} className="rounded-lg bg-cyan-800 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-900">Respond to clarification</button></SectionCard>}
      </div>
      <SectionCard title="Timeline"><Timeline events={timeline} /></SectionCard>
    </div>
    <Modal open={clarificationOpen} onClose={() => setClarificationOpen(false)} title="Respond to clarification">
      <DynamicForm key={`clarification-${application.id}`} fields={responseFields} initialValues={application.data || {}} onSubmit={respondToClarification} submitLabel="Resubmit application" loading={submitting} formError={actionError} />
    </Modal>
  </div>;
}