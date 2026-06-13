import { useQuery } from "@tanstack/react-query";
import { fetchCounters } from "@/api/counters";
import { Loader2 } from "lucide-react";

export default function KioskSetup() {
  const { data: counters, isLoading } = useQuery({
    queryKey: ['countersList'],
    queryFn: fetchCounters,
  });

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-8 flex flex-col items-center justify-center font-sans text-[#2D3748]">
      <div className="bg-white p-12 rounded-[2rem] shadow-[20px_20px_60px_#d9dadd,-20px_-20px_60px_#ffffff] max-w-2xl w-full text-center">
        <h1 className="text-4xl font-black mb-2 text-[#2D3748] tracking-tighter">Kiosk Setup</h1>
        <p className="text-lg text-[#718096] font-medium mb-10">Select the counter to bind this kiosk terminal to.</p>

        {isLoading ? (
          <Loader2 className="w-12 h-12 animate-spin mx-auto text-[#48BB78]" />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {counters?.map((counter: any) => (
              <button
                key={counter.id}
                onClick={() => window.location.href = `/kiosk/${counter.qr_slug}`}
                className="bg-[#F7FAFC] p-6 rounded-2xl border-2 border-transparent hover:border-[#48BB78] hover:shadow-[10px_10px_30px_#d9dadd,-10px_-10px_30px_#ffffff] transition-all text-left group"
              >
                <h3 className="text-xl font-bold text-[#2D3748] group-hover:text-[#48BB78] transition-colors">{counter.name}</h3>
                <span className="inline-block mt-2 text-xs font-bold uppercase tracking-widest bg-[#E2E8F0] text-[#718096] px-3 py-1 rounded-full">
                  {counter.queue_type}
                </span>
              </button>
            ))}
            {(!counters || counters.length === 0) && (
              <div className="col-span-full py-8 text-[#A0AEC0] font-medium">No active counters available.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
