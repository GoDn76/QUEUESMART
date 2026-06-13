import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { useQuery } from "@tanstack/react-query";
import { fetchAnalyticsSummary } from "@/api/admin";

import { fetchRushHours } from "@/api/admin";

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['adminAnalytics'],
    queryFn: fetchAnalyticsSummary,
    retry: false,
  });

  const { data: rushHoursData } = useQuery({
    queryKey: ['adminRushHours'],
    queryFn: fetchRushHours,
    retry: false,
  });

  const stats = data || {
    active_tokens: 0,
    completed_today: 0,
    waiting_count: 0,
    drop_off_rate: 0
  };

  const serviceData = data?.by_service_type 
    ? Object.entries(data.by_service_type).map(([name, metrics]) => ({
        name,
        count: (metrics as any).total_tokens || 0
      }))
    : [];

  const visitorData = rushHoursData?.peak_hours 
    ? rushHoursData.peak_hours.map((ph: any) => ({
        time: `${ph.time_block}:00`,
        visitors: Math.round(ph.predicted_volume)
      }))
    : [];


  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-2xl text-white font-medium tracking-tight">Overview</h3>
        <p className="text-[#A1A1AA] text-sm font-medium mt-1">Real-time status of your queues and operators.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-[#111113] border border-white/5 rounded-lg p-6 flex flex-col justify-between hover:border-[#27272A] transition-colors">
          <h4 className="text-[#A1A1AA] text-sm font-medium">Active Queues</h4>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-4xl text-white font-medium tracking-tight">{isLoading ? '...' : stats.active_tokens}</span>
            <span className="text-xs font-medium text-[#4ADE80]">+4 from last hour</span>
          </div>
        </div>
        
        <div className="bg-[#111113] border border-white/5 rounded-lg p-6 flex flex-col justify-between hover:border-[#27272A] transition-colors">
          <h4 className="text-[#A1A1AA] text-sm font-medium">Completed Today</h4>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-4xl text-white font-medium tracking-tight">{isLoading ? '...' : stats.completed_today}</span>
            <span className="text-xs font-medium text-[#4ADE80]">+12% from yesterday</span>
          </div>
        </div>
        
        <div className="bg-[#111113] border border-white/5 rounded-lg p-6 flex flex-col justify-between hover:border-[#27272A] transition-colors">
          <h4 className="text-[#A1A1AA] text-sm font-medium flex items-center gap-2">
            Waiting Currently
            <span className="w-2 h-2 rounded-full bg-[#FACC15] shadow-[0_0_8px_rgba(250,204,21,0.5)]"></span>
          </h4>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-4xl text-white font-medium tracking-tight">{isLoading ? '...' : stats.waiting_count}</span>
            <span className="text-xs font-medium text-[#A1A1AA]">Slightly elevated</span>
          </div>
        </div>
        
        <div className="bg-[#111113] border border-white/5 rounded-lg p-6 flex flex-col justify-between hover:border-[#27272A] transition-colors">
          <h4 className="text-[#A1A1AA] text-sm font-medium">Drop-off Rate</h4>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-4xl text-white font-medium tracking-tight">{isLoading ? '...' : `${stats.drop_off_rate}%`}</span>
            <span className="text-xs font-medium text-[#4ADE80]">-0.5% from last week</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#111113] border border-white/5 rounded-lg p-6 flex flex-col">
          <div className="mb-6">
            <h4 className="text-white font-medium tracking-tight">Visitor Traffic</h4>
            <p className="text-[#A1A1AA] text-sm font-medium">Visitors per hour today</p>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={visitorData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorVisitors" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4ADE80" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#4ADE80" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#27272A" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="time" stroke="#71717A" fontSize={12} tickLine={false} axisLine={false} dy={10} />
                <YAxis stroke="#71717A" fontSize={12} tickLine={false} axisLine={false} />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: '#09090B', border: '1px solid #27272A', borderRadius: '6px', color: '#FFF' }}
                  itemStyle={{ color: '#4ADE80' }}
                />
                <Area type="monotone" dataKey="visitors" stroke="#4ADE80" strokeWidth={2} fillOpacity={1} fill="url(#colorVisitors)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[#111113] border border-white/5 rounded-lg p-6 flex flex-col">
          <div className="mb-6">
            <h4 className="text-white font-medium tracking-tight">Service Distribution</h4>
            <p className="text-[#A1A1AA] text-sm font-medium">Total visitors by service type</p>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={serviceData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="#27272A" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" stroke="#71717A" fontSize={12} tickLine={false} axisLine={false} dy={10} />
                <YAxis stroke="#71717A" fontSize={12} tickLine={false} axisLine={false} />
                <RechartsTooltip 
                  cursor={{ fill: '#1A1A1A' }} 
                  contentStyle={{ backgroundColor: '#09090B', border: '1px solid #27272A', borderRadius: '6px', color: '#FFF' }}
                />
                {/* Changed from a solid block to a subtle fill with stroke */}
                <Bar dataKey="count" fill="#4ADE80" fillOpacity={0.15} stroke="#4ADE80" strokeWidth={1} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
