import React from "react";
import { ArrowRight, BriefcaseBusiness, Construction, Megaphone } from "lucide-react";
import { Link } from "react-router-dom";
import { workflows, isWorkflowAvailable } from "@/utils/workflows";

export default function WorkflowChooser({ basePath }) {
  const complaintsEnabled = isWorkflowAvailable("complaints");
  const complaintsRoutable = complaintsEnabled && basePath === "/citizen";
  return <section aria-labelledby="workflow-chooser-title" className="mb-6">
    <div className="mb-3">
      <p className="text-xs font-semibold uppercase text-cyan-800">Start here</p>
      <h2 id="workflow-chooser-title" className="mt-1 text-lg font-semibold text-slate-900">Choose a workflow</h2>
    </div>
    <div className="grid gap-3 md:grid-cols-2">
      {complaintsRoutable
        ? <Link to={`${basePath}/complaints`} className="group flex min-h-36 items-start justify-between gap-4 rounded-lg border border-indigo-200 bg-indigo-50 p-5 text-indigo-950 transition-colors hover:bg-indigo-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2">
            <div className="flex items-start gap-4">
              <span className="rounded-md bg-indigo-100 p-2.5"><Megaphone className="h-5 w-5 text-indigo-700" /></span>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold">{workflows.complaints.title}</h3>
                  <span className="rounded bg-emerald-200 px-2 py-1 text-xs font-semibold text-emerald-950">Available</span>
                </div>
                <p className="mt-2 text-sm text-indigo-800">Report civic issues and track their resolution.</p>
                <span className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-indigo-800">Report an issue <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></span>
              </div>
            </div>
          </Link>
        : !complaintsEnabled
          ? <div aria-disabled="true" className="flex min-h-36 items-start gap-4 rounded-lg border border-slate-200 bg-slate-50 p-5 text-slate-500">
              <span className="rounded-md bg-slate-200 p-2.5"><Construction className="h-5 w-5" /></span>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold text-slate-700">{workflows.complaints.title}</h3>
                  <span className="rounded bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-900">Coming soon</span>
                </div>
                <p className="mt-2 text-sm">{workflows.complaints.message || "This workflow is not available yet."}</p>
              </div>
            </div>
          : null}
      <Link to={`${basePath}/services`} className="group flex min-h-36 items-start justify-between gap-4 rounded-lg border border-cyan-800 bg-cyan-950 p-5 text-white transition-colors hover:bg-cyan-900 focus:outline-none focus:ring-2 focus:ring-cyan-700 focus:ring-offset-2">
        <div className="flex items-start gap-4">
          <span className="rounded-md bg-white/10 p-2.5"><BriefcaseBusiness className="h-5 w-5" /></span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold">{workflows.services.title}</h3>
              <span className="rounded bg-emerald-200 px-2 py-1 text-xs font-semibold text-emerald-950">Available</span>
            </div>
            <p className="mt-2 text-sm text-cyan-100">Browse services, submit applications, and track decisions.</p>
            <span className="mt-4 inline-flex items-center gap-2 text-sm font-semibold">Select required services <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></span>
          </div>
        </div>
      </Link>
    </div>
  </section>;
}
