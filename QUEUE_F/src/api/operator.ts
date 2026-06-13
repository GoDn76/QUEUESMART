import apiClient from "./client";

export const fetchCurrentQueue = async () => {
  const { data } = await apiClient.get('/operator/current-queue');
  return data; // Returns Array<TokenOut>
};

export const fetchCurrentServing = async () => {
  const { data } = await apiClient.get('/operator/current-serving');
  return data; // Returns TokenOut | null
};

export const callNextCustomer = async () => {
  const { data } = await apiClient.post('/operator/call-next');
  return data;
};

export const completeToken = async (tokenId: string | number) => {
  const { data } = await apiClient.post(`/operator/complete/${tokenId}`);
  return data;
};

export const skipToken = async (tokenId: string | number) => {
  const { data } = await apiClient.post(`/operator/skip/${tokenId}`);
  return data;
};

export const escalateToken = async (tokenId: string | number, payload: { new_priority_weight: number, reason: string }) => {
  const { data } = await apiClient.post(`/operator/escalate-token/${tokenId}`, payload);
  return data;
};

export const addWalkIn = async (payload: { counter_id: number, service_type_id: number, customer_name: string, customer_phone: string }) => {
  const { data } = await apiClient.post('/operator/add-token', payload);
  return data;
};

export const sendHeartbeat = async () => {
  const { data } = await apiClient.post('/operator/heartbeat');
  return data;
};

export const logoutOperator = async () => {
  const { data } = await apiClient.post('/operator/logout');
  return data;
};
