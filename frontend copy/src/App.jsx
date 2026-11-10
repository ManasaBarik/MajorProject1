import { Toaster } from "@/components/ui/toaster";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClientInstance } from "@/lib/query-client";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import PageNotFound from "./lib/PageNotFound";
import ScrollToTop from "./components/ScrollToTop";
import { CivicAuthProvider } from "@/contexts/CivicAuthContext";
import CivicProtectedRoute from "@/components/CivicProtectedRoute";
import RoleGuard from "@/components/RoleGuard";
import WorkflowGate from "@/components/common/WorkflowGate";

import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import Home from "@/pages/Home";

import CitizenLayout from "@/layouts/CitizenLayout/CitizenLayout";
import BusinessLayout from "@/layouts/BusinessLayout/BusinessLayout";
import OfficerLayout from "@/layouts/OfficerLayout/OfficerLayout";
import AdminLayout from "@/layouts/AdminLayout/AdminLayout";

import CitizenDashboard from "@/pages/citizen/Dashboard";
import CitizenComplaints from "@/pages/citizen/Complaints";
import NewComplaint from "@/pages/citizen/NewComplaint";
import CitizenComplaintDetail from "@/pages/citizen/ComplaintDetail";
import CitizenServices from "@/pages/citizen/Services";
import CitizenApplications from "@/pages/citizen/Applications";
import CitizenApplicationDetail from "@/pages/citizen/ApplicationDetail";
import CitizenNotifications from "@/pages/citizen/Notifications";
import CitizenProfile from "@/pages/citizen/Profile";
import CitizenChat from "@/pages/citizen/Chat";

import BusinessDashboard from "@/pages/business/Dashboard";
import BusinessProfile from "@/pages/business/Profile";
import BusinessServices from "@/pages/business/Services";
import BusinessApplications from "@/pages/business/Applications";
import BusinessApplicationDetail from "@/pages/business/ApplicationDetail";
import BusinessNotifications from "@/pages/business/Notifications";
import BusinessChat from "@/pages/business/Chat";

import OfficerDashboard from "@/pages/officer/Dashboard";
import OfficerComplaints from "@/pages/officer/Complaints";
import OfficerComplaintDetail from "@/pages/officer/ComplaintDetail";
import OfficerApplications from "@/pages/officer/Applications";
import OfficerApplicationDetail from "@/pages/officer/ApplicationDetail";
import OfficerEngineers from "@/pages/officer/Engineers";
import OfficerProfile from "@/pages/officer/Profile";

import AdminDashboard from "@/pages/admin/Dashboard";
import AdminUsers from "@/pages/admin/Users";
import AdminDepartments from "@/pages/admin/Departments";
import AdminServices from "@/pages/admin/Services";
import AdminComplaints from "@/pages/admin/Complaints";
import AdminApplications from "@/pages/admin/Applications";
import AdminAnalytics from "@/pages/admin/Analytics";
import AdminMap from "@/pages/admin/Map";
import AdminAuditLogs from "@/pages/admin/AuditLogs";

const AuthenticatedApp = () => {
  return (
    <CivicAuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/" element={<Home />} />

        <Route element={<CivicProtectedRoute />}>
          <Route element={<RoleGuard roles={["CITIZEN"]} />}>
            <Route element={<CitizenLayout />}>
              <Route path="/citizen/dashboard" element={<CitizenDashboard />} />
              <Route element={<WorkflowGate workflow="complaints" />}>
                <Route path="/citizen/complaints" element={<CitizenComplaints />} />
                <Route path="/citizen/complaints/new" element={<NewComplaint />} />
                <Route path="/citizen/complaints/:id" element={<CitizenComplaintDetail />} />
              </Route>
              <Route path="/citizen/services" element={<CitizenServices />} />
              <Route path="/citizen/applications" element={<CitizenApplications />} />
              <Route path="/citizen/applications/:id" element={<CitizenApplicationDetail />} />
              <Route path="/citizen/notifications" element={<CitizenNotifications />} />
              <Route path="/citizen/profile" element={<CitizenProfile />} />
              <Route path="/citizen/chat" element={<CitizenChat />} />
            </Route>
          </Route>

          <Route element={<RoleGuard roles={["BUSINESS_OWNER"]} />}>
            <Route element={<BusinessLayout />}>
              <Route path="/business/dashboard" element={<BusinessDashboard />} />
              <Route path="/business/profile" element={<BusinessProfile />} />
              <Route path="/business/services" element={<BusinessServices />} />
              <Route path="/business/applications" element={<BusinessApplications />} />
              <Route path="/business/applications/new" element={<BusinessApplicationDetail />} />
              <Route path="/business/applications/:id" element={<BusinessApplicationDetail />} />
              <Route path="/business/notifications" element={<BusinessNotifications />} />
              <Route path="/business/chat" element={<BusinessChat />} />
            </Route>
          </Route>

          <Route element={<RoleGuard roles={["OFFICER", "ENGINEER"]} />}>
            <Route element={<OfficerLayout />}>
              <Route path="/officer/dashboard" element={<OfficerDashboard />} />
              <Route path="/officer/complaints" element={<OfficerComplaints />} />
              <Route path="/officer/complaints/:id" element={<OfficerComplaintDetail />} />
              <Route path="/officer/applications" element={<OfficerApplications />} />
              <Route path="/officer/applications/:id" element={<OfficerApplicationDetail />} />
              <Route path="/officer/engineers" element={<OfficerEngineers />} />
              <Route path="/officer/profile" element={<OfficerProfile />} />
            </Route>
          </Route>

          <Route element={<RoleGuard roles={["ADMINISTRATOR"]} />}>
            <Route element={<AdminLayout />}>
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
              <Route path="/admin/users" element={<AdminUsers />} />
              <Route path="/admin/departments" element={<AdminDepartments />} />
              <Route path="/admin/services" element={<AdminServices />} />
              <Route path="/admin/complaints" element={<AdminComplaints />} />
              <Route path="/admin/applications" element={<AdminApplications />} />
              <Route path="/admin/analytics" element={<AdminAnalytics />} />
              <Route path="/admin/map" element={<AdminMap />} />
              <Route path="/admin/audit-logs" element={<AdminAuditLogs />} />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<PageNotFound />} />
      </Routes>
    </CivicAuthProvider>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClientInstance}>
      <Router>
        <ScrollToTop />
        <AuthenticatedApp />
      </Router>
      <Toaster />
    </QueryClientProvider>
  );
}

export default App;