import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchPendingMigrations, approveAdminMigration, rejectAdminMigration } from "@/api/admin";
import { Check, X, ArrowRightLeft } from "lucide-react";

export default function Migrations() {
  const queryClient = useQueryClient();
  const { data: migrations, isLoading } = useQuery({
    queryKey: ['adminMigrations'],
    queryFn: fetchPendingMigrations,
    refetchInterval: 15000,
  });

  const approveMutation = useMutation({
    mutationFn: approveAdminMigration,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['adminMigrations'] })
  });

  const rejectMutation = useMutation({
    mutationFn: rejectAdminMigration,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['adminMigrations'] })
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-medium tracking-tight">Pending Migrations</h1>
        <p className="text-[#A1A1AA] mt-1">Approve or reject token migrations requested by operators.</p>
      </header>

      <div className="bg-[#111113] border border-[#27272A] rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-[#A1A1AA]">Loading...</div>
        ) : !migrations || migrations.length === 0 ? (
          <div className="p-16 flex flex-col items-center justify-center text-[#A1A1AA]">
            <ArrowRightLeft className="w-12 h-12 mb-4 opacity-20" />
            <p>No pending migrations found.</p>
          </div>
        ) : (
          <div className="divide-y divide-[#27272A]">
            {migrations.map((req: any) => (
              <div key={req.id} className="p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 hover:bg-[#1A1A1A] transition">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="bg-[#27272A] px-2 py-1 rounded text-sm font-medium">Token ID: {req.token_id}</span>
                    <span className="text-sm font-bold text-yellow-500 uppercase">{req.status}</span>
                  </div>
                  <p className="text-white text-lg">
                    Counter {req.from_counter_id} <ArrowRightLeft className="inline w-4 h-4 text-[#A1A1AA] mx-2"/> Counter {req.to_counter_id}
                  </p>
                  {req.predicted_time_saved && (
                    <p className="text-green-400 text-sm mt-1">Predicted to save {req.predicted_time_saved} minutes.</p>
                  )}
                  {req.reason && <p className="text-[#A1A1AA] text-sm mt-1 text-italic">"{req.reason}"</p>}
                </div>
                <div className="flex gap-3">
                  <button 
                    onClick={() => rejectMutation.mutate(req.id)}
                    disabled={rejectMutation.isPending || approveMutation.isPending}
                    className="flex items-center gap-2 px-4 py-2 bg-[#27272A] hover:bg-red-500/20 text-white hover:text-red-500 border border-transparent hover:border-red-500/30 rounded transition disabled:opacity-50"
                  >
                    <X className="w-4 h-4" /> Reject
                  </button>
                  <button 
                    onClick={() => approveMutation.mutate(req.id)}
                    disabled={rejectMutation.isPending || approveMutation.isPending}
                    className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-black font-medium rounded transition disabled:opacity-50"
                  >
                    <Check className="w-4 h-4" /> Approve Override
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
