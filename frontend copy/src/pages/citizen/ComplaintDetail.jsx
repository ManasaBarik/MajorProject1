import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, MapPin, User, Building2 } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import StatusBadge from "@/components/common/StatusBadge";
import PriorityBadge from "@/components/common/PriorityBadge";
import AIRecommendationCard from "@/components/common/AIRecommendationCard";
import Timeline from "@/components/common/Timeline";
import MapView from "@/components/common/MapView";
import Loading from "@/components/common/Loading";
import ErrorState from "@/components/common/ErrorState";
import { formatDate } from "@/utils/civic";
import * as complaintsApi from "@/services/api/complaints";

export default function CitizenComplaintDetail() {
  const { id } = useParams();
  const [complaint, setComplaint] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [ai, setAi] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState({ rating: 5, comment: "" });
  const [fbLoading, setFbLoading] = useState(false);
  const [fbSent, setFbSent] = useState(false);

  const load = () => {
    setLoading(true); setError("");
    Promise.all([complaintsApi.getComplaint(id), complaintsApi.getComplaintTimeline(id), complaintsApi.getComplaintAI(id)])
      .then(([c, t, a]) => { setComplaint(c); setTimeline(t); setAi(a); })
      .catch(e => setError(e.message)).finally(() => setLoading(false));
  };
  useEffect(load, [id]);

  const submitFeedback = async (e) => {
    e.preventDefault(); setFbLoading(true);
    try { await complaintsApi.submitFeedback(id, feedback); setFbSent(true); } finally { setFbLoading(false); }
  };

  if (loading) return <div className="px-5 py-8 sm:px-8"><Loading /></div>;
  if (error) return <div className="px-5 py-8 sm:px-8"><ErrorState message={error} onRetry={load} /></div>;
  if (!complaint) return <div className="px-5 py-8 sm:px-8"><ErrorState message="Complaint not found." /></div>;

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <Link to="/citizen/complaints" className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="h-4 w-4" /> Back to complaints</Link>
    <PageHeader eyebrow={`Complaint #${complaint.id}`} title={complaint.title} description={`Reported on ${formatDate(complaint.created_at)} · ${complaint.ward}`} action={<div className="flex gap-2"><PriorityBadge priority={complaint.priority} /><StatusBadge status={complaint.status} /></div>} />
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <div className="space-y-6">
        <SectionCard title="Description"><p className="text-sm leading-7 text-slate-700">{complaint.description}</p></SectionCard>
        <AIRecommendationCard ai={ai} />
        {complaint.latitude && <SectionCard title="Location" actions={<span className="flex items-center gap-1.5 text-xs text-slate-500"><MapPin className="h-3.5 w-3.5" /> {complaint.address}</span>}>
          <MapView points={[{ id: complaint.id, latitude: complaint.latitude, longitude: complaint.longitude, priority: complaint.priority, category: complaint.category, ward: complaint.ward, status: complaint.status }]} center={[complaint.latitude, complaint.longitude]} height={300} />
        </SectionCard>}
        {complaint.status === "RESOLVED" && (fbSent ? <SectionCard title="Feedback"><p className="text-sm text-emerald-700">Thank you for your feedback.</p></SectionCard> :
          <SectionCard title="Submit feedback"><form onSubmit={submitFeedback} className="space-y-3">
            <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Rating</label><select value={feedback.rating} onChange={e => setFeedback(f => ({ ...f, rating: Number(e.target.value) }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">{[5,4,3,2,1].map(n => <option key={n} value={n}>{n} stars</option>)}</select></div>
            <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Comment</label><textarea rows={3} value={feedback.comment} onChange={e => setFeedback(f => ({ ...f, comment: e.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>
            <button disabled={fbLoading} className="rounded-xl bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{fbLoading ? "Submitting…" : "Submit feedback"}</button>
          </form></SectionCard>)}
      </div>
      <div className="space-y-6">
        <SectionCard title="Details">
          <dl className="space-y-3 text-sm">
            <Row icon={Building2} label="Department" value={complaint.department?.name} />
            <Row label="Category" value={complaint.category} />
            <Row label="Ward" value={complaint.ward} />
            <Row icon={User} label="Assigned to" value={complaint.assigned_engineer?.name || "Unassigned"} />
            <Row label="Updated" value={formatDate(complaint.updated_at)} />
          </dl>
        </SectionCard>
        <SectionCard title="Timeline"><Timeline events={timeline} /></SectionCard>
      </div>
    </div>
  </div>;
}

function Row({ icon: Icon, label, value }) {
  return <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-2 last:border-0 last:pb-0">
    <dt className="flex items-center gap-1.5 text-slate-500">{Icon && <Icon className="h-3.5 w-3.5" />}{label}</dt>
    <dd className="font-medium text-slate-800">{value || "—"}</dd>
  </div>;
}