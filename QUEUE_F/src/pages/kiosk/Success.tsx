import { useEffect } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { CheckCircle } from "lucide-react";

export default function Success() {
  const navigate = useNavigate();
  const { qr_slug } = useParams();
  const location = useLocation();
  const tokenNumber = location.state?.token_number || "T-000";

  useEffect(() => {
    // Automatic Session Reset for the next Kiosk Walk-In
    const timer = setTimeout(() => {
      navigate(`/kiosk/${qr_slug}/select-service`);
    }, 7000);

    return () => clearTimeout(timer);
  }, [navigate, qr_slug]);

  return (
    <div className="h-full flex flex-col items-center justify-center text-center pb-12">
      <CheckCircle className="w-40 h-40 text-[#10B981] mb-12 animate-bounce" />
      <h2 className="text-6xl font-bold text-[#064E3B] mb-4">You're all set!</h2>
      <p className="text-2xl text-[#64748B] mb-16 font-medium">Please take a seat and wait for your token to be called.</p>
      
      <div className="bg-[#F8FAFC] border-4 border-[#E2E8F0] rounded-[4rem] px-32 py-16 inline-block shadow-xl">
        <p className="text-xl font-bold uppercase tracking-widest text-[#64748B] mb-6">Your Token Number</p>
        <span className="text-[10rem] leading-none font-black text-[#064E3B] tracking-tighter drop-shadow-sm">{tokenNumber}</span>
      </div>

      <p className="text-lg text-[#94A3B8] mt-24 font-bold uppercase tracking-widest animate-pulse">Screen will reset automatically...</p>
    </div>
  );
}
