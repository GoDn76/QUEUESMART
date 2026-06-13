import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchCounterDetails } from "@/api/public";
import { Users, FileText, HelpCircle, Loader2 } from "lucide-react";

export default function SelectService() {
  const navigate = useNavigate();
  const { qr_slug } = useParams();

  const { data: counter, isLoading } = useQuery({
    queryKey: ['kioskCounter', qr_slug],
    queryFn: () => fetchCounterDetails(qr_slug as string),
    enabled: !!qr_slug
  });

  const handleSelect = (serviceTypeId: number) => {
    // Navigate to details collection, passing the selected service via state
    navigate(`/kiosk/${qr_slug}/details`, { state: { serviceTypeId } });
  };

  if (isLoading) {
    return <div className="h-full flex items-center justify-center text-[#10B981]"><Loader2 className="w-16 h-16 animate-spin" /></div>;
  }

  if (!counter) {
    return <div className="h-full flex items-center justify-center text-red-500 text-2xl font-bold">Counter Not Found</div>;
  }

  // Icons array to map over randomly or sequentially
  const icons = [Users, FileText, HelpCircle];

  return (
    <div className="h-full flex flex-col justify-center pb-12 px-8">
      <h2 className="text-4xl font-bold text-center mb-12 text-[#064E3B]">What do you need help with today?</h2>
      
      <div className="flex flex-wrap justify-center gap-8 min-h-[20rem]">
        {counter.service_types?.map((service: any, index: number) => {
          const IconComponent = icons[index % icons.length];
          return (
            <button 
              key={service.id}
              onClick={() => handleSelect(service.id)}
              className="bg-white border-2 border-[#E2E8F0] hover:border-[#10B981] p-12 rounded-[2rem] flex flex-col items-center justify-center gap-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-all active:scale-95 group w-72"
            >
              <div className="w-24 h-24 bg-[#ECFDF5] rounded-full flex items-center justify-center group-hover:bg-[#10B981] transition-colors">
                <IconComponent className="w-12 h-12 text-[#10B981] group-hover:text-white transition-colors" />
              </div>
              <span className="text-2xl font-bold text-[#0F172A] text-center">{service.name}</span>
            </button>
          );
        })}
        {(!counter.service_types || counter.service_types.length === 0) && (
          <div className="text-[#64748B] text-xl font-medium mt-12">No services available.</div>
        )}
      </div>
    </div>
  );
}
