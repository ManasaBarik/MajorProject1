import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import StatusBadge from "@/components/common/StatusBadge";
import Loading from "@/components/common/Loading";
import { formatDate } from "@/utils/civic";
import * as applicationsApi from "@/services/api/applications";

export default function OfficerApplications() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  useEffect(() => { applicationsApi.listAssignedApplications().then(setRows).finally(() => setLoading(false)); }, []);

  const columns = [
    { key: "application_number", label: "App. no.", render: r => <span className="font-medium text-slate-800">{r.application_number}</span> },
    { key: "service", label: "Service", render: r => r.service?.name || "Unassigned" },
    { key: "applicant_name", label: "Applicant", render: r => <div><p>{r.applicant_name}</p>{r.business_name && <p className="text-xs text-slate-500">{r.business_name}</p>}</div> },
    { key: "department", label: "Department", render: r => r.department?.name || "—" },
    { key: "status", label: "Status", render: r => <StatusBadge status={r.status} /> },
    { key: "assigned_officer", label: "Assigned officer", render: r => r.assigned_officer?.name || <span className="font-medium text-amber-800">Unassigned</span> },
    { key: "submitted_at", label: "Submitted", render: r => formatDate(r.submitted_at) },
  ];

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Service operations" title="Department application queue" description="Review applications assigned to you and unassigned applications from your department." />
    {loading ? <Loading /> : <DataTable columns={columns} rows={rows} onRowClick={r => navigate(`/officer/applications/${r.id}`)} emptyTitle="No applications in your department queue" />}
  </div>;
}