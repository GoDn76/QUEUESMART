import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchTicketStatus } from "@/api/public";
import { Loader2, BellRing } from "lucide-react";

export default function LiveStatus() {
  const { qr_slug, token_number } = useParams();
  const queryClient = useQueryClient();
  const [wsConnected, setWsConnected] = useState(false);

  const { data: status, isLoading } = useQuery({
    queryKey: ['ticketStatus', qr_slug, token_number],
    queryFn: () => fetchTicketStatus(qr_slug as string, token_number as string),
    enabled: !!qr_slug && !!token_number,
    refetchInterval: 10000,
  });

  // WebSocket Connection
  useEffect(() => {
    if (!status?.id) return;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/user/${status.id}`;
    
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onmessage = () => {
      // Refresh status on push
      queryClient.invalidateQueries({ queryKey: ['ticketStatus'] });
    };

    return () => ws.close();
  }, [status?.id, queryClient]);

  if (isLoading) {
    return <div className="h-full flex items-center justify-center text-[#059669]"><Loader2 className="w-8 h-8 animate-spin" /></div>;
  }

  const isMyTurn = status?.status === 'SERVING';

  return (
    <div className="space-y-8 flex flex-col h-full items-center text-center pt-8">
      
      {/* Status Badge */}
      <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold uppercase tracking-widest border ${
        isMyTurn 
          ? 'bg-[#10B981] text-white border-[#059669] shadow-[0_0_20px_rgba(16,185,129,0.4)] animate-pulse' 
          : 'bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]'
      }`}>
        {isMyTurn ? <BellRing className="w-4 h-4" /> : null}
        {isMyTurn ? "IT IS YOUR TURN!" : "You are in line"}
      </div>

      {/* Token Card */}
      <div className="w-full bg-white rounded-[2.5rem] p-8 shadow-[0_8px_40px_rgb(0,0,0,0.06)] border border-[#F1F5F9] relative overflow-hidden">
        {isMyTurn && <div className="absolute inset-0 bg-gradient-to-b from-[#10B981]/10 to-transparent pointer-events-none"></div>}
        <p className="text-[#64748B] font-bold uppercase tracking-widest text-sm mb-2">Your Token</p>
        <h2 className="text-7xl font-black text-[#064E3B] tracking-tighter mb-8">{token_number}</h2>
        
        <div className="grid grid-cols-2 gap-4 border-t border-[#F1F5F9] pt-8">
          <div>
            <p className="text-3xl font-bold text-[#0F172A]">{status?.people_ahead || 0}</p>
            <p className="text-xs font-bold text-[#64748B] uppercase tracking-wider mt-1">People Ahead</p>
          </div>
          <div>
            <p className="text-3xl font-bold text-[#0F172A]">{status?.est_wait_time || "0m"}</p>
            <p className="text-xs font-bold text-[#64748B] uppercase tracking-wider mt-1">Est. Wait</p>
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-[#F8FAFC] w-full rounded-2xl p-6 border border-[#F1F5F9]">
        <p className="text-sm font-medium text-[#64748B]">
          {isMyTurn 
            ? "Please proceed immediately to the counter." 
            : "Keep this screen open. We will notify you when it's your turn."}
        </p>
        {!wsConnected && !isMyTurn && (
          <p className="text-xs text-amber-500 mt-2 flex justify-center items-center gap-1">
             <Loader2 className="w-3 h-3 animate-spin" /> Reconnecting to live updates...
          </p>
        )}
      </div>

    </div>
  );
}
