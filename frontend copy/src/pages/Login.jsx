import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Landmark, Mail, Lock, ArrowRight } from "lucide-react";
import { useCivicAuth } from "@/contexts/CivicAuthContext";
import { roleHomePath } from "@/utils/civic";

export default function Login() {
  const { login } = useCivicAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const user = await login(email, password);
      navigate(roleHomePath(user.role), { replace: true });
    } catch (err) {
      setError(err.message || "Login failed. Check your credentials.");
    } finally { setLoading(false); }
  };

  return <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
    <div className="w-full max-w-md">
      <div className="mb-6 flex items-center justify-center gap-2 text-xl font-bold"><Landmark className="h-7 w-7 text-cyan-700" /> CivicOne</div>
      <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
        <h1 className="text-xl font-bold">Sign in to your workspace</h1>
        <p className="mt-1 text-sm text-slate-500">Access municipal services for your role.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Email</label>
            <div className="relative"><Mail className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input type="email" required value={email} onChange={e => setEmail(e.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm focus:border-cyan-500 focus:outline-none" placeholder="you@example.com" /></div>
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Password</label>
            <div className="relative"><Lock className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input type="password" required value={password} onChange={e => setPassword(e.target.value)} className="w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm focus:border-cyan-500 focus:outline-none" placeholder="••••••••" /></div>
          </div>
          {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
          <div className="flex items-center justify-between text-sm">
            <Link to="/register" className="font-medium text-cyan-700 hover:underline">Create account</Link>
            <Link to="/forgot-password" className="text-slate-500 hover:underline">Forgot password?</Link>
          </div>
          <button type="submit" disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-700 py-2.5 font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{loading ? "Signing in…" : <>Sign in <ArrowRight className="h-4 w-4" /></>}</button>
        </form>
        <p className="mt-5 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">Use your approved civic portal credentials to continue.</p>
      </div>
      <div className="mt-4 text-center"><Link to="/" className="text-sm text-slate-500 hover:underline">← Back to home</Link></div>
    </div>
  </div>;
}