// Auth & Organizations
export interface OrganizationOut {
  id: number;
  name: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
}

export interface SessionLoginResponse {
  access_token: string;
  session_id: string;
}

// Admin
export interface OperatorAdminOut {
  id: number;
  organization_id: number;
  name: string;
  email: string;
  counter_id: number;
  active: boolean;
  last_login_at: string | null;
  failed_login_attempts: number;
  password_changed_at: string | null;
  session_version: number;
}

export interface AdminCounterStatusResponse {
  counter_id: number;
  counter_name: string;
  session_active: boolean;
  queue_length: number;
  operator: string;
  last_seen: string;
}

// Counters
export interface CounterOut {
  id: number;
  organization_id: number;
  name: string;
  queue_type: "FIFO" | "PRIORITY" | "HYBRID";
  qr_slug: string;
  active: boolean;
}

// Services
export interface ServiceTypeOut {
  id: number;
  name: string;
  estimated_duration_minutes: number;
  priority_weight: number;
}

// Tokens
export interface TokenOut {
  id: number;
  sequence_number: number;
  token_number: string;
  counter_id: number;
  service_type_id: number;
  customer_name: string;
  customer_phone: string;
  status: "WAITING" | "IN_PROGRESS" | "COMPLETED" | "SKIPPED";
  priority_score: number;
  created_at: string;
  called_at: string | null;
  completed_at: string | null;
}

// Analytics
export interface AnalyticsSummaryOut {
  active_tokens: number;
  completed_today: number;
  waiting_count: number;
  drop_off_rate: number;
  overall: {
    average_wait_minutes: number;
    average_service_minutes: number;
    total_tokens: number;
    dropped_tokens: number;
    drop_off_rate: number;
  };
  by_counter: Record<string, any>;
  by_service_type: Record<string, any>;
}

// Public Queue
export interface PublicQueueStatusOut {
  counter_id: number;
  counter_name: string;
  queue_type: string;
  current_token: {
    token_number: string;
    customer_name: string;
  } | null;
  people_ahead: number;
  estimated_wait_minutes: number;
  suggested_low_traffic_window: string;
  service_types: ServiceTypeOut[];
}

export interface DisplayBoardDetailsResponse {
  display_id: string;
  name: string;
  board_type: "COUNTER" | "ORGANIZATION";
  overall_waiting_count: number;
  overall_completed_today: number;
  all_counters_state: Array<{
    counter_id: number;
    counter_name: string;
    current_token: {
      token_number: string;
      customer_name: string;
    } | null;
    waiting_count: number;
  }>;
}
