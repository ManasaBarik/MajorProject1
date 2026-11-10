import React from "react";
import { Construction } from "lucide-react";
import { Outlet } from "react-router-dom";
import { isWorkflowAvailable, workflows } from "@/utils/workflows";

export default function WorkflowGate({ workflow }) {
  if (isWorkflowAvailable(workflow)) return <Outlet />;

  const config = workflows[workflow];
  return <main className="mx-auto max-w-3xl px-5 py-16 sm:px-8">
    <div className="border-l-4 border-amber-500 bg-amber-50 p-6">
      <Construction className="h-7 w-7 text-amber-800" />
      <p className="mt-4 text-xs font-semibold uppercase text-amber-900">Coming soon</p>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">{config?.title || "Workflow"}</h1>
      <p className="mt-2 text-sm leading-6 text-slate-700">This workflow is under maintenance and is not available yet.</p>
    </div>
  </main>;
}