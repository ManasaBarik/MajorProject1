import React, { useEffect, useState } from "react";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import Loading from "@/components/common/Loading";
import { formatDateTime } from "@/utils/civic";
import * as usersApi from "@/services/api/users";

export default function AdminAuditLogs() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { usersApi.listAuditLogs().then(setRows).finally(() => setLoading(false)); }, []);

  const columns = [
    { key: "id", label: "ID", render: r => <span className="font-medium text-slate-500">#{r.id}</span> },
    { key: "actor", label: "Actor", render: r => <span className="font-medium text-slate-800">{r.actor}</span> },
    { key: "action", label: "Action", render: r => <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">{r.action}</span> },
    { key: "target", label: "Target" },
    { key: "timestamp", label: "Timestamp", render: r => formatDateTime(r.timestamp) },
  ];

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Governance" title="Audit logs" description="Review authorized administrative activity records." />
    {loading ? <Loading /> : <DataTable columns={columns} rows={rows} emptyTitle="No audit logs" />}
  </div>;
}