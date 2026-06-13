import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchDisplayState } from "@/api/display";
import { Volume2, MonitorPlay, Loader2 } from "lucide-react";

import { useAuthStore } from "@/store/authStore";

export default function DisplayBoard() {
  const { displayId } = useParams();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const authStoreToken = useAuthStore(state => state.token);
  
  // Hydration state to prevent firing query before localStorage is read
  const [hasHydrated, setHasHydrated] = useState(false);
  useEffect(() => {
    setHasHydrated(useAuthStore.persist.hasHydrated());
    const unsub = useAuthStore.persist.onFinishHydration(() => setHasHydrated(true));
    return () => { if (unsub) unsub(); }
  }, []);

  // Prefer URL token (e.g. smart TV direct link) over local storage token
  const token = searchParams.get('token') || authStoreToken;

  const { data: board, isLoading } = useQuery({
    queryKey: ['displayState', displayId, token], // Add token to key to force refetch if it changes
    queryFn: () => fetchDisplayState(displayId as string, token || undefined),
    enabled: !!displayId && hasHydrated, // Wait for localStorage to be read!
    refetchInterval: 10000,
    retry: false,
  });

  // Sound and cache invalidation on WebSocket push
  useEffect(() => {
    if (!board) return;
    
    // Connect to organization level WS if organization board, else counter WS
    const topic = board.board_type === 'ORGANIZATION' 
        ? `org/${board.organization_id}` 
        : `counter/${board.counter_id}`;
        
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${topic}`;
    
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === "TOKEN_CALLED") {
          // Play a simple beep natively if possible, or attempt audio play
          try {
            const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = "sine";
            osc.frequency.setValueAtTime(600, ctx.currentTime);
            gain.gain.setValueAtTime(0.5, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 1);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 1);
          } catch(e) {}
        }
      } catch(e) {}
      
      queryClient.invalidateQueries({ queryKey: ['displayState'] });
    };

    return () => ws.close();
  }, [board?.board_type, board?.organization_id, board?.counter_id, queryClient]);

  if (!hasHydrated || isLoading) {
    return <div className="h-full flex items-center justify-center text-[#4ADE80]"><Loader2 className="w-16 h-16 animate-spin" /></div>;
  }

  if (!token) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-red-500 font-bold text-4xl">
        <p>Display Offline</p>
        <p className="text-lg text-gray-500 mt-4">Missing Authentication Token</p>
      </div>
    );
  }

  if (!board) return <div className="h-full flex flex-col items-center justify-center text-red-500 font-bold text-4xl"><p>Display Offline</p><p className="text-lg text-gray-500 mt-4">Invalid Display ID or Token</p></div>;

  const states = board.board_type === 'ORGANIZATION' ? board.all_counters_state : (board.counter_state ? [board.counter_state] : []);

  return (
    <div className="flex-1 w-full flex flex-col bg-[#09090B] p-8 gap-8">
      
      {/* Header */}
      <header className="flex justify-between items-center border-b border-[#27272A] pb-6">
         <div className="flex items-center gap-4">
            <MonitorPlay className="w-10 h-10 text-[#4ADE80]" />
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-white">{board.name}</h1>
              <p className="text-[#A1A1AA] uppercase tracking-widest text-sm mt-1">{board.organization_name}</p>
            </div>
         </div>
         <div className="text-right">
            <p className="text-4xl font-black text-white">{board.overall_waiting_count || 0}</p>
            <p className="text-[#A1A1AA] uppercase tracking-widest text-xs mt-1">Total Waiting</p>
         </div>
      </header>

      {/* Grid of Counters */}
      <div className={`flex-1 grid gap-8 ${states && states.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
        {states?.map((state: any) => (
          <div key={state.counter_id} className="bg-[#111113] border border-[#27272A] rounded-3xl p-8 flex flex-col h-full shadow-[0_10px_40px_rgba(0,0,0,0.5)]">
             
             {/* Counter Title */}
             <div className="bg-[#1A1A1A] inline-block px-6 py-2 rounded-full border border-white/5 mb-8 self-start">
               <span className="text-xl font-bold text-white uppercase tracking-widest">{state.counter_name}</span>
             </div>

             <div className="flex-1 flex gap-8">
                {/* Now Serving */}
                <div className="flex-[3] flex flex-col items-center justify-center bg-[#09090B] border border-[#27272A] rounded-2xl relative overflow-hidden group">
                   {state.current_token && <div className="absolute inset-0 bg-[#4ADE80]/5 animate-pulse pointer-events-none"></div>}
                   <Volume2 className={`w-12 h-12 mb-6 opacity-80 ${state.current_token ? 'text-[#4ADE80]' : 'text-[#27272A]'}`} />
                   <h2 className="text-2xl font-bold tracking-widest uppercase text-[#A1A1AA] mb-4">Now Serving</h2>
                   <h1 className="text-[9rem] font-black text-white leading-none tracking-tighter">
                     {state.current_token ? state.current_token.token_number : "--"}
                   </h1>
                </div>

                {/* Upcoming */}
                <div className="flex-[2] flex flex-col gap-4">
                   <h3 className="text-lg font-bold text-[#A1A1AA] uppercase tracking-widest mb-2 border-b border-[#27272A] pb-2">Up Next</h3>
                   <div className="flex-1 flex flex-col gap-4">
                     {state.upcoming_tokens?.slice(0, 3).map((t: any, idx: number) => (
                        <div key={t.id} className="flex justify-between items-center bg-[#1A1A1A] border border-[#27272A] p-6 rounded-xl flex-1">
                          <span className={`font-bold text-white ${idx === 0 ? 'text-5xl' : 'text-3xl opacity-80'}`}>{t.token_number}</span>
                          <span className="text-[#A1A1AA] text-sm uppercase tracking-widest">{idx === 0 ? 'Next' : 'Wait'}</span>
                        </div>
                     ))}
                     {(!state.upcoming_tokens || state.upcoming_tokens.length === 0) && (
                        <div className="flex-1 flex items-center justify-center text-[#A1A1AA] text-lg font-medium border border-dashed border-[#27272A] rounded-xl">No one waiting</div>
                     )}
                   </div>
                </div>
             </div>
          </div>
        ))}
        {(!states || states.length === 0) && (
          <div className="col-span-full h-full flex flex-col items-center justify-center text-[#A1A1AA]">
            <p className="text-xl font-medium">No active counters to display.</p>
          </div>
        )}
      </div>
    </div>
  );
}
