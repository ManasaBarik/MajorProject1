import React, { useEffect, useState } from "react";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import StatusBadge from "@/components/common/StatusBadge";
import Loading from "@/components/common/Loading";
import { formatDate } from "@/utils/civic";
import * as applicationsApi from "@/services/api/applications";

export default function AdminApplications() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { applicationsApi.listApplications().then(setRows).finally(() => setLoading(false)); }, []);

  const columns = [
    { key: "application_number", label: "App. no.", render: r => <span className="font-medium text-slate-800">{r.application_number}</span> },
    { key: "service", label: "Service", render: r => r.service?.name || "Unassigned" },
    { key: "applicant_name", label: "Applicant" },
    { key: "department", label: "Department", render: r => r.department?.name || "Unassigned" },
    { key: "status", label: "Status", render: r => <StatusBadge status={r.status} /> },
    { key: "submitted_at", label: "Submitted", render: r => formatDate(r.submitted_at) },
  ];

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Service operations" title="All applications" description="Monitor municipal service application workflows." />
    {loading ? <Loading /> : <DataTable columns={columns} rows={rows} emptyTitle="No applications" />}
  </div>;
}