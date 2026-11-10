import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Landmark } from "lucide-react";
import * as authApi from "@/services/api/auth";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (password !== confirm) { setError("Passwords do not match."); return; }
    setLoading(true);
    try { await authApi.passwordResetConfirm(token, password); navigate("/login", { replace: true }); }
    catch (err) { setError(err.message || "Reset failed."); }
    finally { setLoading(false); }
  };

  return <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
    <div className="w-full max-w-md">
      <div className="mb-6 flex items-center justify-center gap-2 text-xl font-bold"><Landmark className="h-7 w-7 text-cyan-700" /> CivicOne</div>
      <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
        <h1 className="text-xl font-bold">Set a new password</h1>
        <form onSubmit={submit} className="mt-5 space-y-4">
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">New password</label><input type="password" required value={password} onChange={e => setPassword(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Confirm password</label><input type="password" required value={confirm} onChange={e => setConfirm(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>
          {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
          <button type="submit" disabled={loading} className="w-full rounded-xl bg-cyan-700 py-2.5 font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{loading ? "Resetting…" : "Reset password"}</button>
        </form>
        <p className="mt-5 text-center text-sm text-slate-500"><Link to="/login" className="font-medium text-cyan-700 hover:underline">← Back to sign in</Link></p>
      </div>
    </div>
  </div>;
}