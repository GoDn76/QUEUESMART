import { Outlet } from "react-router-dom";

export default function DisplayLayout() {
  return (
    <div className="dark h-screen w-full bg-[#09090B] text-white font-sans antialiased overflow-hidden flex flex-col selection:bg-[#4ADE80] selection:text-black">
      <div className="w-full flex-1 flex flex-col relative overflow-hidden">
        {/* Subtle background glow */}
        <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-[#4ADE80]/5 blur-[120px] rounded-full pointer-events-none"></div>
        <div className="flex-1 z-10 flex flex-col">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
