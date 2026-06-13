import apiClient from "./client";
import type { AnalyticsSummaryOut, AdminCounterStatusResponse, OperatorAdminOut, ServiceTypeOut } from "@/types/api";

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummaryOut> {
  const { data } = await apiClient.get("/analytics/summary");
  return data;
}

export async function fetchCountersStatus(): Promise<AdminCounterStatusResponse[]> {
  const { data } = await apiClient.get("/admin/counters");
  return data;
}

export async function fetchOperators(): Promise<OperatorAdminOut[]> {
  const { data } = await apiClient.get("/admin/operators");
  return data;
}

export async function fetchServices(): Promise<ServiceTypeOut[]> {
  const { data } = await apiClient.get("/services/");
  return data;
}

export async function createService(payload: { name: string; estimated_duration_minutes: number; priority_weight: number }) {
  const { data } = await apiClient.post("/services/", payload);
  return data;
}

export async function createOperator(payload: { name: string; email: string; password?: string; counter_id?: number }) {
  const { data } = await apiClient.post("/admin/operators/create", payload);
  return data;
}

export async function fetchRushHours() {
  const { data } = await apiClient.get("/analytics/forecast/rush-hours");
  return data;
}

export async function fetchPendingMigrations() {
  const { data } = await apiClient.get("/migrations/pending");
  return data;
}

export async function approveAdminMigration(migrationId: number) {
  const { data } = await apiClient.post(`/migrations/${migrationId}/approve`);
  return data;
}

export async function rejectAdminMigration(migrationId: number) {
  const { data } = await apiClient.post(`/migrations/${migrationId}/reject`);
  return data;
}

export async function resetOperatorPassword(operatorId: number, payload: { new_password: string }) {
  const { data } = await apiClient.post(`/admin/operators/reset-password/${operatorId}`, payload);
  return data;
}

export async function disableOperator(operatorId: number) {
  const { data } = await apiClient.post(`/admin/operators/disable/${operatorId}`);
  return data;
}

export async function enableOperator(operatorId: number) {
  const { data } = await apiClient.post(`/admin/operators/enable/${operatorId}`);
  return data;
}

export async function deleteOperator(operatorId: number) {
  const { data } = await apiClient.delete(`/admin/operators/${operatorId}`);
  return data;
}

export async function fetchCounterStatus(counterId: number): Promise<AdminCounterStatusResponse> {
  const { data } = await apiClient.get(`/admin/counters/${counterId}/status`);
  return data;
}

export async function forceTakeoverCounter(counterId: number) {
  const { data } = await apiClient.post(`/admin/counters/${counterId}/force-takeover`);
  return data;
}
