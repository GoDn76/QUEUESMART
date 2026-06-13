import apiClient from "./client";

export const fetchHealth = async () => {
  const { data } = await apiClient.get('/health');
  return data;
};
