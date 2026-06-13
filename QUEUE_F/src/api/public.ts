import axios from "axios";

// 1. Get the base URL (e.g., "http://localhost:8000/api/v1")
const envUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// 2. Safely split and keep only the domain/port (e.g., "http://localhost:8000")
const publicBaseUrl = envUrl.split('/api')[0];

const publicApiClient = axios.create({
  baseURL: publicBaseUrl, 
  headers: {
    "Content-Type": "application/json",
  },
});

export const fetchCounterDetails = async (qrSlug: string) => {
  const { data } = await publicApiClient.get(`/q/${qrSlug}`);
  return data;
};

export const joinQueue = async (qrSlug: string, payload: { customer_name: string, customer_phone: string, service_type_id: number }) => {
  const { data } = await publicApiClient.post(`/q/${qrSlug}/join`, payload);
  return data;
};

export const fetchTicketStatus = async (qrSlug: string, tokenNumber: string) => {
  const { data } = await publicApiClient.get(`/q/${qrSlug}/status/${tokenNumber}`);
  return data;
};

