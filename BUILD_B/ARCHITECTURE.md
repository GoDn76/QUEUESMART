# QueueMind Architecture Documentation

This document describes the architectural layout of the **QueueMind Smart Queue Platform**, explaining the consistency design between PostgreSQL and Redis, and illustrating the event-driven sequence diagrams.

---

## Redis vs PostgreSQL Responsibilities

QueueMind utilizes a **Hybrid Dual-Store Architecture** to support extreme write throughput, concurrent race-safety, and horizontally scalable real-time notifications:

| Metric / Operational State | PostgreSQL (Source of Truth) | Redis (Real-Time Operational Layer) |
| :--- | :--- | :--- |
| **System of Record** | All persistent metadata (Organizations, ServiceTypes, Counters, Operators, Tokens, QueueEvents). | None. Used strictly for fast-access runtime operational data. |
| **Active Queue state** | Backup store. Serves as fallback query sorting if Redis is offline. | **Primary operational state** managed as a **Sorted Set (ZSET)**. |
| **Currently serving state** | Persistent ticket status (`IN_PROGRESS`). | Instant lookup cache `current_token:{counter_id}` for fast lobby dashboards. |
| **Live Metrics & Analytics** | Historical aggregation queries for admin summaries. | Real-time incrementing counters for fast dashboard rendering. |
| **Rate Limiting** | None. | **Sliding Window Rate Limiter** via Redis Sorted Sets. |
| **Pub/Sub Broker** | None. | Channel broker distributing events to horizontal server nodes. |

---

## Consistency & Graceful Degradation Strategy

1. **Write-Through Persistence**:
   Every state modification (joining, calling, completing, skipping) begins with a PostgreSQL transaction commit, assuring ACID durability. After database success, Redis state is updated and EventBus triggers.

2. **Startup Recovery (`RedisRecoveryService`)**:
   During application initialization, the service aggressively reads from PostgreSQL to rebuild all active Redis `WAITING` queues, `IN_PROGRESS` current token caches, and metric counters, resolving any conflicting duplicate token states using chronological tiebreakers.

3. **Explicit Idempotency**:
   Queue operations (`call_next`, `complete_token`, `skip_token`, `escalate_token`) enforce strict database state preconditions. This ensures that accidental double-clicks or retries cannot cause a queue to advance twice or a completed token to be processed again.

4. **Graceful Fallback Mode**:
   If Redis goes offline, the `QueueEngine` catches connection warnings and operates in **degraded mode**:
   - **Queue Popping**: Queries PostgreSQL directly for `WAITING` tickets sorted according to Counter logic.
   - **Rate Limiting**: Fails open, logging warnings but allowing customers to register.
   - **Live Metrics**: Resolves counts via DB aggregate counts.
   - **WebSockets**: Falls back to process-local memory room broadcasts.

---

## Sequence Diagrams

### 1. Join Queue Flow

```mermaid
sequence_loop "Customer Joins"
    autonumber
    actor Customer
    participant FastAPI as FastAPI Instance
    database Redis as Redis Server
    database Postgres as PostgreSQL DB

    Customer ->> FastAPI: POST /q/{qr_slug}/join (Name, Phone, ServiceType)
    activate FastAPI
    
    FastAPI ->> Redis: ZSET sliding window check (rate_limit:{phone})
    Redis -->> FastAPI: count (e.g. 1 ticket)
    
    FastAPI ->> Postgres: INSERT INTO tokens (status = WAITING)
    Postgres -->> FastAPI: token.id (Identity sequence generated)
    
    FastAPI ->> Postgres: UPDATE token SET token_number = T-{token.id}
    Postgres -->> FastAPI: OK
    
    FastAPI ->> Redis: ZADD queue:{counter_id} (token_id, score)
    FastAPI ->> Redis: INCR metrics:org:{org_id}:waiting_count
    
    FastAPI ->> Postgres: INSERT INTO queue_events (event = JOINED)
    Postgres -->> FastAPI: OK
    
    FastAPI ->> Redis: PUBLISH counter:{counter_id} (TOKEN_JOINED)
    
    FastAPI -->> Customer: Token details (T-001)
    deactivate FastAPI
```

---

### 2. Call Next Flow

```mermaid
sequence_loop "Operator Calls Next"
    autonumber
    actor Operator
    participant FastAPI as FastAPI Instance
    database Redis as Redis Server
    database Postgres as PostgreSQL DB

    Operator ->> FastAPI: POST /api/v1/operator/call-next
    activate FastAPI
    
    FastAPI ->> Redis: ZPOPMIN queue:{counter_id}
    Redis -->> FastAPI: token_id (lowest score)
    
    note over FastAPI: If Redis fails / empty,\nfallback to Postgres sorting
    
    FastAPI ->> Postgres: UPDATE token SET status = IN_PROGRESS, called_at = NOW
    Postgres -->> FastAPI: OK (returns token details)
    
    FastAPI ->> Redis: SET current_token:{counter_id} (token data)
    FastAPI ->> Redis: DECR metrics:org:{org_id}:waiting_count
    
    FastAPI ->> Postgres: INSERT INTO queue_events (event = CALLED)
    Postgres -->> FastAPI: OK
    
    FastAPI ->> Redis: PUBLISH counter:{counter_id} (TOKEN_CALLED)
    FastAPI ->> Redis: PUBLISH user:{token_id} (YOUR_TURN)
    
    note over FastAPI: Recalculates wait positions\nand notifies remaining users
    FastAPI ->> Redis: PUBLISH user:{other_tokens} (QUEUE_POSITION_CHANGED)
    
    FastAPI -->> Operator: Token details
    deactivate FastAPI
```

---

### 3. Complete Token Flow

```mermaid
sequence_loop "Operator Completes serving"
    autonumber
    actor Operator
    participant FastAPI as FastAPI Instance
    database Redis as Redis Server
    database Postgres as PostgreSQL DB

    Operator ->> FastAPI: POST /api/v1/operator/complete/{token_id}
    activate FastAPI
    
    FastAPI ->> Postgres: UPDATE token SET status = COMPLETED, completed_at = NOW
    Postgres -->> FastAPI: OK
    
    FastAPI ->> Redis: DEL current_token:{counter_id}
    FastAPI ->> Redis: DECR metrics:org:{org_id}:active_tokens
    FastAPI ->> Redis: INCR metrics:org:{org_id}:completed_today
    
    FastAPI ->> Postgres: INSERT INTO queue_events (event = COMPLETED)
    Postgres -->> FastAPI: OK
    
    FastAPI ->> Redis: PUBLISH counter:{counter_id} (TOKEN_COMPLETED)
    
    FastAPI -->> Operator: Token details (status: COMPLETED)
    deactivate FastAPI
```

---

### 4. WebSocket Event Broadcast Flow

```mermaid
sequence_loop "Horizontal Scale Broadcast"
    autonumber
    actor LobbyScreen as Display Board (Node A)
    participant ServerA as FastAPI Node A
    participant Redis as Redis Pub/Sub
    participant ServerB as FastAPI Node B
    actor Operator as Operator (Node B)

    LobbyScreen ->> ServerA: ws://.../ws/display/{counter_id} (Connected)
    ServerA ->> ServerA: Add socket to local display_board_rooms[counter_id]
    
    Operator ->> ServerB: POST /api/v1/operator/call-next
    activate ServerB
    note over ServerB: Performs database & Redis state updates
    ServerB ->> Redis: PUBLISH counter:{counter_id} (TOKEN_CALLED)
    ServerB -->> Operator: Token called
    deactivate ServerB
    
    Redis ->> ServerA: Message received from counter:* pattern
    activate ServerA
    ServerA ->> ServerA: Lookup display_board_rooms[counter_id]
    ServerA ->> LobbyScreen: Send JSON payload (TOKEN_CALLED)
    deactivate ServerA
```
