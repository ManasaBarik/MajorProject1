import React, { useEffect, useState } from "react";
import { HardHat, Building2 } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import Loading from "@/components/common/Loading";
import EmptyState from "@/components/common/EmptyState";
import * as servicesApi from "@/services/api/services";

export default function OfficerEngineers() {
  const [departments, setDepartments] = useState([]);
  const [staff, setStaff] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    servicesApi.listDepartments().then(async (depts) => {
      setDepartments(depts);
      const map = {};
      await Promise.all(depts.map(async d => { map[d.id] = await servicesApi.getDepartmentStaff(d.id); }));
      setStaff(map);
    }).finally(() => setLoading(false));
  }, []);

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Team" title="Field engineers" description="View staff available for authorized field assignments." />
    {loading ? <Loading /> : <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
      {departments.map(d => <SectionCard key={d.id} title={d.name} description={d.description}>
        {(staff[d.id] || []).filter(s => s.role === "ENGINEER").length ? <ul className="space-y-2">{staff[d.id].filter(s => s.role === "ENGINEER").map(e => <li key={e.id} className="flex items-center gap-3 rounded-lg border border-slate-100 px-3 py-2"><span className="rounded-lg bg-cyan-50 p-2"><HardHat className="h-4 w-4 text-cyan-700" /></span><div><p className="text-sm font-medium text-slate-800">{e.name}</p><p className="text-xs text-slate-400">Field engineer</p></div></li>)}</ul> : <p className="text-sm text-slate-500">No engineers assigned.</p>}
      </SectionCard>)}
    </div>}
  </div>;
}