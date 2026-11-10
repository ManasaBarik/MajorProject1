import React from "react";
import { LayoutDashboard, Users, Building2, LayoutGrid, MessageSquareWarning, BriefcaseBusiness, BarChart3, Map, ScrollText } from "lucide-react";
import AppShell from "@/components/common/AppShell";

const navItems = [
  { label: "Dashboard", path: "/admin/dashboard", icon: LayoutDashboard },
  { label: "Users", path: "/admin/users", icon: Users },
  { label: "Departments", path: "/admin/departments", icon: Building2 },
  { label: "Services", path: "/admin/services", icon: LayoutGrid },
  { label: "Complaints", path: "/admin/complaints", icon: MessageSquareWarning },
  { label: "Applications", path: "/admin/applications", icon: BriefcaseBusiness },
  { label: "Analytics", path: "/admin/analytics", icon: BarChart3 },
  { label: "Map", path: "/admin/map", icon: Map },
  { label: "Audit logs", path: "/admin/audit-logs", icon: ScrollText },
];

export default function AdminLayout() { return <AppShell section="Administrator" navItems={navItems} />; }