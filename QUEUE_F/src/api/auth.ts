import apiClient from "./client";
import { useAuthStore } from "@/store/authStore";

export const registerAdmin = async (payload: { name: string; email: string; password: string }) => {
  const { data } = await apiClient.post("/auth/register", payload);
  return data;
};

export const login = async (email: string, password: string, type: 'ADMIN' | 'OPERATOR') => {
  try {
    const endpoint = type === 'ADMIN' ? "/auth/login" : "/auth/operator/login";
    
    // Per documentation: Body is JSON, not URL encoded.
    const response = await apiClient.post(endpoint, {
      email,
      password,
    });
    
    const { access_token, session_id, counter_id } = response.data;
    const authStore = useAuthStore.getState();
    
    if (type === 'ADMIN') {
      authStore.loginAdmin(access_token);
    } else {
      authStore.loginOperator(access_token, session_id, counter_id);
    }

    return { role: type, session_id, counter_id };
  } catch (error) {
    console.error("Login Error", error);
    throw error;
  }
};
