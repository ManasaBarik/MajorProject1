import React from "react";
import { LayoutDashboard, BriefcaseBusiness, Bell, User, Bot, Building2 } from "lucide-react";
import AppShell from "@/components/common/AppShell";

const navItems = [
  { label: "Dashboard", path: "/business/dashboard", icon: LayoutDashboard },
  { label: "Business profile", path: "/business/profile", icon: User },
  { label: "Services", path: "/business/services", icon: Building2 },
  { label: "Applications", path: "/business/applications", icon: BriefcaseBusiness },
  { label: "Notifications", path: "/business/notifications", icon: Bell },
  { label: "Civic assistant", path: "/business/chat", icon: Bot },
];

export default function BusinessLayout() { return <AppShell section="Business" navItems={navItems} />; }