import apiClient from "./client";

export const fetchDisplayState = async (displayId: string, token?: string) => {
  const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
  
  if (/^\d+$/.test(displayId)) {
    // Legacy endpoint for Counter ID
    const { data } = await apiClient.get(`/display/${displayId}`);
    return {
      display_id: displayId,
      name: `${data.counter_name} Display`,
      board_type: "COUNTER",
      organization_id: 1,
      organization_name: "QueueMind",
      counter_id: data.counter_id,
      counter_state: {
        counter_id: data.counter_id,
        counter_name: data.counter_name,
        queue_type: data.queue_type,
        active: true,
        current_token: data.current_token,
        upcoming_tokens: data.upcoming_tokens,
        queue_length: data.queue_length,
        estimated_wait_minutes: data.estimated_wait_minutes
      },
      overall_waiting_count: data.queue_length,
      overall_completed_today: 0
    };
  }

  // Modern endpoint for UUID
  const { data } = await apiClient.get(`/display/${displayId}/state`, { headers });
  return data;
};
