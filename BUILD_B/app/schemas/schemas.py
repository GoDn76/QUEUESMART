from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# --- Auth & Token Schemas ---

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SessionLoginResponse(TokenResponse):
    session_id: str
    counter_id: Optional[int] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# --- Organization Schemas ---

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)


class OrganizationOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


# --- Counter Schemas ---

class CounterCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    queue_type: str = Field(..., pattern="^(FIFO|PRIORITY|HYBRID)$")
    qr_slug: Optional[str] = Field(None, pattern="^[a-zA-Z0-9-_]+$")


class CounterOut(BaseModel):
    id: int
    organization_id: int
    name: str
    queue_type: str
    qr_slug: str
    active: bool

    class Config:
        from_attributes = True


# --- Service Type Schemas ---

class ServiceTypeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    estimated_duration_minutes: int = Field(default=15, ge=1)
    priority_weight: int = Field(default=10, ge=1)


class ServiceTypeOut(BaseModel):
    id: int
    organization_id: int
    name: str
    estimated_duration_minutes: int
    priority_weight: int

    class Config:
        from_attributes = True


# --- Operator Schemas ---

class OperatorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    counter_id: Optional[int] = None


class OperatorOut(BaseModel):
    id: int
    organization_id: int
    name: str
    email: EmailStr
    counter_id: Optional[int]

    class Config:
        from_attributes = True


class OperatorAdminOut(OperatorOut):
    active: bool
    last_login_at: Optional[datetime]
    failed_login_attempts: int
    session_version: int


class OperatorUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    counter_id: Optional[int] = None
    active: Optional[bool] = None


class OperatorResetPassword(BaseModel):
    new_password: str = Field(..., min_length=6)


# --- Token Schemas ---

class TokenCreate(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")  # E.164 phone format
    service_type_id: int


class TokenOut(BaseModel):
    id: int
    sequence_number: int
    token_number: str
    counter_id: int
    service_type_id: int
    customer_name: str
    customer_phone: str
    status: str
    priority_score: int
    created_at: datetime
    called_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    near_notification_sent: bool = False
    your_turn_notification_sent: bool = False

    class Config:
        from_attributes = True


# --- Display Board & Public View ---

class DisplayBoardOut(BaseModel):
    counter_id: int
    counter_name: str
    queue_type: str
    current_token: Optional[TokenOut] = None
    upcoming_tokens: List[TokenOut]
    queue_length: int
    estimated_wait_minutes: int


# --- Analytics Schemas ---

class MetricBreakdown(BaseModel):
    average_wait_minutes: float
    average_service_minutes: float
    total_tokens: int
    dropped_tokens: int
    drop_off_rate: float
    counter_utilization: Optional[float] = None


class AnalyticsSummaryOut(BaseModel):
    active_tokens: int
    completed_today: int
    waiting_count: int
    drop_off_rate: float
    overall: MetricBreakdown
    by_counter: Dict[str, MetricBreakdown]
    by_service_type: Dict[str, MetricBreakdown]


# --- Public Queue Status Out ---

class PublicQueueStatusOut(BaseModel):
    counter_id: int
    counter_name: str
    queue_type: str
    current_token: Optional[TokenOut] = None
    people_ahead: int
    estimated_wait_minutes: int
    suggested_low_traffic_window: str
    service_types: List[ServiceTypeOut]


# --- Public Queue Mini Status ---

class PublicQueueMiniStatus(BaseModel):
    current_token: Optional[str] = None
    waiting_count: int
    estimated_wait: int
    queue_type: str


# --- Operator assisted schemas ---

class OperatorAddTokenRequest(BaseModel):
    counter_id: int
    service_type_id: int
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")


class EscalateTokenRequest(BaseModel):
    new_priority_weight: int = Field(..., ge=1, le=1000)
    reason: str = Field(..., min_length=2, max_length=255)


# --- DisplayBoard Schemas ---

class DisplayBoardCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    board_type: str = Field(..., pattern="^(COUNTER|ORGANIZATION)$")
    counter_id: Optional[int] = None


class DisplayBoardCreateResponse(BaseModel):
    display_id: str
    display_token: str
    display_url: str


class CounterDisplayState(BaseModel):
    counter_id: int
    counter_name: str
    queue_type: str
    active: bool
    current_token: Optional[TokenOut] = None
    upcoming_tokens: List[TokenOut]
    queue_length: int
    estimated_wait_minutes: int


class DisplayBoardDetailsResponse(BaseModel):
    display_id: str
    name: str
    board_type: str
    organization_id: int
    organization_name: str
    counter_id: Optional[int] = None
    counter_state: Optional[CounterDisplayState] = None
    all_counters_state: Optional[List[CounterDisplayState]] = None
    overall_waiting_count: int
    overall_completed_today: int


# --- Admin UI Dashboards ---

class AdminCounterStatusResponse(BaseModel):
    counter_id: int
    counter_name: str
    operator: Optional[str] = None
    session_active: bool
    last_seen: Optional[str] = None
    queue_length: int


# --- Token Migration Schemas ---

class TokenMigrationRequestCreate(BaseModel):
    token_id: int
    from_counter_id: int
    to_counter_id: int
    predicted_time_saved: Optional[int] = None
    reason: Optional[str] = None


class TokenMigrationRequestOut(BaseModel):
    id: int
    token_id: int
    from_counter_id: int
    to_counter_id: int
    predicted_time_saved: Optional[int]
    reason: Optional[str]
    status: str
    created_by_id: Optional[int]
    source_operator_approved: bool
    destination_operator_approved: bool
    approved_by_id: Optional[int]
    approved_at: Optional[datetime]
    executed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class TokenMigrationApproval(BaseModel):
    approve: bool



