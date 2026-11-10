import React from "react";
import { LayoutDashboard, MessageSquareWarning, BriefcaseBusiness, Bell, User, Bot, Building2 } from "lucide-react";
import AppShell from "@/components/common/AppShell";

const navItems = [
  { label: "Dashboard", path: "/citizen/dashboard", icon: LayoutDashboard },
  { label: "Complaints", path: "/citizen/complaints", icon: MessageSquareWarning },
  { label: "Services", path: "/citizen/services", icon: Building2 },
  { label: "Applications", path: "/citizen/applications", icon: BriefcaseBusiness },
  { label: "Notifications", path: "/citizen/notifications", icon: Bell },
  { label: "Civic assistant", path: "/citizen/chat", icon: Bot },
  { label: "Profile", path: "/citizen/profile", icon: User },
];

export default function CitizenLayout() { return <AppShell section="Citizen" navItems={navItems} />; }