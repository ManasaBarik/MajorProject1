import React, { useEffect, useState } from "react";
import { BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import PageHeader from "@/components/common/PageHeader";
import StatCard from "@/components/common/StatCard";
import SectionCard from "@/components/common/SectionCard";
import Loading from "@/components/common/Loading";
import { MessageSquareWarning, CheckCircle2, Clock, AlertTriangle } from "lucide-react";
import * as analyticsApi from "@/services/api/analytics";

const PIE_COLORS = ["#0891b2","#3b82f6","#f97316","#10b981","#a855f7","#ef4444","#64748b","#eab308"];

export default function AdminAnalytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([analyticsApi.getOverview(), analyticsApi.getComplaintCategories(), analyticsApi.getComplaintDepartments(), analyticsApi.getComplaintWards(), analyticsApi.getComplaintTrends()])
      .then(([overview, categories, departments, wards, trends]) => ({ overview, categories, departments, wards, trends }))
      .then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="px-5 py-8 sm:px-8"><Loading /></div>;
  const o = data.overview;

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="Performance" title="Analytics" description="Review complaint, department, category, ward, and trend analytics." />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Total complaints" value={o.total_complaints} icon={MessageSquareWarning} tone="cyan" />
      <StatCard label="Open" value={o.open_complaints} icon={Clock} tone="amber" />
      <StatCard label="Resolved" value={o.resolved_complaints} icon={CheckCircle2} tone="emerald" />
      <StatCard label="Overdue" value={o.overdue_complaints} icon={AlertTriangle} tone="rose" />
    </div>
    <div className="mt-6 grid gap-6 lg:grid-cols-2">
      <SectionCard title="Complaint trends" description="Monthly complaints vs. resolved.">
        <div style={{ height: 280 }}><ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.trends}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="month" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} /><Tooltip /><Legend /><Line type="monotone" dataKey="complaints" stroke="#0891b2" strokeWidth={2} /><Line type="monotone" dataKey="resolved" stroke="#10b981" strokeWidth={2} /></LineChart>
        </ResponsiveContainer></div>
      </SectionCard>
      <SectionCard title="By category" description="Complaint distribution across categories.">
        <div style={{ height: 280 }}><ResponsiveContainer width="100%" height="100%">
          <PieChart><Pie data={data.categories} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={90} label>{data.categories.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart>
        </ResponsiveContainer></div>
      </SectionCard>
      <SectionCard title="By department" description="Complaint load per department.">
        <div style={{ height: 280 }}><ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.departments}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="department" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 12 }} /><Tooltip /><Bar dataKey="count" fill="#0891b2" radius={[4,4,0,0]} /></BarChart>
        </ResponsiveContainer></div>
      </SectionCard>
      <SectionCard title="By ward" description="Complaint distribution across wards.">
        <div style={{ height: 280 }}><ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.wards}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="ward" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 12 }} /><Tooltip /><Bar dataKey="count" fill="#6366f1" radius={[4,4,0,0]} /></BarChart>
        </ResponsiveContainer></div>
      </SectionCard>
    </div>
  </div>;
}