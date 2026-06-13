import { Outlet, Link, useNavigate } from "react-router-dom";
import { LayoutDashboard, Users, Monitor, Settings, MonitorSpeaker, LineChart, LogOut, ArrowRightLeft, Bell } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

export default function AdminLayout() {
  const navigate = useNavigate();
  const logout = useAuthStore(state => state.logout);

  const handleLogout = () => {
    logout();
    navigate("/admin/login");
  };
  return (
    <div className="theme-operations dark flex h-screen w-full font-sans antialiased selection:bg-[#4ADE80] selection:text-black bg-[#09090B] text-white">
      {/* Sidebar */}
      <aside className="w-64 border-r border-white/5 bg-[#000000] flex flex-col">
        <div className="p-6 border-b border-white/5">
          <h1 className="text-xl font-bold tracking-tight text-white">QueueMind Admin</h1>
        </div>
        <nav className="flex-1 p-4 space-y-2">
          <Link to="/admin/dashboard" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#111113] text-sm font-medium text-[#A1A1AA] hover:text-white transition-colors">
            <LayoutDashboard className="w-4 h-4" /> Dashboard
          </Link>
          <Link to="/admin/counters" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#111113] text-sm font-medium text-[#A1A1AA] hover:text-white transition-colors">
            <Monitor className="w-4 h-4" /> Counters
          </Link>
          <Link to="/admin/operators" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#111113] text-sm font-medium text-[#A1A1AA] hover:text-white transition-colors">
            <Users className="w-4 h-4" /> Operators
          </Link>
          <Link to="/admin/services" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#111113] text-sm font-medium text-[#A1A1AA] hover:text-white transition-colors">
            <Settings className="w-4 h-4" /> Services
          </Link>
          <Link to="/admin/display-setup" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#111113] text-sm font-medium text-[#A1A1AA] hover:text-white transition-colors">
            <MonitorSpeaker className="w-4 h-4" /> Displays
          </Link>
          <Link to="/admin/analytics" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#111113] text-sm font-medium text-[#A1A1AA] hover:text-white transition-colors">
            <LineChart className="w-4 h-4" /> Analytics
          </Link>
          <Link to="/admin/migrations" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#111113] text-sm font-medium text-[#A1A1AA] hover:text-white transition-colors">
            <ArrowRightLeft className="w-4 h-4" /> Migrations
          </Link>
          <Link to="/admin/notifications" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#111113] text-sm font-medium text-[#A1A1AA] hover:text-white transition-colors">
            <Bell className="w-4 h-4" /> Notifications
          </Link>
          <Link to="/admin/settings" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#111113] text-sm font-medium text-[#A1A1AA] hover:text-white transition-colors">
            <Settings className="w-4 h-4" /> Settings
          </Link>
        </nav>
        <div className="p-4 border-t border-white/5">
          <button onClick={handleLogout} className="flex items-center w-full gap-3 px-3 py-2 rounded-md hover:bg-red-500/10 text-sm font-medium text-red-500 hover:text-red-400 transition-colors">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </aside>
      
      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-[#09090B]">
        <header className="h-16 border-b border-white/5 bg-[#09090B] flex items-center px-6">
          <h2 className="text-sm font-medium text-[#A1A1AA]">Operations Center</h2>
        </header>
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
