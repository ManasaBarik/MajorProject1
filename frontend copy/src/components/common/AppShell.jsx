import React, { useState } from "react";
import { Menu, X, Landmark, LogOut } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useCivicAuth } from "@/contexts/CivicAuthContext";

export default function AppShell({ section, navItems }) {
  const [open, setOpen] = useState(false);
  const { logout } = useCivicAuth();
  const navigate = useNavigate();
  const linkClass = ({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${isActive ? "bg-cyan-50 text-cyan-800" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"}`;
  return <div className="min-h-screen bg-slate-50 text-slate-950">
    <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center border-b border-slate-200 bg-white/95 px-4 backdrop-blur lg:hidden">
      <button onClick={() => setOpen(true)} aria-label="Open navigation" className="rounded-lg p-2 hover:bg-slate-100"><Menu className="h-5 w-5" /></button>
      <div className="ml-3 flex items-center gap-2 font-semibold"><Landmark className="h-5 w-5 text-cyan-700" /> CivicOne</div>
    </header>
    {open && <button aria-label="Close navigation overlay" className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden" onClick={() => setOpen(false)} />}
    <aside className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white p-5 transition-transform lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
      <div className="mb-8 flex items-center justify-between"><div><div className="flex items-center gap-2 text-lg font-bold"><Landmark className="h-6 w-6 text-cyan-700" /> CivicOne</div><p className="mt-1 text-xs text-slate-500">{section} workspace</p></div><button onClick={() => setOpen(false)} aria-label="Close navigation" className="p-2 lg:hidden"><X className="h-5 w-5" /></button></div>
      <nav className="flex-1 space-y-1">{navItems.map(({ label, path, icon: Icon }) => <NavLink key={path} to={path} className={linkClass} onClick={() => setOpen(false)}><Icon className="h-4 w-4" />{label}</NavLink>)}</nav>
      <button onClick={() => { logout(); navigate("/login"); }} className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100"><LogOut className="h-4 w-4" /> Sign out</button>
    </aside>
    <main className="min-h-screen pt-16 lg:ml-72 lg:pt-0"><Outlet /></main>
  </div>;
}
