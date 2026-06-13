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
