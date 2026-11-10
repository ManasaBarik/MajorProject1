import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BriefcaseBusiness, Bell } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import StatCard from "@/components/common/StatCard";
import SectionCard from "@/components/common/SectionCard";
import StatusBadge from "@/components/common/StatusBadge";
import Loading from "@/components/common/Loading";
import WorkflowChooser from "@/components/common/WorkflowChooser";
import { timeAgo } from "@/utils/civic";
import { isWorkflowAvailable } from "@/utils/workflows";
import * as complaintsApi from "@/services/api/complaints";
import * as applicationsApi from "@/services/api/applications";
import * as notificationsApi from "@/services/api/notifications";

export default function CitizenDashboard() {
  const [applications, setApplications] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      isWorkflowAvailable("complaints") ? complaintsApi.listComplaints() : Promise.resolve([]),
      applicationsApi.listApplications(),
      notificationsApi.listNotifications(),
    ])
      .then(([, a, n]) => { setApplications(a); setNotifications(n); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="px-5 py-8 sm:px-8"><Loading /></div>;
  const unread = notifications.filter(n => !n.read).length;

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Overview" title="Citizen dashboard" description="Choose a workflow, then follow its progress here." />
    <WorkflowChooser basePath="/citizen" />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <StatCard label="Applications" value={applications.length} icon={BriefcaseBusiness} tone="cyan" />
      <StatCard label="Unread notifications" value={unread} icon={Bell} tone="rose" />
    </div>
    <div className="mt-6 grid gap-6">
      <SectionCard title="Recent applications" actions={<Link to="/citizen/applications" className="text-sm font-medium text-cyan-700 hover:underline">View all</Link>}>
        <div className="space-y-3">{applications.slice(0, 5).map(a => <Link key={a.id} to={`/citizen/applications/${a.id}`} className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3 hover:bg-slate-50">
          <div><p className="text-sm font-medium text-slate-800">{a.service.name}</p><p className="text-xs text-slate-400">{a.application_number} · {timeAgo(a.submitted_at)}</p></div>
          <StatusBadge status={a.status} /></Link>)}</div>
      </SectionCard>
    </div>
  </div>;
}