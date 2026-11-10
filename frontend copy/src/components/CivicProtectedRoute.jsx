import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useCivicAuth } from "@/contexts/CivicAuthContext";

export default function CivicProtectedRoute() {
  const { user, loading } = useCivicAuth();
  if (loading) {
    return <div className="flex min-h-screen items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-cyan-700" /></div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}