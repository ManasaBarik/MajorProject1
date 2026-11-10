import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BriefcaseBusiness, Bell, Layers, Clock } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import StatCard from "@/components/common/StatCard";
import SectionCard from "@/components/common/SectionCard";
import StatusBadge from "@/components/common/StatusBadge";
import Loading from "@/components/common/Loading";
import WorkflowChooser from "@/components/common/WorkflowChooser";
import { timeAgo } from "@/utils/civic";
import * as applicationsApi from "@/services/api/applications";
import * as servicesApi from "@/services/api/services";
import * as businessesApi from "@/services/api/businesses";
import * as notificationsApi from "@/services/api/notifications";

export default function BusinessDashboard() {
  const [business, setBusiness] = useState(null);
  const [applications, setApplications] = useState([]);
  const [services, setServices] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([businessesApi.listBusinesses(), applicationsApi.listApplications(), servicesApi.listServices(), notificationsApi.listNotifications()])
      .then(([b, a, s, n]) => { setBusiness(b[0]); setApplications(a); setServices(s); setNotifications(n); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="px-5 py-8 sm:px-8"><Loading /></div>;
  const pending = applications.filter(a => ["SUBMITTED","UNDER_REVIEW","CLARIFICATION_REQUESTED"].includes(a.status)).length;
  const unread = notifications.filter(n => !n.read).length;

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Overview" title="Business dashboard" description={business ? `Manage ${business.name}` : "Manage your business"} action={
      <Link to="/business/services" className="inline-flex items-center gap-2 rounded-xl bg-cyan-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800"><Layers className="h-4 w-4" /> Browse services</Link>} />
    <WorkflowChooser basePath="/business" />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Applications" value={applications.length} icon={BriefcaseBusiness} tone="cyan" />
      <StatCard label="Pending review" value={pending} icon={Clock} tone="amber" />
      <StatCard label="Available services" value={services.length} icon={Layers} tone="cyan" />
      <StatCard label="Unread updates" value={unread} icon={Bell} tone="rose" />
    </div>
    <div className="mt-6 grid gap-6 lg:grid-cols-2">
      <SectionCard title="Business information" actions={<Link to="/business/profile" className="text-sm font-medium text-cyan-700 hover:underline">Edit</Link>}>
        {business ? <dl className="space-y-2 text-sm">
          <div className="flex justify-between"><dt className="text-slate-500">Owner</dt><dd className="font-medium">{business.owner_name}</dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">Type</dt><dd className="font-medium">{business.type}</dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">GSTIN</dt><dd className="font-medium">{business.gstin}</dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">License</dt><dd className="font-medium">{business.license_number}</dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">Address</dt><dd className="font-medium">{business.address}</dd></div>
        </dl> : <p className="text-sm text-slate-500">No business profile.</p>}
      </SectionCard>
      <SectionCard title="Recent applications" actions={<Link to="/business/applications" className="text-sm font-medium text-cyan-700 hover:underline">View all</Link>}>
        <div className="space-y-3">{applications.slice(0, 5).map(a => <Link key={a.id} to={`/business/applications/${a.id}`} className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3 hover:bg-slate-50">
          <div><p className="text-sm font-medium text-slate-800">{a.service.name}</p><p className="text-xs text-slate-400">{a.application_number} · {timeAgo(a.submitted_at)}</p></div>
          <StatusBadge status={a.status} /></Link>)}</div>
      </SectionCard>
    </div>
  </div>;
}