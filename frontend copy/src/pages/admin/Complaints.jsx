import React, { useEffect, useState } from "react";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import StatusBadge from "@/components/common/StatusBadge";
import PriorityBadge from "@/components/common/PriorityBadge";
import Loading from "@/components/common/Loading";
import { formatDate } from "@/utils/civic";
import * as complaintsApi from "@/services/api/complaints";

export default function AdminComplaints() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { complaintsApi.listComplaints().then(setRows).finally(() => setLoading(false)); }, []);

  const columns = [
    { key: "id", label: "ID", render: r => <span className="font-medium text-slate-500">#{r.id}</span> },
    { key: "title", label: "Title", render: r => <span className="font-medium text-slate-800">{r.title}</span> },
    { key: "category", label: "Category" },
    { key: "ward", label: "Ward", render: r => r.ward || "—" },
    { key: "department", label: "Department", render: r => r.department?.name || "Unassigned" },
    { key: "priority", label: "Priority", render: r => <PriorityBadge priority={r.priority} /> },
    { key: "status", label: "Status", render: r => <StatusBadge status={r.status} /> },
    { key: "created_at", label: "Created", render: r => formatDate(r.created_at) },
  ];

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="City operations" title="All complaints" description="Monitor complaint demand and official progress across the municipality." />
    {loading ? <Loading /> : <DataTable columns={columns} rows={rows} emptyTitle="No complaints" />}
  </div>;
}