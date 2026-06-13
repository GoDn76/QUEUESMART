import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchCounters, createCounter } from "@/api/counters";
import type { CounterPayload } from "@/api/counters";
import { useForm } from "react-hook-form";
import { QRCodeSVG } from "qrcode.react";
import { Plus, Copy, Check, Loader2, MonitorPlay } from "lucide-react";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export default function Counters() {
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [copiedSlug, setCopiedSlug] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Fetch Counters
  const { data: counters = [], isLoading } = useQuery({
    queryKey: ['countersList'],
    queryFn: fetchCounters,
  });

  // Create Mutation
  const createMutation = useMutation({
    mutationFn: createCounter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['countersList'] });
      setIsAddOpen(false);
      reset();
    }
  });

  // Form Setup
  const { register, handleSubmit, reset } = useForm<CounterPayload>();

  const onSubmit = (data: CounterPayload) => {
    createMutation.mutate(data);
  };

  const copyToClipboard = (slug: string) => {
    const url = `${window.location.origin}/q/${slug}`;
    navigator.clipboard.writeText(url);
    setCopiedSlug(slug);
    setTimeout(() => setCopiedSlug(null), 2000);
  };

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-2xl text-white font-medium tracking-tight">Counter Management</h3>
          <p className="text-[#A1A1AA] text-sm font-medium mt-1">Provision physical kiosks and generate QR codes.</p>
        </div>
        
        <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
          <DialogTrigger asChild>
            <button className="flex items-center gap-2 bg-white hover:bg-gray-200 text-black px-4 py-2 rounded-md font-medium text-sm transition-colors active:scale-95">
              <Plus className="w-4 h-4" /> Create Counter
            </button>
          </DialogTrigger>
          <DialogContent className="bg-[#111113] border border-white/5 text-white sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle className="text-lg font-medium tracking-tight">Provision New Counter</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-[#A1A1AA]">Counter Name</label>
                <input 
                  {...register("name", { required: true })}
                  className="w-full bg-[#1A1A1A] border border-[#27272A] rounded-md px-3 py-2 text-white focus:outline-none focus:border-[#4ADE80]" 
                  placeholder="e.g. General OPD A" 
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[#A1A1AA]">Queue Algorithm</label>
                <select 
                  {...register("queue_type", { required: true })}
                  className="w-full bg-[#1A1A1A] border border-[#27272A] rounded-md px-3 py-2 text-white focus:outline-none focus:border-[#4ADE80]"
                >
                  <option value="FIFO">FIFO (First In, First Out)</option>
                  <option value="PRIORITY">PRIORITY (Weight Based)</option>
                  <option value="HYBRID">HYBRID (Mixed)</option>
                </select>
              </div>
              <button 
                type="submit" 
                disabled={createMutation.isPending}
                className="w-full bg-white hover:bg-gray-200 text-black py-2 rounded-md font-medium mt-4 transition-colors disabled:opacity-50 flex justify-center items-center"
              >
                {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Generate Counter & QR"}
              </button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="text-[#A1A1AA] text-sm animate-pulse">Loading counters...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {counters.map((counter: any) => {
            // Using /q/ as specified in your Master Routing Spec
            const queueUrl = `${window.location.origin}/mobile/joinQueue/${counter.qr_slug}`;
            return (
              <div key={counter.id} className="bg-[#111113] border border-white/5 rounded-lg p-6 flex flex-col justify-between hover:border-[#27272A] transition-colors group">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h4 className="text-white font-medium text-lg tracking-tight">{counter.name}</h4>
                    <div className="flex gap-2 mt-2">
                      <span className="text-[10px] font-bold tracking-wider uppercase bg-[#1A1A1A] text-[#A1A1AA] px-2 py-1 rounded border border-[#27272A]">
                        {counter.queue_type}
                      </span>
                      {counter.active && (
                        <span className="text-[10px] font-bold tracking-wider uppercase bg-[#4ADE80]/10 text-[#4ADE80] px-2 py-1 rounded border border-[#4ADE80]/20">
                          ACTIVE
                        </span>
                      )}
                    </div>
                  </div>
                  {/* The Rendered QR Code */}
                  <div className="bg-white p-2 rounded-md shadow-sm">
                    <QRCodeSVG value={queueUrl} size={80} level="M" />
                  </div>
                </div>

                <div className="mt-4 border-t border-[#27272A] pt-4 flex items-center justify-between">
                  <div className="truncate pr-4">
                    <p className="text-xs text-[#A1A1AA] font-mono truncate">{queueUrl}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <button 
                      onClick={() => window.open(`/display/${counter.id}`, '_blank')}
                      className="flex items-center gap-1 text-purple-400 hover:text-purple-300 text-[10px] font-bold tracking-widest uppercase transition-colors"
                      title="Launch Display Board"
                    >
                      <MonitorPlay className="w-4 h-4" /> Display
                    </button>
                    <button 
                      onClick={() => copyToClipboard(counter.qr_slug)}
                      className="flex-shrink-0 text-[#A1A1AA] hover:text-white transition-colors"
                      title="Copy Public Link"
                    >
                      {copiedSlug === counter.qr_slug ? <Check className="w-4 h-4 text-[#4ADE80]" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
