import React from "react";
import { LayoutDashboard, MessageSquareWarning, BriefcaseBusiness, Users, User } from "lucide-react";
import AppShell from "@/components/common/AppShell";

const navItems = [
  { label: "Dashboard", path: "/officer/dashboard", icon: LayoutDashboard },
  { label: "Complaints", path: "/officer/complaints", icon: MessageSquareWarning },
  { label: "Applications", path: "/officer/applications", icon: BriefcaseBusiness },
  { label: "Engineers", path: "/officer/engineers", icon: Users },
  { label: "Profile", path: "/officer/profile", icon: User },
];

export default function OfficerLayout() { return <AppShell section="Officer" navItems={navItems} />; }