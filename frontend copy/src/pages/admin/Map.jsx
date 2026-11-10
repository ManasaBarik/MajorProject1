import React, { useEffect, useState } from "react";
import { Flame, MapPin } from "lucide-react";
import PageHeader from "@/components/common/PageHeader";
import SectionCard from "@/components/common/SectionCard";
import MapView from "@/components/common/MapView";
import Loading from "@/components/common/Loading";
import * as analyticsApi from "@/services/api/analytics";

export default function AdminMap() {
  const [points, setPoints] = useState([]);
  const [heatmap, setHeatmap] = useState([]);
  const [showHeat, setShowHeat] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([analyticsApi.getMapComplaints(), analyticsApi.getHeatmap()])
      .then(([p, h]) => { setPoints(p); setHeatmap(h); }).finally(() => setLoading(false));
  }, []);

  const display = showHeat ? heatmap.map(h => ({ id: `${h.lat},${h.lng}`, latitude: h.lat, longitude: h.lng, intensity: h.intensity, category: "", priority: "", ward: "", status: "" })) : points;

  return <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
    <PageHeader eyebrow="GIS" title="Civic issue map" description="View privacy-safe complaint locations, priority patterns, and recurring problem areas." action={
      <button onClick={() => setShowHeat(v => !v)} className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold ${showHeat ? "bg-orange-600 text-white" : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"}`}><Flame className="h-4 w-4" /> {showHeat ? "Showing heatmap" : "Show heatmap"}</button>} />
    {loading ? <Loading /> : <SectionCard title={showHeat ? "Heatmap" : "Complaint locations"} description={showHeat ? "Recurring problem areas shown by intensity. No private user information is exposed." : "Each marker is a reported civic issue. Click a marker for details."}>
      <MapView points={display} height={520} />
    </SectionCard>}
    <p className="mt-4 flex items-center gap-1.5 text-xs text-slate-400"><MapPin className="h-3.5 w-3.5" /> Map data © OpenStreetMap contributors. Locations are approximate to protect privacy.</p>
  </div>;
}