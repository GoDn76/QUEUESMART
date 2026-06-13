import { Link } from "react-router-dom";
import { Monitor, LayoutDashboard, Terminal } from "lucide-react";

export default function Hub() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-slate-900">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-extrabold tracking-tight mb-4 text-slate-900">QueueMind</h1>
          <p className="text-xl text-slate-600 font-medium">Select a module to launch</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Link to="/admin" className="group flex flex-col items-center text-center p-8 bg-white rounded-2xl shadow-sm border border-slate-200 hover:shadow-lg hover:border-blue-500 transition-all">
            <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <LayoutDashboard className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Admin Dashboard</h2>
            <p className="text-slate-500">Manage queues, operators, and analytics.</p>
          </Link>

          <Link to="/operator" className="group flex flex-col items-center text-center p-8 bg-white rounded-2xl shadow-sm border border-slate-200 hover:shadow-lg hover:border-yellow-500 transition-all">
            <div className="w-16 h-16 bg-yellow-100 text-yellow-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <Monitor className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Operator Workspace</h2>
            <p className="text-slate-500">Real-time control center for staff.</p>
          </Link>

          <Link to="/kiosk" className="group flex flex-col items-center text-center p-8 bg-white rounded-2xl shadow-sm border border-slate-200 hover:shadow-lg hover:border-emerald-500 transition-all">
            <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <Terminal className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Kiosk Terminal</h2>
            <p className="text-slate-500">Self-service token generation.</p>
          </Link>

        </div>
      </div>
    </div>
  );
}
