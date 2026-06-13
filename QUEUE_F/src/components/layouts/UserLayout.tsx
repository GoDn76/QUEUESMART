import { Outlet } from "react-router-dom";

export default function UserLayout() {
  return (
    <div className="theme-clay light min-h-screen w-full bg-[#F0FDF4] text-[#064E3B] font-sans antialiased selection:bg-[#4ADE80] selection:text-white">
      <main className="max-w-md mx-auto min-h-screen bg-white shadow-[0_0_50px_rgba(4,120,87,0.05)] sm:border-x sm:border-[#DCFCE7] flex flex-col relative overflow-hidden">
        {/* Subtle background decoration */}
        <div className="absolute top-0 left-0 w-full h-64 bg-gradient-to-b from-[#DCFCE7] to-transparent opacity-50 pointer-events-none"></div>
        <div className="flex-1 overflow-auto z-10 p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
