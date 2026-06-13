import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { fetchCounterDetails, joinQueue } from "@/api/public";
import { Loader2, Clock, Users } from "lucide-react";

export default function JoinQueue() {
  const { qr_slug } = useParams();
  const navigate = useNavigate();

  const { data: counter, isLoading: isLoadingCounter } = useQuery({
    queryKey: ['counterDetails', qr_slug],
    queryFn: () => fetchCounterDetails(qr_slug as string),
    enabled: !!qr_slug
  });

  const joinMutation = useMutation({
    mutationFn: (data: any) => joinQueue(qr_slug as string, data),
    onSuccess: (data) => {
      // Redirect to the Live Status page upon successful join
      navigate(`/mobile/status/${qr_slug}/${data.token_number}`);
    }
  });

  const { register, handleSubmit } = useForm();

  if (isLoadingCounter) {
    return <div className="h-full flex items-center justify-center text-[#059669]"><Loader2 className="w-8 h-8 animate-spin" /></div>;
  }

  if (!counter) {
    return <div className="h-full flex items-center justify-center text-red-500 font-medium">Counter Not Found</div>;
  }

  return (
    <div className="space-y-8 pb-8">
      {/* Header Info */}
      <div className="text-center space-y-2 mt-4">
        <h1 className="text-3xl font-black tracking-tight text-[#064E3B]">{counter.name}</h1>
        <div className="inline-block bg-[#ECFDF5] text-[#059669] px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest border border-[#A7F3D0]">
          {counter.queue_type} Queue
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded-3xl p-5 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-[#F1F5F9] flex flex-col items-center text-center">
          <Users className="w-6 h-6 text-[#10B981] mb-2" />
          <span className="text-2xl font-bold text-[#064E3B]">{counter.people_ahead || 0}</span>
          <span className="text-xs font-medium text-[#64748B]">Waiting</span>
        </div>
        <div className="bg-white rounded-3xl p-5 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-[#F1F5F9] flex flex-col items-center text-center">
          <Clock className="w-6 h-6 text-[#10B981] mb-2" />
          <span className="text-2xl font-bold text-[#064E3B]">{counter.estimated_wait_minutes || "0"}m</span>
          <span className="text-xs font-medium text-[#64748B]">Est. Wait</span>
        </div>
      </div>
      
      {counter.suggested_low_traffic_window && (
        <div className="bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0] rounded-xl p-4 text-center shadow-[0_4px_14px_0_rgba(16,185,129,0.1)]">
          <p className="text-sm font-bold">💡 AI Suggestion</p>
          <p className="text-xs font-medium mt-1">Want a faster visit? Best time to come is {counter.suggested_low_traffic_window}</p>
        </div>
      )}

      {/* Join Form */}
      <div className="bg-white rounded-3xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-[#F1F5F9]">
        <h3 className="text-lg font-bold text-[#064E3B] mb-4">Join the Queue</h3>
        <form onSubmit={handleSubmit((d) => joinMutation.mutate({
          customer_name: d.name,
          customer_phone: d.phone.replace(/[\s-]/g, ''),
          service_type_id: parseInt(d.service_type) || counter.service_types?.[0]?.id || 1
        }))} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-bold text-[#64748B] uppercase tracking-wider">Full Name</label>
            <input 
              {...register("name", { required: true })}
              className="w-full bg-[#F8FAFC] border-none rounded-xl px-4 py-3 text-[#0F172A] font-medium focus:ring-2 focus:ring-[#10B981] transition-all"
              placeholder="e.g. Jane Doe"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-bold text-[#64748B] uppercase tracking-wider">Phone Number</label>
            <input 
              {...register("phone", { required: true })}
              type="tel"
              className="w-full bg-[#F8FAFC] border-none rounded-xl px-4 py-3 text-[#0F172A] font-medium focus:ring-2 focus:ring-[#10B981] transition-all"
              placeholder="e.g. +1 234 567 890"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-bold text-[#64748B] uppercase tracking-wider">Service Needed</label>
            <select 
              {...register("service_type")}
              className="w-full bg-[#F8FAFC] border-none rounded-xl px-4 py-3 text-[#0F172A] font-medium focus:ring-2 focus:ring-[#10B981] transition-all"
            >
              {counter.service_types && counter.service_types.length > 0 ? (
                counter.service_types.map((service: any) => (
                  <option key={service.id} value={service.id}>{service.name}</option>
                ))
              ) : (
                <option value="1">General Inquiry</option>
              )}
            </select>
          </div>
          
          <button 
            type="submit"
            disabled={joinMutation.isPending}
            className="w-full mt-6 bg-[#10B981] hover:bg-[#059669] text-white py-4 rounded-xl font-bold text-lg shadow-[0_4px_14px_0_rgba(16,185,129,0.39)] transition-all active:scale-95 flex items-center justify-center disabled:opacity-50"
          >
            {joinMutation.isPending ? <Loader2 className="w-6 h-6 animate-spin" /> : "Get My Token"}
          </button>
        </form>
      </div>
    </div>
  );
}
