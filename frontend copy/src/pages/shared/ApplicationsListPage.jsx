import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import StatusBadge from "@/components/common/StatusBadge";
import Loading from "@/components/common/Loading";
import { formatDate } from "@/utils/civic";
import * as applicationsApi from "@/services/api/applications";

export default function ApplicationsListPage({ basePath, newLabel = "New application", newTo }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  useEffect(() => { applicationsApi.listApplications().then(setRows).finally(() => setLoading(false)); }, []);

  const columns = [
    { key: "application_number", label: "App. no.", render: r => <span className="font-medium text-slate-800">{r.application_number}</span> },
    { key: "service", label: "Service", render: r => r.service?.name || "Unassigned" },
    { key: "department", label: "Department", render: r => r.department?.name || "Unassigned" },
    { key: "status", label: "Status", render: r => <StatusBadge status={r.status} /> },
    { key: "submitted_at", label: "Submitted", render: r => formatDate(r.submitted_at) },
  ];

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Municipal services" title="Applications" description="Track submitted service applications and requests." action={
      <button onClick={() => navigate(newTo)} className="inline-flex items-center gap-2 rounded-xl bg-cyan-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800"><Plus className="h-4 w-4" /> {newLabel}</button>} />
    {loading ? <Loading /> : <DataTable columns={columns} rows={rows} onRowClick={r => navigate(`${basePath}/applications/${r.id}`)} emptyTitle="No applications yet" />}
  </div>;
}