import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clock, IndianRupee, ArrowRight } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import Loading from "@/components/common/Loading";
import * as servicesApi from "@/services/api/services";

export default function ServicesPage({ basePath }) {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  useEffect(() => { servicesApi.listServices().then(setServices).finally(() => setLoading(false)); }, []);

  const groups = [
    { type: "MUNICIPAL", title: "Municipal services" },
    { type: "BUSINESS", title: "Business services" },
    { type: "OTHER", title: "Other services" },
  ];

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Service directory" title="Select a required service" description="Compare eligibility, required documents, fees, and processing times before applying." />
    {loading ? <Loading /> : groups.map(group => {
      const rows = services.filter(service => group.type === "OTHER"
        ? !["MUNICIPAL", "BUSINESS"].includes(service.service_type)
        : service.service_type === group.type);
      if (!rows.length) return null;
      return <section key={group.type} className="mb-8">
        <h2 className="mb-3 border-b border-slate-200 pb-2 text-lg font-semibold text-slate-900">{group.title}</h2>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map(s => <SectionCard key={s.id}>
            <span className="rounded-md bg-cyan-50 px-2 py-1 text-xs font-semibold text-cyan-800">{s.code}</span>
            <h3 className="mt-3 font-semibold text-slate-900">{s.name}</h3>
            <p className="mt-1.5 text-sm leading-6 text-slate-600">{s.description}</p>
            <dl className="mt-4 space-y-2 border-t border-slate-100 pt-3 text-sm">
              <div className="flex justify-between gap-3"><dt className="text-slate-500">Department</dt><dd className="text-right font-medium text-slate-800">{s.department?.name || "—"}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-slate-500">Eligibility</dt><dd className="text-right text-slate-700">{s.eligibility || "Open to eligible applicants"}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-slate-500">Processing</dt><dd className="flex items-center gap-1 text-slate-700"><Clock className="h-3.5 w-3.5" /> {s.processing_time_days} days</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-slate-500">Fee</dt><dd className="flex items-center gap-1 text-slate-700"><IndianRupee className="h-3.5 w-3.5" /> {Number(s.fee) ? s.fee : "No fee"}</dd></div>
              <div><dt className="text-slate-500">Required information</dt><dd className="mt-1 text-slate-700">{(s.requirements || []).length ? s.requirements.map(field => field.label).join(", ") : "No additional fields"}</dd></div>
            </dl>
            {s.procedure && <details className="mt-3 text-sm"><summary className="cursor-pointer font-medium text-cyan-800">Application procedure</summary><p className="mt-2 leading-6 text-slate-600">{s.procedure}</p></details>}
            <button onClick={() => navigate(`${basePath}/applications/new?service=${s.id}`)} className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-800 py-2.5 text-sm font-semibold text-white hover:bg-cyan-900">Apply <ArrowRight className="h-4 w-4" /></button>
          </SectionCard>)}
        </div>
      </section>;
    })}
  </div>;
}