import apiClient from "./client";

export interface CounterPayload {
  name: string;
  queue_type: "FIFO" | "PRIORITY" | "HYBRID";
  // qr_slug is omitted as requested (backend generates it)
}

export const fetchCounters = async () => {
  const { data } = await apiClient.get('/counters/');
  return data;
};

export const createCounter = async (payload: CounterPayload) => {
  const { data } = await apiClient.post('/counters/', payload);
  return data;
};

export const fetchCounterOperators = async (counterId: number) => {
  const { data } = await apiClient.get(`/counters/${counterId}/operators`);
  return data;
};

export const assignOperatorToCounter = async (counterId: number, operatorId: number) => {
  const { data } = await apiClient.post(`/counters/${counterId}/operators`, { operator_id: operatorId });
  return data;
};
