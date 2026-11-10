import React, { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { priorityColor } from "@/utils/civic";

const FILL = { LOW: "#64748b", MEDIUM: "#3b82f6", HIGH: "#f97316", CRITICAL: "#ef4444" };

function Recenter({ center }) {
  const map = useMap();
  useEffect(() => { if (center) map.setView(center); }, [center, map]);
  return null;
}

function MapClickHandler({ onPick }) {
  useMapEvents({
    click: event => onPick?.([
      Number(event.latlng.lat.toFixed(6)),
      Number(event.latlng.lng.toFixed(6)),
    ]),
  });
  return null;
}

export default function MapView({ points = [], center = [20.2961, 85.8245], height = 420, onPick, picked }) {
  return <div className="overflow-hidden rounded-2xl border border-slate-200" style={{ height }}>
    <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
      <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {onPick && <MapClickHandler onPick={onPick} />}
      <Recenter center={picked || center} />
      {picked && <CircleMarker center={picked} radius={10} pathOptions={{ color: "#0891b2", fillColor: "#0891b2", fillOpacity: 0.6 }}><Popup>Selected location</Popup></CircleMarker>}
      {points.map(p => <CircleMarker key={p.id} center={[p.latitude, p.longitude]} radius={p.intensity ? 6 + p.intensity * 14 : 7} pathOptions={{ color: FILL[p.priority] || "#64748b", fillColor: FILL[p.priority] || "#64748b", fillOpacity: p.intensity ? 0.4 : 0.7 }} eventHandlers={onPick ? { click: () => onPick([p.latitude, p.longitude]) } : undefined}>
        <Popup>{p.category ? `${p.category} · ${p.priority || ""}` : "Complaint"}{p.ward ? `<br/>${p.ward}` : ""}{p.status ? `<br/>${p.status}` : ""}</Popup>
      </CircleMarker>)}
    </MapContainer>
  </div>;
}