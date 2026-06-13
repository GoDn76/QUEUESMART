import { useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { joinQueue } from "@/api/public"; 
import { Loader2, ArrowLeft } from "lucide-react";

export default function Details() {
  const navigate = useNavigate();
  const { qr_slug } = useParams();
  const location = useLocation();
  const serviceTypeId = location.state?.serviceTypeId || 1;

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");

  const joinMutation = useMutation({
    mutationFn: () => joinQueue(qr_slug as string, { customer_name: name, customer_phone: phone, service_type_id: serviceTypeId }),
    onSuccess: (data) => {
      navigate(`/kiosk/${qr_slug}/success`, { state: { token_number: data.token_number } });
    }
  });

  return (
    <div className="max-w-3xl mx-auto flex flex-col h-full pt-8 pb-12">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-[#64748B] font-bold uppercase tracking-widest mb-12 hover:text-[#064E3B] transition w-fit">
        <ArrowLeft className="w-5 h-5" /> Go Back
      </button>

      <h2 className="text-5xl font-bold mb-12 text-[#064E3B]">Who are we helping today?</h2>
      
      <div className="space-y-8 flex-1">
        <div className="space-y-3">
          <label className="text-lg font-bold text-[#64748B] uppercase tracking-wider pl-2">Your Full Name</label>
          <input 
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-[#F8FAFC] border-2 border-[#E2E8F0] rounded-3xl px-8 py-6 text-3xl font-medium focus:border-[#10B981] focus:ring-4 focus:ring-[#10B981]/20 transition-all outline-none shadow-inner"
            placeholder="Tap to enter name..."
          />
        </div>
        <div className="space-y-3">
          <label className="text-lg font-bold text-[#64748B] uppercase tracking-wider pl-2">Phone Number (Optional)</label>
          <input 
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full bg-[#F8FAFC] border-2 border-[#E2E8F0] rounded-3xl px-8 py-6 text-3xl font-medium focus:border-[#10B981] focus:ring-4 focus:ring-[#10B981]/20 transition-all outline-none shadow-inner"
            placeholder="Tap to enter phone..."
          />
        </div>
      </div>

      <button 
        onClick={() => joinMutation.mutate()}
        disabled={!name || joinMutation.isPending}
        className="w-full mt-12 bg-[#10B981] hover:bg-[#059669] text-white py-8 rounded-3xl font-black text-3xl shadow-[0_10px_40px_0_rgba(16,185,129,0.3)] transition-all active:scale-95 flex items-center justify-center disabled:opacity-50"
      >
        {joinMutation.isPending ? <Loader2 className="w-10 h-10 animate-spin" /> : "Print My Ticket"}
      </button>
    </div>
  );
}
