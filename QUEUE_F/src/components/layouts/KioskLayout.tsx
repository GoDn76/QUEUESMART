import { Outlet } from "react-router-dom";

export default function KioskLayout() {
  return (
    <div className="theme-clay light h-screen w-full bg-[#F0FDF4] text-[#064E3B] font-sans antialiased overflow-hidden flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-5xl h-full bg-white shadow-[0_20px_100px_rgba(4,120,87,0.08)] rounded-[3rem] border border-[#DCFCE7] flex flex-col relative overflow-hidden">
        {/* Subtle decorative header */}
        <div className="h-32 bg-gradient-to-b from-[#ECFDF5] to-transparent w-full absolute top-0 left-0 pointer-events-none"></div>
        
        {/* Main Content Area */}
        <div className="flex-1 z-10 p-12 flex flex-col">
           <header className="mb-12 text-center">
             <h1 className="text-5xl font-black tracking-tighter text-[#064E3B]">QueueMind</h1>
             <p className="text-xl font-bold text-[#10B981] uppercase tracking-widest mt-2">Self-Service Terminal</p>
           </header>
           <div className="flex-1">
             <Outlet />
           </div>
        </div>
      </div>
    </div>
  );
}
