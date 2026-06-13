import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import AdminLayout from "./components/layouts/AdminLayout";
import OperatorLayout from "./components/layouts/OperatorLayout";
import KioskLayout from "./components/layouts/KioskLayout";
import UserLayout from "./components/layouts/UserLayout";
import DisplayLayout from "./components/layouts/DisplayLayout";

import Dashboard from "./pages/admin/Dashboard";
import Counters from "./pages/admin/Counters";
import Operators from "./pages/admin/Operators";
import Services from "./pages/admin/Services";
import Displays from "./pages/admin/Displays";
import Analytics from "./pages/admin/Analytics";
import Settings from "./pages/admin/Settings";
import Migrations from "./pages/admin/Migrations";
import Terminal from "./pages/operator/Terminal";
import SelectService from "./pages/kiosk/SelectService";
import Details from "./pages/kiosk/Details";
import Success from "./pages/kiosk/Success";
import DisplayBoard from "./pages/display/DisplayBoard";
import Hub from "./pages/Hub";
import Login from "./pages/auth/Login";
import ProtectedRoute from "./components/auth/ProtectedRoute";

import JoinQueue from "./pages/public/JoinQueue";
import LiveStatus from "./pages/public/LiveStatus";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Hub / Landing */}
        <Route path="/" element={<Hub />} />
        
        {/* Auth */}
        <Route path="/admin/login" element={<Login />} />
        <Route path="/operator/login" element={<Login />} />
        <Route path="/login" element={<Navigate to="/admin/login" replace />} />

        {/* Admin Routes */}
        <Route path="/admin" element={<ProtectedRoute allowedRoles={["ADMIN"]}><AdminLayout /></ProtectedRoute>}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="counters" element={<Counters />} />
          <Route path="operators" element={<Operators />} />
          <Route path="services" element={<Services />} />
          <Route path="displays" element={<Displays />} />
          <Route path="display-setup" element={<Displays />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="migrations" element={<Migrations />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        {/* Operator Routes */}
        <Route path="/operator" element={<ProtectedRoute allowedRoles={["OPERATOR"]}><OperatorLayout /></ProtectedRoute>}>
          <Route index element={<Navigate to="terminal" replace />} />
          <Route path="terminal" element={<Terminal />} />
        </Route>

        {/* Kiosk Routes */}
        <Route path="/kiosk/:qr_slug" element={<KioskLayout />}>
          <Route index element={<Navigate to="select-service" replace />} />
          <Route path="select-service" element={<SelectService />} />
          <Route path="details" element={<Details />} />
          <Route path="success" element={<Success />} />
        </Route>

        {/* Display Board Routes */}
        <Route path="/display/:displayId" element={<DisplayLayout />}>
          <Route index element={<DisplayBoard />} />
        </Route>

        {/* User Queue Tracking Route (Light Claymorphism) */}
        <Route path="/mobile" element={<UserLayout />}>
          <Route path="joinQueue/:qr_slug" element={<JoinQueue />} />
          <Route path="status/:qr_slug/:token_number" element={<LiveStatus />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
