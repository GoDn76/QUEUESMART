import { useNavigate, useParams } from "react-router-dom";
import { Users, FileText, HelpCircle } from "lucide-react";

export default function SelectService() {
  const navigate = useNavigate();
  const { qr_slug } = useParams();

  const handleSelect = (serviceTypeId: number) => {
    // Navigate to details collection, passing the selected service via state
    navigate(`/kiosk/${qr_slug}/details`, { state: { serviceTypeId } });
  };

  return (
    <div className="h-full flex flex-col justify-center pb-12">
      <h2 className="text-4xl font-bold text-center mb-12">What do you need help with today?</h2>
      
      <div className="grid grid-cols-3 gap-8 h-80">
        <button 
          onClick={() => handleSelect(1)}
          className="bg-white border-2 border-[#E2E8F0] hover:border-[#10B981] p-12 rounded-[2rem] flex flex-col items-center justify-center gap-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-all active:scale-95 group"
        >
          <div className="w-24 h-24 bg-[#ECFDF5] rounded-full flex items-center justify-center group-hover:bg-[#10B981] transition-colors">
            <Users className="w-12 h-12 text-[#10B981] group-hover:text-white transition-colors" />
          </div>
          <span className="text-2xl font-bold">General Inquiry</span>
        </button>

        <button 
          onClick={() => handleSelect(2)}
          className="bg-white border-2 border-[#E2E8F0] hover:border-[#10B981] p-12 rounded-[2rem] flex flex-col items-center justify-center gap-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-all active:scale-95 group"
        >
          <div className="w-24 h-24 bg-[#ECFDF5] rounded-full flex items-center justify-center group-hover:bg-[#10B981] transition-colors">
            <FileText className="w-12 h-12 text-[#10B981] group-hover:text-white transition-colors" />
          </div>
          <span className="text-2xl font-bold">Billing & Payments</span>
        </button>

        <button 
          onClick={() => handleSelect(3)}
          className="bg-white border-2 border-[#E2E8F0] hover:border-[#10B981] p-12 rounded-[2rem] flex flex-col items-center justify-center gap-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-all active:scale-95 group"
        >
          <div className="w-24 h-24 bg-[#ECFDF5] rounded-full flex items-center justify-center group-hover:bg-[#10B981] transition-colors">
            <HelpCircle className="w-12 h-12 text-[#10B981] group-hover:text-white transition-colors" />
          </div>
          <span className="text-2xl font-bold">Customer Support</span>
        </button>
      </div>
    </div>
  );
}
