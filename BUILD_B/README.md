# QueueMind - Smart Queue Platform Backend

QueueMind is a production-grade, horizontally scalable, QR-based Smart Queue Platform built using **Python, FastAPI, PostgreSQL, and Redis**. 

It enables organizations (hospitals, colleges, retail counters, etc.) to set up queues and issue QR codes. Customers scan the QR code to join queues instantly without registration. Real-time updates are broadcast dynamically using WebSockets backed by a Redis Pub/Sub EventBus.

---

## Technical Features

- **Concurrency-Safe Token Generation**: Database-native sequences to avoid collisions under high intake volumes.
- **Advanced Queue Sorting**: Supports **FIFO**, **PRIORITY**, and **HYBRID** (Priority Bucket First + FIFO inside bucket) sorting powered by Redis Sorted Sets.
- **Fail-Safe Graceful Degradation**: Seamless SQL-only query fallback if Redis goes offline.
- **WebSocket Room Broadcasts**: Scale-friendly room management (counter, display board, organization, and user rooms) driven by a decoupled Redis EventBus.
- **Sliding-Window Rate Limiting**: Redis-based prevention of queue abuse (max 3 joins / 5 minutes per phone number).
- **Statistical Prediction Engine**: Rule-based insights and wait-time caching to minimize API latency.

---

## Tech Stack

- **Framework**: Python 3.11+ / FastAPI
- **Database**: PostgreSQL (System of Record)
- **Operational Cache/Broker**: Redis (Active state, Metrics, Pub/Sub EventBus)
- **ORM**: SQLAlchemy 2.0 (Asynchronous transactions)
- **Validation**: Pydantic v2
- **Testing**: Pytest & httpx (with SQLite in-memory mock integration tests)

---

## Project Structure

```text
app/
├── api/
│   └── v1/
│       ├── routes/            # REST endpoint routers (auth, operator, public, etc.)
│       └── deps.py            # FastAPI dependency injections & security guards
├── core/
│   ├── config.py              # Settings loading from environment variables
│   ├── security.py            # JWT token creation and password hashing context
│   ├── exceptions.py          # Custom application exceptions hierarchy
│   ├── event_bus.py           # EventBus interface & Redis Pub/Sub implementation
│   └── websocket_manager.py   # WS room manager and Redis channel routes
├── db/
│   ├── session.py             # Async SQLAlchemy engine & session factory
│   └── init_db.py             # PostgreSQL table creator & initial data seeder
├── models/
│   └── models.py              # Declarative SQLAlchemy database schemas
├── schemas/
│   └── schemas.py             # Input/Output Pydantic data validators
├── services/
│   ├── queue_engine.py        # Core queue operations coordinator (Single Source of Truth)
│   ├── auth.py                # Admin / Operator login and register actions
│   ├── prediction.py          # Wait time predictions & peak hours forecasts
│   ├── analytics.py           # Dashboard operational metrics & drop-off rates
│   └── redis_recovery.py      # Startup reconciliation and Redis state rebuild
└── main.py                    # FastAPI entrypoint, lifespan context & WS endpoints
tests/                         # pytest test suite
Dockerfile                     # Application docker builder
docker-compose.yml             # Orchestration of web, db, and redis
```

---

## Getting Started

### Method 1: Running via Docker Compose (Recommended)

1. Clone or copy the project files to your directory.
2. Build and run the services with Docker Compose:
   ```bash
   docker-compose up --build
   ```
   *This commands automatically spins up a PostgreSQL server, a Redis cache server, and binds the FastAPI app to port `8000`.*
3. Open `http://localhost:8000/docs` in your browser to inspect the interactive Swagger API documentation.

### Method 2: Running Locally

1. **Prerequisites**: Ensure you have PostgreSQL and Redis installed and running locally.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment variables template and configure it:
   ```bash
   copy .env.example .env
   # Adjust credentials (e.g. DATABASE_URL, REDIS_URL) to point to your local servers.
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```

---

## Running the Automated Test Suite

The test suite runs using an in-memory SQLite database and a mock Redis client to ensure tests run fast without external server requirements.

Run the tests inside your virtual environment:
```bash
# On Windows:
$env:PYTHONPATH="."
.\venv\Scripts\pytest

# On macOS/Linux:
PYTHONPATH=. pytest
```

---

## REST API Summary

### Public Customer Endpoints (No Authentication)
- `GET /health`: System health and dependency connection status.
- `GET /q/{qr_slug}`: Public page details (Current ticket serving, queue length, estimated wait time, suggested low-traffic times).
- `POST /q/{qr_slug}/join`: Register ticket in the queue.
- `GET /q/{qr_slug}/status/{token_number}`: Fetch status of a specific ticket.

### Display Board Endpoints
- `GET /api/v1/display/{display_id}/state`: Lobby display board data (Requires URL-safe access token).

### Operator Endpoints (Operator JWT Token Required)
- `POST /api/v1/operator/call-next`: Advance the queue (pop next ticket and status transitions).
- `POST /api/v1/operator/complete/{token_id}`: Mark active ticket as resolved.
- `POST /api/v1/operator/skip/{token_id}`: Skip current ticket.
- `GET /api/v1/operator/current-queue`: View waiting queue sorted in real-time.

### Admin/Organization Endpoints (Organization Admin JWT Required)
- `POST /api/v1/auth/register`: Provision a new organization.
- `POST /api/v1/auth/login`: Administrative login.
- `POST /api/v1/counters/`: Register a counter.
- `POST /api/v1/counters/{counter_id}/operators`: Add an operator.
- `POST /api/v1/services/`: Add queue ServiceTypes.
- `GET /api/v1/analytics/summary`: View dashboard analytics (Drop-off rates, service speeds, wait times).

---

## WebSocket Channel Rooms

Clients can subscribe to the following rooms for instant updates:

- **Display Boards**: `ws://localhost:8000/ws/display/{counter_id}` (Receives `TOKEN_CALLED`, `TOKEN_COMPLETED`, etc.)
- **Operator Dashboard**: `ws://localhost:8000/ws/counter/{counter_id}`
- **Organization Metrics**: `ws://localhost:8000/ws/organization/{organization_id}`
- **Targeted User Updates**: `ws://localhost:8000/ws/user/{token_id}` (Receives `YOUR_TURN`, `TOKEN_NEAR`, `QUEUE_POSITION_CHANGED`)

---

## Architecture Diagrams

For database persistence mechanics, caching design, and Pub/Sub message-routing sequences, please review [ARCHITECTURE.md](file:///c:/Users/Gaurav%20Urmaliya/Downloads/QUEUESMART/ARCHITECTURE.md).
