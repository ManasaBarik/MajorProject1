import React from "react";
import { Landmark, ArrowRight, ShieldCheck, Languages } from "lucide-react";
import { Link, Navigate } from "react-router-dom";
import { useCivicAuth } from "@/contexts/CivicAuthContext";
import { roleHomePath } from "@/utils/civic";

export default function Home() {
  const { user, loading } = useCivicAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center bg-slate-950"><div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-700 border-t-cyan-400" /></div>;
  if (user) return <Navigate to={roleHomePath(user.role)} replace />;
  return <main className="min-h-screen bg-slate-950 text-white">
    <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8"><div className="flex items-center gap-2 font-bold"><Landmark className="h-6 w-6 text-cyan-400" /> CivicOne</div><Link to="/login" className="rounded-xl border border-white/20 px-4 py-2 text-sm font-semibold hover:bg-white/10">Sign in</Link></nav>
    <section className="mx-auto grid max-w-7xl gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[1.15fr_.85fr] lg:py-28">
      <div><p className="mb-5 text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">Unified municipal services</p><h1 className="max-w-3xl text-5xl font-bold leading-[1.08] tracking-tight sm:text-6xl">Your city services, in one clear place.</h1><p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">Report civic issues, apply for municipal services, track progress, and stay informed through one accessible platform.</p><Link to="/login" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-400">Open your workspace <ArrowRight className="h-4 w-4" /></Link></div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1"><div className="rounded-3xl border border-white/10 bg-white/5 p-6"><ShieldCheck className="h-7 w-7 text-cyan-400" /><h2 className="mt-5 text-xl font-semibold">Accountable by design</h2><p className="mt-2 text-sm leading-6 text-slate-300">Track complaints and applications through every official stage.</p></div><div className="rounded-3xl border border-white/10 bg-white/5 p-6"><Languages className="h-7 w-7 text-cyan-400" /><h2 className="mt-5 text-xl font-semibold">Built for everyone</h2><p className="mt-2 text-sm leading-6 text-slate-300">Clear, responsive access for citizens, businesses, officers, and administrators.</p></div></div>
    </section>
  </main>;
}