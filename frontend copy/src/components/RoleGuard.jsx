import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useCivicAuth } from "@/contexts/CivicAuthContext";
import { roleHomePath } from "@/utils/civic";

export default function RoleGuard({ roles }) {
  const { user } = useCivicAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) return <Navigate to={roleHomePath(user.role)} replace />;
  return <Outlet />;
}