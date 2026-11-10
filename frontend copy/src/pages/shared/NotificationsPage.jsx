import React, { useEffect, useState } from "react";
import { CheckCheck } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import Loading from "@/components/common/Loading";
import EmptyState from "@/components/common/EmptyState";
import { timeAgo } from "@/utils/civic";
import * as notificationsApi from "@/services/api/notifications";

export default function NotificationsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const load = () => { setLoading(true); notificationsApi.listNotifications().then(setItems).finally(() => setLoading(false)); };
  useEffect(load, []);
  const markAll = async () => { await notificationsApi.markAllNotificationsRead(); load(); };
  const markOne = async (id) => { await notificationsApi.markNotificationRead(id); load(); };

  return <div className="mx-auto max-w-3xl px-5 py-8 sm:px-8">
    <PageHeader eyebrow="Updates" title="Notifications" description="Official updates about your complaints and applications." action={
      <button onClick={markAll} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"><CheckCheck className="h-4 w-4" /> Mark all read</button>} />
    {loading ? <Loading /> : items.length ? <div className="space-y-3">{items.map(n => <button key={n.id} onClick={() => markOne(n.id)} className={`flex w-full items-start gap-3 rounded-2xl border px-4 py-3 text-left ${n.read ? "border-slate-200 bg-white" : "border-cyan-200 bg-cyan-50/50"}`}>
      <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read ? "bg-slate-300" : "bg-cyan-600"}`} />
      <div className="flex-1"><p className="text-sm font-medium text-slate-800">{n.title}</p><p className="text-sm text-slate-500">{n.message}</p><p className="mt-1 text-xs text-slate-400">{timeAgo(n.created_at)}</p></div>
    </button>)}</div> : <EmptyState title="No notifications" message="You're all caught up." />}
  </div>;
}