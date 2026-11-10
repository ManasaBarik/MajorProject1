import React from "react";
import EmptyState from "./EmptyState";
import Loading from "./Loading";

export default function DataTable({ columns, rows, loading, rowKey = "id", onRowClick, emptyTitle }) {
  if (loading) return <Loading />;
  if (!rows?.length) return <EmptyState title={emptyTitle || "No records to show"} />;
  return <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
    <table className="w-full text-left text-sm">
      <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
        <tr>{columns.map(col => <th key={col.key} className="px-4 py-3 font-semibold">{col.label}</th>)}</tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {rows.map(row => <tr key={row[rowKey]} onClick={() => onRowClick?.(row)} className={`hover:bg-slate-50 ${onRowClick ? "cursor-pointer" : ""}`}>
          {columns.map(col => <td key={col.key} className="px-4 py-3 align-top">{col.render ? col.render(row) : row[col.key]}</td>)}
        </tr>)}
      </tbody>
    </table>
  </div>;
}
