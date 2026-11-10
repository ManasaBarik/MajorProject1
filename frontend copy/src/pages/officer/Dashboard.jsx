import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MessageSquareWarning, AlertTriangle, Loader, Clock, BriefcaseBusiness } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import StatCard from "@/components/common/StatCard";
import SectionCard from "@/components/common/SectionCard";
import StatusBadge from "@/components/common/StatusBadge";
import PriorityBadge from "@/components/common/PriorityBadge";
import Loading from "@/components/common/Loading";
import { timeAgo } from "@/utils/civic";
import * as complaintsApi from "@/services/api/complaints";
import * as applicationsApi from "@/services/api/applications";

export default function OfficerDashboard() {
  const [complaints, setComplaints] = useState([]);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([complaintsApi.listComplaints(), applicationsApi.listAssignedApplications()])
      .then(([c, a]) => { setComplaints(c); setApplications(a); }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="px-5 py-8 sm:px-8"><Loading /></div>;
  const newCount = complaints.filter(c => c.status === "SUBMITTED" || c.status === "CLASSIFIED").length;
  const assigned = complaints.filter(c => c.assigned_engineer).length;
  const highPriority = complaints.filter(c => ["HIGH","CRITICAL"].includes(c.priority) && !["RESOLVED","CLOSED","REJECTED"].includes(c.status)).length;
  const inProgress = complaints.filter(c => c.status === "IN_PROGRESS").length;

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Operations" title="Officer dashboard" description="Review assigned civic work and municipal service applications." />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="New complaints" value={newCount} icon={MessageSquareWarning} tone="cyan" />
      <StatCard label="High priority" value={highPriority} icon={AlertTriangle} tone="rose" />
      <StatCard label="In progress" value={inProgress} icon={Loader} tone="amber" />
      <StatCard label="Assigned applications" value={applications.length} icon={BriefcaseBusiness} tone="cyan" />
    </div>
    <div className="mt-6 grid gap-6 lg:grid-cols-2">
      <SectionCard title="Complaint queue" actions={<Link to="/officer/complaints" className="text-sm font-medium text-cyan-700 hover:underline">View all</Link>}>
        <div className="space-y-3">{complaints.slice(0, 6).map(c => <Link key={c.id} to={`/officer/complaints/${c.id}`} className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3 hover:bg-slate-50">
          <div className="flex items-center gap-3"><PriorityBadge priority={c.priority} /><div><p className="text-sm font-medium text-slate-800">{c.title}</p><p className="text-xs text-slate-400">{c.ward} · {timeAgo(c.created_at)}</p></div></div>
          <StatusBadge status={c.status} /></Link>)}</div>
      </SectionCard>
      <SectionCard title="Assigned applications" actions={<Link to="/officer/applications" className="text-sm font-medium text-cyan-700 hover:underline">View all</Link>}>
        <div className="space-y-3">{applications.slice(0, 6).map(a => <Link key={a.id} to={`/officer/applications/${a.id}`} className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3 hover:bg-slate-50">
          <div><p className="text-sm font-medium text-slate-800">{a.service.name}</p><p className="text-xs text-slate-400">{a.application_number}</p></div>
          <StatusBadge status={a.status} /></Link>)}</div>
      </SectionCard>
    </div>
  </div>;
}