# QueueMind Backend API Documentation

Welcome to the QueueMind Backend API specification. This document outlines every REST API endpoint, WebSocket connection, authorization requirement, and schema definition for the system.

---

## 🔑 Authentication & Scopes

The backend uses JWT (JSON Web Tokens) for authentication. Send the token in the `Authorization` header of your requests:
```http
Authorization: Bearer <jwt_token>
```

### Roles and Subject Formats
The system decodes the `sub` claim in the JWT to determine access permissions:
1. **Organization Admin**: Subject is formatted as `org:<org_id>`. Exposes admin management endpoints.
2. **Counter Operator**: Subject is formatted as `operator:<operator_id>`. Requires an active session lock for mutation routes.

---

## 📂 API Reference Index

### 🔐 Authentication Router (`/api/v1/auth`)

#### 1. Register Organization
* **Method:** `POST`
* **Path:** `/api/v1/auth/register`
* **Authentication:** None
* **Request Body (`OrganizationCreate`):**
  ```json
  {
    "name": "City Hospital",
    "email": "admin@cityhospital.com",
    "password": "securepassword"
  }
  ```
* **Response (`OrganizationOut`):**
  ```json
  {
    "id": 1,
    "name": "City Hospital",
    "email": "admin@cityhospital.com",
    "created_at": "2026-06-11T13:17:09"
  }
  ```
* **Description:** Register a new organization. Email must be unique.

#### 2. Organization Login
* **Method:** `POST`
* **Path:** `/api/v1/auth/login`
* **Authentication:** None
* **Request Body (`UserLogin`):**
  ```json
  {
    "email": "admin@cityhospital.com",
    "password": "securepassword"
  }
  ```
* **Response (`TokenResponse`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
* **Description:** Log in as an organization administrator and receive a JWT.

#### 3. Operator Login
* **Method:** `POST`
* **Path:** `/api/v1/auth/operator/login`
* **Authentication:** None
* **Request Body (`UserLogin`):**
  ```json
  {
    "email": "operator@cityhospital.com",
    "password": "operatorpassword"
  }
  ```
* **Response (`SessionLoginResponse`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "session_id": "a3871b14-4ca6-4f79-90f0-951cf157293d"
  }
  ```
* **Description:** Log in as an operator. Authenticates credentials, checks rate limits, acquires a Redis session lock (`counter_active:<counter_id>`), and returns a session-versioned token.

---

### 🛡️ Admin Operations Router (`/api/v1/admin`)
> [!IMPORTANT]
> All endpoints in this router require **Organization Admin** authentication.

#### 1. Create Operator
* **Method:** `POST`
* **Path:** `/api/v1/admin/operators/create`
* **Request Body (`OperatorCreate`):**
  ```json
  {
    "name": "Jane Doe",
    "email": "jane@cityhospital.com",
    "password": "operatorpassword",
    "counter_id": 1
  }
  ```
* **Response (`OperatorAdminOut`):**
  ```json
  {
    "id": 2,
    "organization_id": 1,
    "name": "Jane Doe",
    "email": "jane@cityhospital.com",
    "counter_id": 1,
    "active": true,
    "last_login_at": null,
    "failed_login_attempts": 0,
    "password_changed_at": null,
    "session_version": 1
  }
  ```

#### 2. Reset Operator Password
* **Method:** `POST`
* **Path:** `/api/v1/admin/operators/reset-password/{operator_id}`
* **Request Body (`OperatorResetPassword`):**
  ```json
  {
    "new_password": "newsecurepassword"
  }
  ```
* **Response (`OperatorAdminOut`):** Returns the updated operator metadata.
* **Description:** Resets the password, increments `session_version` (which automatically invalidates the operator's active JWT), and creates a `PASSWORD_RESET` audit log.

#### 3. Disable Operator
* **Method:** `POST`
* **Path:** `/api/v1/admin/operators/disable/{operator_id}`
* **Response (`OperatorAdminOut`):** Returns the updated operator metadata with `active=false`.
* **Description:** Disables an operator's account and increments their `session_version` to block subsequent token usage.

#### 4. Enable Operator
* **Method:** `POST`
* **Path:** `/api/v1/admin/operators/enable/{operator_id}`
* **Response (`OperatorAdminOut`):** Returns the updated operator metadata with `active=true`.

#### 5. List All Operators
* **Method:** `GET`
* **Path:** `/api/v1/admin/operators`
* **Response:** `List[OperatorAdminOut]`

#### 6. List Counters Status
* **Method:** `GET`
* **Path:** `/api/v1/admin/counters`
* **Response:** `List[AdminCounterStatusResponse]`
  ```json
  [
    {
      "counter_id": 1,
      "counter_name": "OPD Counter A",
      "session_active": true,
      "queue_length": 5,
      "operator": "Jane Doe",
      "last_seen": "2026-06-11T13:17:09"
    }
  ]
  ```
* **Description:** View all counters, their active operator, length of the queue, and session lock state.

#### 7. Force Release Counter Lock (Takeover)
* **Method:** `POST`
* **Path:** `/api/v1/admin/counters/{counter_id}/force-takeover`
* **Response:**
  ```json
  {
    "status": "ok",
    "message": "Lock released for counter 1"
  }
  ```
* **Description:** Admin override to force-release an operator's counter lock from Redis, freeing it for other operators.

---

### 🖥️ Counter Management Router (`/api/v1/counters`)
> [!IMPORTANT]
> Endpoints require **Organization Admin** authentication.

#### 1. Create Counter
* **Method:** `POST`
* **Path:** `/api/v1/counters/`
* **Request Body (`CounterCreate`):**
  ```json
  {
    "name": "General OPD A",
    "queue_type": "HYBRID",
    "qr_slug": "general-opd-a"
  }
  ```
  * *Allowed queue types:* `FIFO`, `PRIORITY`, `HYBRID`
* **Response (`CounterOut`):**
  ```json
  {
    "id": 1,
    "organization_id": 1,
    "name": "General OPD A",
    "queue_type": "HYBRID",
    "qr_slug": "general-opd-a",
    "active": true
  }
  ```

#### 2. List Counters
* **Method:** `GET`
* **Path:** `/api/v1/counters/`
* **Response:** `List[CounterOut]`

#### 3. Assign Operator to Counter
* **Method:** `POST`
* **Path:** `/api/v1/counters/{counter_id}/operators`
* **Request Body (`OperatorCreate`)**
* **Response (`OperatorOut`)**

#### 4. List Assigned Operators
* **Method:** `GET`
* **Path:** `/api/v1/counters/{counter_id}/operators`
* **Response:** `List[OperatorOut]`

---

### 🏷️ Service Types Router (`/api/v1/services`)
> [!IMPORTANT]
> Endpoints require **Organization Admin** authentication.

#### 1. Create Service Type
* **Method:** `POST`
* **Path:** `/api/v1/services/`
* **Request Body (`ServiceTypeCreate`):**
  ```json
  {
    "name": "Consultation",
    "estimated_duration_minutes": 15,
    "priority_weight": 20
  }
  ```
* **Response (`ServiceTypeOut`):** Returns the created Service Type.

#### 2. List Service Types
* **Method:** `GET`
* **Path:** `/api/v1/services/`
* **Response:** `List[ServiceTypeOut]`

---

### 📊 Operator Dashboard Router (`/api/v1/operator`)
> [!IMPORTANT]
> Mutation endpoints require **Active Operator Session** authentication (valid operator token and matching Redis lock). Read-only endpoints require a valid **Operator** token.

#### 1. Call Next Customer
* **Method:** `POST`
* **Path:** `/api/v1/operator/call-next`
* **Response (`TokenOut`):**
  ```json
  {
    "id": 5,
    "sequence_number": 4,
    "token_number": "T-004",
    "counter_id": 1,
    "service_type_id": 1,
    "customer_name": "Bob Martin",
    "customer_phone": "+15551234",
    "status": "IN_PROGRESS",
    "priority_score": 20,
    "created_at": "2026-06-11T13:10:00",
    "called_at": "2026-06-11T13:17:10",
    "completed_at": null
  }
  ```
* **Description:** Pops the next customer according to the counter's sorting algorithms, updates status to `IN_PROGRESS`, sets the current serving token in Redis, and broadcasts updates.

#### 2. Complete Serving
* **Method:** `POST`
* **Path:** `/api/v1/operator/complete/{token_id}`
* **Response (`TokenOut`):** Returns token with status updated to `COMPLETED`.

#### 3. Skip Serving
* **Method:** `POST`
* **Path:** `/api/v1/operator/skip/{token_id}`
* **Response (`TokenOut`):** Returns token with status updated to `SKIPPED`.

#### 4. List Current Queue
* **Method:** `GET`
* **Path:** `/api/v1/operator/current-queue`
* **Response:** `List[TokenOut]`
* **Description:** Fetches all currently waiting customers in this operator's queue, sorted according to sorting algorithm scores.

#### 5. Get Current Serving Token
* **Method:** `GET`
* **Path:** `/api/v1/operator/current-serving`
* **Response:** `Optional[TokenOut]`

#### 6. Add Walk-In Customer
* **Method:** `POST`
* **Path:** `/api/v1/operator/add-token`
* **Request Body (`OperatorAddTokenRequest`):**
  ```json
  {
    "counter_id": 1,
    "customer_name": "Alice Smith",
    "customer_phone": "+15559876",
    "service_type_id": 1
  }
  ```
* **Response (`TokenOut`):** Created token details.

#### 7. Escalate Token Priority
* **Method:** `POST`
* **Path:** `/api/v1/operator/escalate-token/{token_id}`
* **Request Body (`EscalateTokenRequest`):**
  ```json
  {
    "new_priority_weight": 80,
    "reason": "Vulnerable Patient"
  }
  ```
* **Response (`TokenOut`):** Escalated token details.
* **Description:** Recalculates and updates the token's priority, re-sorting it in Redis and triggering a position recalculation.

#### 8. Renew Session Heartbeat
* **Method:** `POST`
* **Path:** `/api/v1/operator/heartbeat`
* **Response:** `{"status": "ok", "message": "Heartbeat refreshed"}`
* **Description:** Renews the operator's Redis lock TTL (default 90 seconds). Must be polled regularly by operator dashboards.

#### 9. Logout
* **Method:** `POST`
* **Path:** `/api/v1/operator/logout`
* **Response:** `{"status": "ok", "message": "Logged out successfully"}`
* **Description:** Releases the Redis session lock and publishes an `OPERATOR_LOGOUT` event.

---

### 📈 Analytics Router (`/api/v1/analytics`)

#### 1. Retrieve Organization Analytics Summary
* **Method:** `GET`
* **Path:** `/api/v1/analytics/summary`
* **Authentication:** Organization Admin
* **Response (`AnalyticsSummaryOut`):**
  ```json
  {
    "active_tokens": 12,
    "completed_today": 45,
    "waiting_count": 8,
    "drop_off_rate": 0.05,
    "overall": {
      "average_wait_minutes": 8.4,
      "average_service_minutes": 12.1,
      "total_tokens": 60,
      "dropped_tokens": 3,
      "drop_off_rate": 0.05
    },
    "by_counter": {
      "OPD Counter A": {
        "average_wait_minutes": 6.2,
        "average_service_minutes": 10.5,
        "total_tokens": 30,
        "dropped_tokens": 1,
        "drop_off_rate": 0.033
      }
    },
    "by_service_type": {
      "General OPD": {
        "average_wait_minutes": 7.5,
        "average_service_minutes": 11.2,
        "total_tokens": 40,
        "dropped_tokens": 2,
        "drop_off_rate": 0.05
      }
    }
  }
  ```

---

### 📺 Display Board Router (`/api/v1/display`)

#### 1. Register Display Board
* **Method:** `POST`
* **Path:** `/api/v1/display/create`
* **Authentication:** Staff/Admin (either Org or Operator credentials)
* **Request Body (`DisplayBoardCreate`):**
  ```json
  {
    "name": "Main Lobby Display",
    "board_type": "ORGANIZATION",
    "counter_id": null
  }
  ```
  * *Allowed board types:* `COUNTER`, `ORGANIZATION`
* **Response (`DisplayBoardCreateResponse`):**
  ```json
  {
    "display_id": "d40ec12e-033d-4c73-8b53-52a2cee48767",
    "display_token": "Ut9u253KgV0bpq8XIUdQp62ZYcLb95nfI2uqGeovUNQ",
    "display_url": "https://queuemind.app/display/d40ec12e-033d-4c73-8b53-52a2cee48767"
  }
  ```

#### 2. Get Display Board State
* **Method:** `GET`
* **Path:** `/api/v1/display/{display_id}/state`
* **Authentication:** Token Verification
* **Query Parameter:** `access_token=<display_token>` (or `Authorization: Bearer <display_token>`)
* **Response (`DisplayBoardDetailsResponse`):**
  ```json
  {
    "display_id": "d40ec12e-033d-4c73-8b53-52a2cee48767",
    "name": "Main Lobby Display",
    "board_type": "ORGANIZATION",
    "overall_waiting_count": 8,
    "overall_completed_today": 45,
    "all_counters_state": [
      {
        "counter_id": 1,
        "counter_name": "OPD Counter A",
        "current_token": {
          "token_number": "T-004",
          "customer_name": "Bob Martin"
        },
        "waiting_count": 3
      }
    ]
  }
  ```

---

### 🌐 Public Queue Flow Router (`/q`)

#### 1. Get Public Queue Page Status
* **Method:** `GET`
* **Path:** `/q/{qr_slug}`
* **Authentication:** None (Public)
* **Response (`PublicQueueStatusOut`):**
  ```json
  {
    "counter_id": 1,
    "counter_name": "OPD Counter A",
    "queue_type": "HYBRID",
    "current_token": {
      "token_number": "T-004",
      "customer_name": "Bob Martin"
    },
    "people_ahead": 3,
    "estimated_wait_minutes": 45,
    "suggested_low_traffic_window": "2 PM - 4 PM",
    "service_types": [
      {
        "id": 1,
        "name": "General OPD",
        "estimated_duration_minutes": 15,
        "priority_weight": 20
      }
    ]
  }
  ```
* **Description:** Public landing page state for customer check-ins. Calculates wait time forecasts and suggests low-traffic hours.

#### 2. Join Queue
* **Method:** `POST`
* **Path:** `/q/{qr_slug}/join`
* **Authentication:** None (Public)
* **Request Body (`TokenCreate`):**
  ```json
  {
    "customer_name": "Charlie Brown",
    "customer_phone": "+15558765",
    "service_type_id": 1
  }
  ```
* **Response (`TokenOut`):** Newly created ticket/token details.
* **Description:** Public check-in route. Strictly rate-limited to 3 joins per 5 minutes per phone number.

#### 3. Get Specific Token Status
* **Method:** `GET`
* **Path:** `/q/{qr_slug}/status/{token_number}`
* **Authentication:** None (Public)
* **Response (`TokenOut`):** Current status and timing for the ticket.

---

### 🩺 Health Router (`/health`)

#### 1. System Health Status
* **Method:** `GET`
* **Path:** `/health`
* **Authentication:** None
* **Response:**
  * **200 OK** (Overall status is `healthy` or `degraded`):
    ```json
    {
      "status": "healthy",
      "postgres": "UP",
      "redis": "UP",
      "version": "1.0.0",
      "timestamp": "2026-06-11T13:20:00.000000+00:00"
    }
    ```
  * **503 Service Unavailable** (Overall status is `unhealthy`):
    ```json
    {
      "status": "unhealthy",
      "postgres": "DOWN",
      "redis": "UP",
      "version": "1.0.0",
      "timestamp": "2026-06-11T13:20:00.000000+00:00"
    }
    ```

---

## 🔌 WebSockets Reference

WebSockets enable real-time dashboard and board updates. All WebSocket connection endpoints are unauthenticated but scoped by identifiers.

### 1. Counter WebSocket Room
* **Endpoint:** `/ws/counter/{counter_id}`
* **Scope:** Real-time updates for operator dashboards. Receives push events like:
  * `TOKEN_JOINED`, `QUEUE_ADVANCED`, `TOKEN_COMPLETED`, `TOKEN_SKIPPED`, `TOKEN_ESCALATED`

### 2. Display Board WebSocket Room
* **Endpoint:** `/ws/display/{counter_id}`
* **Scope:** Public display updates. Receives push events when the queue updates.

### 3. Organization WebSocket Room
* **Endpoint:** `/ws/organization/{organization_id}`
* **Scope:** Receives organizational metrics transitions for administrator metrics dashboards.

### 4. Targeted User WebSocket Room
* **Endpoint:** `/ws/user/{token_id}`
* **Scope:** Targeted customer notifications. Sends specific shifts and calls:
  * `YOUR_TURN`: Sent when operator calls the customer.
  * `TOKEN_NEAR`: Sent when the customer is in the top 3 (O(1) look-ahead).
  * `TOKEN_ESCALATED`: Sent when the customer's priority changes.
