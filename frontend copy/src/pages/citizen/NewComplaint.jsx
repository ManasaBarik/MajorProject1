import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MapPin, Crosshair } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import MapView from "@/components/common/MapView";
import * as complaintsApi from "@/services/api/complaints";

export default function NewComplaint() {
  const defaultLocation = [20.2961, 85.8245];
  const navigate = useNavigate();
  const [form, setForm] = useState({ title: "", description: "", category: "", address: "" });
  const [location, setLocation] = useState(defaultLocation);
  const [image, setImage] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState("");
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    complaintsApi.listComplaintCategories().then(setCategories).catch(err => setError(err.message));
  }, []);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const useMyLocation = () => {
    if (!navigator.geolocation) { setError("Location is not supported by this browser."); return; }
    setError("");
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      pos => {
        setLocation([
          Number(pos.coords.latitude.toFixed(6)),
          Number(pos.coords.longitude.toFixed(6)),
        ]);
        setLocating(false);
      },
      err => { setError(err.message || "Could not fetch your location."); setLocating(false); },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.title || !form.description) { setError("Title and description are required."); return; }
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("title", form.title);
      fd.append("description", form.description);
      if (form.category) fd.append("category", form.category);
      if (location) {
        fd.append("latitude", Number(location[0]).toFixed(6));
        fd.append("longitude", Number(location[1]).toFixed(6));
      }
      fd.append("address", form.address);
      if (image) fd.append("image", image);
      await complaintsApi.createComplaint(fd);
      navigate("/citizen/complaints");
    } catch (err) { setError(err.message || "Could not submit complaint."); }
    finally { setSubmitting(false); }
  };

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="New complaint" title="Report a civic issue" description="Describe the issue and mark its location. A municipal officer will review and classify your report." />
    <form onSubmit={submit} className="grid gap-6 lg:grid-cols-[1fr_1fr]">
      <SectionCard title="Issue details">
        <div className="space-y-4">
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Title *</label><input value={form.title} onChange={e => set("title", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" placeholder="Short summary of the issue" /></div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Description *</label><textarea rows={5} value={form.description} onChange={e => set("description", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" placeholder="Describe what is happening, since when, and any impact" /></div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Category <span className="text-slate-400">(optional)</span></label>
            <select value={form.category} onChange={e => set("category", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none">
              <option value="">Select category</option>{categories.map(c => <option key={c} value={c}>{c.replaceAll("_", " ")}</option>)}
            </select>
          </div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Address</label><input value={form.address} onChange={e => set("address", e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-cyan-500 focus:outline-none" placeholder="Street, area, landmark" /></div>
          <div><label className="mb-1.5 block text-sm font-medium text-slate-700">Photo (optional)</label><input type="file" accept="image/*" onChange={e => setImage(e.target.files[0])} className="w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2" /></div>
        </div>
      </SectionCard>
      <div className="space-y-6">
        <SectionCard title="Location" description="Click on the map to mark the issue spot, or use your current location." actions={<div className="flex items-center gap-3"><span className="flex items-center gap-1.5 text-xs text-slate-500"><MapPin className="h-3.5 w-3.5" /> {location ? `${location[0].toFixed(4)}, ${location[1].toFixed(4)}` : "Not set"}</span><button type="button" onClick={useMyLocation} disabled={locating} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"><Crosshair className="h-3.5 w-3.5" /> {locating ? "Locating…" : "Use my location"}</button></div>}>
          <MapView height={360} onPick={setLocation} picked={location} />
        </SectionCard>
        {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
        <button type="submit" disabled={submitting} className="w-full rounded-xl bg-cyan-700 py-3 font-semibold text-white hover:bg-cyan-800 disabled:opacity-60">{submitting ? "Submitting…" : "Submit complaint"}</button>
      </div>
    </form>
  </div>;
}