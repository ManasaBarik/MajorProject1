import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Landmark } from "lucide-react";
import { useCivicAuth } from "@/contexts/CivicAuthContext";
import { roleHomePath } from "@/utils/civic";

export default function Register() {
  const { register } = useCivicAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "", role: "CITIZEN" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirm) { setError("Passwords do not match."); return; }
    setLoading(true);
    try {
      await register({ name: form.name, email: form.email, password: form.password, role: form.role });
      navigate("/login", { replace: true });
    } catch (err) { setError(err.message || "Registration failed."); }
    finally { setLoading(false); }
  };

  return <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-8">
    <div className="w-full max-w-md">
      <div className="mb-6 flex items-center justify-center gap-2 text-xl font-bold"><Landmark className="h-7 w-7 text-cyan-700" /> CivicOne</div>
      <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
        <h1 className="text-xl font-bold">Create your account</h1>
        <form onSubmit={submit} className="mt-5 space-y-4">
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Full name</label><input required value={form.name} onChange={e => set("name", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Email</label><input type="email" required value={form.email} onChange={e => set("email", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Account type</label>
            <select value={form.role} onChange={e => set("role", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none">
              <option value="CITIZEN">Citizen</option>
              <option value="BUSINESS_OWNER">Business Owner</option>
            </select>
          </div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Password</label><input type="password" required value={form.password} onChange={e => set("password", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Confirm password</label><input type="password" required value={form.confirm} onChange={e => set("confirm", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" /></div>
          {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
          <button type="submit" disabled={loading} className="w-full rounded-xl bg-cyan-700 py-2.5 font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{loading ? "Creating…" : "Create account"}</button>
        </form>
        <p className="mt-5 text-center text-sm text-slate-500">Already have an account? <Link to="/login" className="font-medium text-cyan-700 hover:underline">Sign in</Link></p>
      </div>
    </div>
  </div>;
}