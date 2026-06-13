import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  fetchCurrentQueue, fetchCurrentServing, callNextCustomer, 
  completeToken, skipToken, sendHeartbeat, logoutOperator, escalateToken, addWalkIn,
  fetchOperatorMigrations, approveMigration, rejectMigration
} from "@/api/operator";
import { useAuthStore } from "@/store/authStore";
import { Loader2, LogOut, ArrowUp, UserPlus, Check, X } from "lucide-react";
import { useQueueSocket } from "@/hooks/useQueueSocket";

export default function Terminal() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const logout = useAuthStore(state => state.logout);
  const operatorCounterId = useAuthStore(state => state.counterId);
  const [showWalkIn, setShowWalkIn] = useState(false);
  const [showMigrations, setShowMigrations] = useState(false);
  
  const [walkInName, setWalkInName] = useState("");
  const [walkInPhone, setWalkInPhone] = useState("");

  // 1. Fetch live queue data
  const { data: queueArray, isLoading: isLoadingQueue } = useQuery({
    queryKey: ['operatorQueue'],
    queryFn: fetchCurrentQueue,
    refetchInterval: 10000,
  });

  const { data: servingData, isLoading: isLoadingServing } = useQuery({
    queryKey: ['operatorServing'],
    queryFn: fetchCurrentServing,
  });

  const waitingList = Array.isArray(queueArray) ? queueArray : [];
  const currentToken = servingData?.token_number;
  const currentTokenId = servingData?.id;
  // If we have an active ticket, grab counter_id from it, otherwise use operatorCounterId
  const counterId = servingData?.counter_id || operatorCounterId; 

  // 2. CRITICAL BACKGROUND TASK: 60s Heartbeat for Redis Lock
  useEffect(() => {
    const runHeartbeat = async () => {
      try {
        await sendHeartbeat();
      } catch (err: any) {
        if (err.response?.status === 403) {
          alert("Session expired or lock lost. You have been logged out.");
          logout();
          navigate("/operator/login");
        }
      }
    };

    runHeartbeat();
    const interval = setInterval(runHeartbeat, 60000);
    return () => clearInterval(interval);
  }, [logout, navigate]);

  // 3. WebSocket Connection
  const { isConnected, status } = useQueueSocket("counter", counterId?.toString());

  // 4. Mutations
  const callNextMutation = useMutation({
    mutationFn: callNextCustomer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['operatorQueue'] });
      queryClient.invalidateQueries({ queryKey: ['operatorServing'] });
    }
  });

  const completeMutation = useMutation({
    mutationFn: () => completeToken(currentTokenId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['operatorQueue'] });
      queryClient.invalidateQueries({ queryKey: ['operatorServing'] });
    }
  });

  const skipMutation = useMutation({
    mutationFn: () => skipToken(currentTokenId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['operatorQueue'] });
      queryClient.invalidateQueries({ queryKey: ['operatorServing'] });
    }
  });

  const escalateMutation = useMutation({
    mutationFn: (tokenId: string | number) => escalateToken(tokenId, { new_priority_weight: 200, reason: "Operator Escalation" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['operatorQueue'] });
    }
  });

  const walkInMutation = useMutation({
    mutationFn: () => addWalkIn({ counter_id: counterId, service_type_id: 1, customer_name: walkInName, customer_phone: walkInPhone }),
    onSuccess: () => {
      setShowWalkIn(false);
      setWalkInName("");
      setWalkInPhone("");
      queryClient.invalidateQueries({ queryKey: ['operatorQueue'] });
    }
  });

  const { data: migrations } = useQuery({
    queryKey: ['operatorMigrations'],
    queryFn: fetchOperatorMigrations,
    refetchInterval: 10000,
  });

  const approveMigrationMutation = useMutation({
    mutationFn: approveMigration,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['operatorMigrations'] })
  });

  const rejectMigrationMutation = useMutation({
    mutationFn: rejectMigration,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['operatorMigrations'] })
  });

  const handleLogout = async () => {
    try {
      await logoutOperator();
    } catch(e) {}
    logout();
    navigate("/operator/login");
  };

  const isMutating = callNextMutation.isPending || completeMutation.isPending || skipMutation.isPending;

  if (!counterId) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center bg-[#09090B] text-white space-y-6">
        <h1 className="text-3xl font-bold">Session Invalid</h1>
        <p className="text-[#A1A1AA]">We couldn't detect your assigned counter. Please log out and log in again.</p>
        <button onClick={handleLogout} className="px-6 py-3 bg-[#4ADE80] text-black font-bold uppercase rounded-md shadow-[0_0_15px_rgba(74,222,128,0.3)]">
          Return to Login
        </button>
      </div>
    );
  }

  return (
    <div className="h-screen w-full flex flex-col p-8 bg-[#09090B] text-white selection:bg-[#4ADE80] selection:text-black relative">
      
      {/* Walk-In Modal */}
      {showWalkIn && (
        <div className="absolute inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
           <div className="bg-[#111113] border border-[#27272A] p-8 rounded-lg w-full max-w-md">
              <h3 className="text-xl font-bold mb-4">Add Walk-In Customer</h3>
              <div className="space-y-4">
                <input 
                  type="text" 
                  placeholder="Customer Name" 
                  value={walkInName}
                  onChange={e => setWalkInName(e.target.value)}
                  className="w-full bg-[#1A1A1A] border border-[#27272A] p-3 rounded text-white"
                />
                <input 
                  type="text" 
                  placeholder="Phone Number (optional)" 
                  value={walkInPhone}
                  onChange={e => setWalkInPhone(e.target.value)}
                  className="w-full bg-[#1A1A1A] border border-[#27272A] p-3 rounded text-white"
                />
                <div className="flex gap-4 mt-6">
                  <button onClick={() => setShowWalkIn(false)} className="flex-1 bg-[#27272A] py-3 rounded font-bold uppercase">Cancel</button>
                  <button 
                    onClick={() => walkInMutation.mutate()} 
                    disabled={!walkInName || walkInMutation.isPending}
                    className="flex-1 bg-[#4ADE80] text-black py-3 rounded font-bold uppercase disabled:opacity-50"
                  >
                    {walkInMutation.isPending ? "Adding..." : "Add"}
                  </button>
                </div>
              </div>
           </div>
        </div>
      )}

      {/* Migrations Modal */}
      {showMigrations && (
        <div className="absolute inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
           <div className="bg-[#111113] border border-[#27272A] p-8 rounded-lg w-full max-w-2xl">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold">Migration Requests</h3>
                <button onClick={() => setShowMigrations(false)} className="text-[#A1A1AA] hover:text-white"><X className="w-6 h-6" /></button>
              </div>
              <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
                {migrations && migrations.length > 0 ? migrations.map((req: any) => (
                  <div key={req.id} className="bg-[#1A1A1A] p-4 rounded border border-[#27272A] flex justify-between items-center">
                    <div>
                      <p className="font-bold text-white">Token ID: {req.token_id}</p>
                      <p className="text-sm text-[#A1A1AA]">From Counter {req.from_counter_id} → To Counter {req.to_counter_id}</p>
                      <p className="text-xs text-yellow-500 mt-1">Status: {req.status}</p>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => rejectMigrationMutation.mutate(req.id)} className="bg-red-500/10 text-red-500 px-3 py-1 rounded border border-red-500/20 hover:bg-red-500/20 text-sm font-bold uppercase flex items-center gap-1">
                        <X className="w-4 h-4"/> Reject
                      </button>
                      <button onClick={() => approveMigrationMutation.mutate(req.id)} className="bg-green-500/10 text-green-500 px-3 py-1 rounded border border-green-500/20 hover:bg-green-500/20 text-sm font-bold uppercase flex items-center gap-1">
                        <Check className="w-4 h-4"/> Approve
                      </button>
                    </div>
                  </div>
                )) : <p className="text-[#A1A1AA] text-center py-8">No pending migrations.</p>}
              </div>
           </div>
        </div>
      )}

      {/* Header */}
      <header className="flex justify-between items-center border-b border-white/5 pb-6 mb-6">
        <div>
          <h1 className="text-2xl font-medium tracking-tight text-white uppercase">Mission Control</h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Counter Operations • Status: {status.toUpperCase()}</p>
        </div>
        <div className="flex items-center gap-4">
           <button onClick={() => setShowMigrations(true)} className="flex items-center gap-2 bg-[#1A1A1A] hover:bg-[#27272A] border border-blue-500/30 text-blue-400 px-4 py-2 rounded-md text-sm font-bold uppercase transition">
             Migrations
           </button>
           <button onClick={() => setShowWalkIn(true)} className="flex items-center gap-2 bg-[#1A1A1A] hover:bg-[#27272A] border border-[#27272A] px-4 py-2 rounded-md text-sm font-bold uppercase transition">
             <UserPlus className="w-4 h-4" /> Walk-In
           </button>
           <div className="flex items-center gap-3 bg-[#111113] border border-white/5 px-4 py-2 rounded-full">
             <span className={`w-3 h-3 rounded-full ${isConnected ? 'bg-[#4ADE80] shadow-[0_0_10px_rgba(74,222,128,0.5)]' : 'bg-[#FACC15]'}`} />
             <span className={`text-sm font-bold tracking-wider ${isConnected ? 'text-[#4ADE80]' : 'text-[#FACC15]'}`}>
               {isConnected ? 'LIVE' : status.toUpperCase()}
             </span>
           </div>
           <button onClick={handleLogout} className="p-2 bg-red-500/10 text-red-500 hover:bg-red-500/20 rounded-md border border-red-500/20 transition">
             <LogOut className="w-5 h-5" />
           </button>
        </div>
      </header>

      {/* Main Interface */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left: Active Ticket */}
        <div className="lg:col-span-2 bg-[#111111] border border-[#27272A] rounded-lg p-12 flex flex-col justify-center items-center relative overflow-hidden group">
           <div className="absolute inset-0 bg-[#4ADE80]/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
           
           <p className="text-[#A1A1AA] text-sm font-medium tracking-widest mb-6 uppercase">Now Serving</p>
           
           <h2 className="text-[12rem] leading-none font-black text-white tracking-tighter">
             {isLoadingServing ? "..." : currentToken || "--"}
           </h2>
           
           {currentToken && (
              <div className="mt-12 flex gap-4 text-sm font-medium">
                 <span className="bg-[#1A1A1A] text-[#A1A1AA] px-4 py-2 rounded-md border border-[#27272A]">
                   {servingData?.customer_name || "Anonymous"}
                 </span>
                 <span className="bg-[#1A1A1A] text-[#A1A1AA] px-4 py-2 rounded-md border border-[#27272A]">
                   {servingData?.customer_phone || "No Phone"}
                 </span>
              </div>
           )}
        </div>

        {/* Right: Actions & Queue List */}
        <div className="flex flex-col gap-6">
          
          {/* Action Pad */}
          <div className="bg-[#111113] border border-white/5 rounded-lg p-6 space-y-4">
            {currentToken ? (
              <div className="grid grid-cols-2 gap-4">
                <button 
                  onClick={() => completeMutation.mutate()}
                  disabled={isMutating}
                  className="h-24 bg-white hover:bg-gray-200 text-black text-xl font-bold uppercase tracking-widest rounded-md transition-all active:scale-95 disabled:opacity-50"
                >
                  {completeMutation.isPending ? <Loader2 className="w-6 h-6 animate-spin mx-auto" /> : "Complete"}
                </button>
                <button 
                  onClick={() => skipMutation.mutate()}
                  disabled={isMutating}
                  className="h-24 bg-[#1A1A1A] hover:bg-[#27272A] border border-[#27272A] text-white text-xl font-bold uppercase tracking-widest rounded-md transition-all active:scale-95 disabled:opacity-50"
                >
                  {skipMutation.isPending ? <Loader2 className="w-6 h-6 animate-spin mx-auto" /> : "Skip"}
                </button>
              </div>
            ) : (
              <button 
                onClick={() => callNextMutation.mutate()}
                disabled={isMutating}
                className="w-full h-32 bg-[#4ADE80] hover:bg-[#22c55e] text-black text-3xl font-black uppercase tracking-widest rounded-md transition-all active:scale-95 disabled:opacity-50 shadow-[0_0_20px_rgba(74,222,128,0.3)]"
              >
                {callNextMutation.isPending ? <Loader2 className="w-8 h-8 animate-spin mx-auto" /> : "Call Next"}
              </button>
            )}
          </div>
          
          {/* Queue List */}
          <div className="flex-1 bg-[#111113] border border-white/5 rounded-lg p-6 flex flex-col">
             <h3 className="text-xs font-bold uppercase tracking-widest text-[#A1A1AA] mb-4">Up Next in Queue ({waitingList.length})</h3>
             <div className="flex-1 overflow-auto space-y-2 pr-2">
                {isLoadingQueue ? (
                  <p className="text-[#A1A1AA] text-sm animate-pulse">Loading queue...</p>
                ) : queueArray && (queueArray as any).error ? (
                  <div className="text-red-500 font-bold p-4 bg-red-500/10 rounded">
                    Error loading queue: {JSON.stringify((queueArray as any).error)}
                  </div>
                ) : waitingList.length > 0 ? (
                  waitingList.map((ticket: any) => (
                    <div key={ticket.id} className="flex justify-between items-center p-4 bg-[#1A1A1A] border border-[#27272A] rounded-md group">
                      <div className="flex flex-col">
                        <span className="font-bold text-lg text-white">{ticket.token_number}</span>
                        <span className="text-xs text-[#A1A1AA]">{ticket.customer_name || 'Walk-in'}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`text-[10px] font-bold tracking-wider uppercase px-2 py-1 rounded border ${ticket.priority_score > 100 ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' : 'bg-[#111111] text-[#A1A1AA] border-[#27272A]'}`}>
                          {ticket.priority_score > 100 ? 'PRIORITY' : 'NORMAL'}
                        </span>
                        <button 
                          onClick={() => escalateMutation.mutate(ticket.id)}
                          disabled={escalateMutation.isPending || ticket.priority_score > 100}
                          className="opacity-0 group-hover:opacity-100 p-2 bg-[#27272A] hover:bg-[#3f3f46] rounded-full transition disabled:opacity-0"
                          title="Escalate Token"
                        >
                          <ArrowUp className="w-3 h-3 text-amber-500" />
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-[#A1A1AA]">
                    <p className="text-sm font-medium">Queue is empty</p>
                  </div>
                )}
             </div>
          </div>

        </div>
      </div>
    </div>
  );
}
