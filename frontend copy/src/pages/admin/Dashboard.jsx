import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MessageSquareWarning, CheckCircle2, Clock, Map as MapIcon } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import StatCard from "@/components/common/StatCard";
import SectionCard from "@/components/common/SectionCard";
import MapView from "@/components/common/MapView";
import Loading from "@/components/common/Loading";
import * as analyticsApi from "@/services/api/analytics";

export default function AdminDashboard() {
  const [overview, setOverview] = useState(null);
  const [mapPoints, setMapPoints] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([analyticsApi.getOverview(), analyticsApi.getMapComplaints()])
      .then(([o, m]) => { setOverview(o); setMapPoints(m); }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="px-5 py-8 sm:px-8"><Loading /></div>;

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="City overview" title="Administration dashboard" description="Monitor municipal performance across complaints, departments, wards, and services." action={<Link to="/admin/analytics" className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">Full analytics</Link>} />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Total complaints" value={overview?.total_complaints ?? "—"} icon={MessageSquareWarning} tone="cyan" />
      <StatCard label="Open complaints" value={overview?.open_complaints ?? "—"} icon={Clock} tone="amber" />
      <StatCard label="Resolved complaints" value={overview?.resolved_complaints ?? "—"} icon={CheckCircle2} tone="emerald" />
      <StatCard label="Avg. resolution time" value={overview?.average_resolution_time_hours ? `${overview.average_resolution_time_hours}h` : "—"} icon={Clock} tone="cyan" />
    </div>
    <div className="mt-6 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
      <SectionCard title="Civic issue map" description="Privacy-safe complaint locations across the city." actions={<Link to="/admin/map" className="inline-flex items-center gap-1.5 text-sm font-medium text-cyan-700 hover:underline"><MapIcon className="h-4 w-4" /> Open GIS</Link>}>
        <MapView points={mapPoints} height={360} />
      </SectionCard>
      <SectionCard title="At a glance">
        <dl className="space-y-3 text-sm">
          {[["Overdue complaints", overview?.overdue_complaints], ["Total applications", overview?.total_applications], ["Pending applications", overview?.pending_applications]].map(([k, v]) => <div key={k} className="flex justify-between border-b border-slate-100 pb-2 last:border-0"><dt className="text-slate-500">{k}</dt><dd className="font-semibold text-slate-900">{v ?? "—"}</dd></div>)}
        </dl>
      </SectionCard>
    </div>
  </div>;
}