import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { fetchAnalyticsSummary, fetchRushHours } from "@/api/admin";

export default function Analytics() {
  const { data: summary, isLoading: isSummaryLoading } = useQuery({
    queryKey: ['analyticsSummary'],
    queryFn: fetchAnalyticsSummary
  });

  const { data: rushHours, isLoading: isRushLoading } = useQuery({
    queryKey: ['analyticsRushHours'],
    queryFn: fetchRushHours
  });

  const isLoading = isSummaryLoading || isRushLoading;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-3xl font-semibold tracking-tight">Analytics</h3>
          <p className="text-muted-foreground text-sm mt-1">Deep dive into performance metrics and historical trends.</p>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-[#A1A1AA]">Loading Analytics Data...</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total Visitors Today</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{summary?.total_customers_today || 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Average Wait Time</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{summary?.average_wait_time_minutes || 0}m</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Peak Drop-off Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{summary?.drop_off_rate_percent || 0}%</div>
                <p className="text-xs text-muted-foreground mt-1">Abandoned queue rate</p>
              </CardContent>
            </Card>
          </div>

          {rushHours && (
            <Card>
              <CardHeader>
                <CardTitle>AI Rush Hour Forecast</CardTitle>
                <CardDescription>Predicted peak busy hours</CardDescription>
              </CardHeader>
              <CardContent>
                {rushHours.peak_hours && rushHours.peak_hours.length > 0 ? (
                  <div className="space-y-4">
                    {rushHours.peak_hours.map((ph: any, i: number) => (
                      <div key={i} className="flex justify-between items-center border-b border-[#27272A] pb-2 last:border-0">
                        <span className="font-medium">{ph.time_block}:00</span>
                        <div className="flex flex-col items-end">
                          <span className="text-sm text-yellow-500 font-bold uppercase">{ph.intensity} Intensity</span>
                          <span className="text-xs text-gray-500">Predicted volume: {ph.predicted_volume.toFixed(1)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#A1A1AA]">No sufficient data for AI forecasting.</p>
                )}
              </CardContent>
            </Card>
          )}

          {summary?.wait_times_by_service && (
             <Card>
              <CardHeader>
                <CardTitle>Wait Time by Service (Today)</CardTitle>
                <CardDescription>Average minutes waited</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {summary.wait_times_by_service.map((item: any, i: number) => (
                     <div key={i} className="flex justify-between items-center">
                        <span className="font-bold">{item.service_type_name}</span>
                        <span>{item.average_wait}m</span>
                     </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
