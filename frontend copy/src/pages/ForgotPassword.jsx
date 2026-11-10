import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Landmark, Mail } from "lucide-react";
import * as authApi from "@/services/api/auth";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try { await authApi.passwordReset(email); } catch {}
    setSent(true); setLoading(false);
  };

  return <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
    <div className="w-full max-w-md">
      <div className="mb-6 flex items-center justify-center gap-2 text-xl font-bold"><Landmark className="h-7 w-7 text-cyan-700" /> CivicOne</div>
      <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
        <h1 className="text-xl font-bold">Reset your password</h1>
        {sent ? <div className="mt-5 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700">If an account exists for that email, a reset link has been sent. Check your inbox.</div> :
        <form onSubmit={submit} className="mt-5 space-y-4">
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Email</label><div className="relative"><Mail className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input type="email" required value={email} onChange={e => setEmail(e.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm focus:border-cyan-500 focus:outline-none" /></div></div>
          <button type="submit" disabled={loading} className="w-full rounded-xl bg-cyan-700 py-2.5 font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{loading ? "Sending…" : "Send reset link"}</button>
        </form>}
        <p className="mt-5 text-center text-sm text-slate-500"><Link to="/login" className="font-medium text-cyan-700 hover:underline">← Back to sign in</Link></p>
      </div>
    </div>
  </div>;
}