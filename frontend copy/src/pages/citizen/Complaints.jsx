import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import StatusBadge from "@/components/common/StatusBadge";
import PriorityBadge from "@/components/common/PriorityBadge";
import Loading from "@/components/common/Loading";
import { formatDate } from "@/utils/civic";
import * as complaintsApi from "@/services/api/complaints";

export default function CitizenComplaints() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => { complaintsApi.listComplaints().then(setRows).finally(() => setLoading(false)); }, []);

  const columns = [
    { key: "id", label: "ID", render: r => <span className="font-medium text-slate-500">#{r.id}</span> },
    { key: "title", label: "Title", render: r => <span className="font-medium text-slate-800">{r.title}</span> },
    { key: "category", label: "Category" },
    { key: "ward", label: "Ward" },
    { key: "priority", label: "Priority", render: r => <PriorityBadge priority={r.priority} /> },
    { key: "status", label: "Status", render: r => <StatusBadge status={r.status} /> },
    { key: "created_at", label: "Created", render: r => formatDate(r.created_at) },
  ];

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Civic issues" title="My complaints" description="View and track issues you have reported." action={
      <button onClick={() => navigate("/citizen/complaints/new")} className="inline-flex items-center gap-2 rounded-xl bg-cyan-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800"><Plus className="h-4 w-4" /> New complaint</button>} />
    {loading ? <Loading /> : <DataTable columns={columns} rows={rows} onRowClick={r => navigate(`/citizen/complaints/${r.id}`)} emptyTitle="You have not reported any complaints yet" />}
  </div>;
}