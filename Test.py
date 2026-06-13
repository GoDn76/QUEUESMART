import requests
import time
import random

BASE_URL = "http://localhost:8000/api/v1"

ORG_EMAIL = "admin-luffy@cityhospital.com"
ORG_PASS = "securepassword"


# =========================
# SAFE REQUEST WRAPPERS
# =========================
def post(url, data, headers=None):
    r = requests.post(url, json=data, headers=headers)
    try:
        res = r.json()
    except:
        res = {"raw": r.text}

    print(f"[POST] {url} → {r.status_code}")

    if r.status_code >= 400:
        print("WARN:", res)
        return None

    return res


def get(url, headers=None):
    r = requests.get(url, headers=headers)
    try:
        res = r.json()
    except:
        res = {"raw": r.text}

    print(f"[GET] {url} → {r.status_code}")
    return res


# =========================
# 1. ORG BOOTSTRAP (SAFE)
# =========================
print("\n=== ORG BOOTSTRAP ===")

post(f"{BASE_URL}/auth/register", {
    "name": "City Hospital",
    "email": ORG_EMAIL,
    "password": ORG_PASS
})

login = post(f"{BASE_URL}/auth/login", {
    "email": ORG_EMAIL,
    "password": ORG_PASS
})

org_token = login["access_token"]
headers = {"Authorization": f"Bearer {org_token}"}


# =========================
# 2. COUNTERS (REUSE FIRST)
# =========================
print("\n=== COUNTERS ===")

counters = get(f"{BASE_URL}/counters/", headers)

counter_a = None
counter_b = None

for c in counters:
    if c["qr_slug"] == "opd-a":
        counter_a = c["id"]
    if c["qr_slug"] == "opd-b":
        counter_b = c["id"]

if not counter_a:
    c = post(f"{BASE_URL}/counters/", {
        "name": "OPD Counter A",
        "queue_type": "HYBRID",
        "qr_slug": "opd-a"
    }, headers)
    counter_a = c["id"]

if not counter_b:
    c = post(f"{BASE_URL}/counters/", {
        "name": "OPD Counter B",
        "queue_type": "FIFO",
        "qr_slug": "opd-b"
    }, headers)
    counter_b = c["id"]


# =========================
# 3. SERVICES (REUSE FIRST)
# =========================
print("\n=== SERVICES ===")

services = get(f"{BASE_URL}/services/", headers)

general = None
emergency = None

for s in services:
    if s["name"] == "General OPD":
        general = s["id"]
    if s["name"] == "Emergency":
        emergency = s["id"]

if not general:
    general = post(f"{BASE_URL}/services/", {
        "name": "General OPD",
        "estimated_duration_minutes": 15,
        "priority_weight": 20
    }, headers)["id"]

if not emergency:
    emergency = post(f"{BASE_URL}/services/", {
        "name": "Emergency",
        "estimated_duration_minutes": 5,
        "priority_weight": 100
    }, headers)["id"]


# =========================
# 4. OPERATORS (SAFE)
# =========================
print("\n=== OPERATORS ===")

post(f"{BASE_URL}/admin/operators/create", {
    "name": "Jane Doe",
    "email": "jane@cityhospital.com",
    "password": "operatorpassword",
    "counter_id": counter_a
}, headers)

post(f"{BASE_URL}/admin/operators/create", {
    "name": "John Smith",
    "email": "john@cityhospital.com",
    "password": "operatorpassword",
    "counter_id": counter_b
}, headers)


# =========================
# 5. OPERATOR LOGIN
# =========================
print("\n=== OPERATOR SESSION ===")

op_login = post(f"{BASE_URL}/auth/operator/login", {
    "email": "jane@cityhospital.com",
    "password": "operatorpassword"
})

op_headers = {
    "Authorization": f"Bearer {op_login['access_token']}"
}


# =========================
# 6. HEARTBEAT (FIX session_active)
# =========================
print("\n=== OPERATOR HEARTBEAT ===")

post(f"{BASE_URL}/operator/heartbeat", {}, op_headers)


# =========================
# 7. AUTO-DETECT PUBLIC ROUTE (FIX 404)
# =========================
print("\n=== PUBLIC ROUTE TEST ===")

slug = "opd-a"

PUBLIC_URLS = [
    f"http://localhost:8000/q/{slug}/join",
    f"{BASE_URL}/q/{slug}/join",
    f"{BASE_URL}/public/q/{slug}/join"
]

PUBLIC_JOIN_URL = None

for url in PUBLIC_URLS:
    test = requests.post(url, json={
        "customer_name": "test",
        "customer_phone": "+910000000000",
        "service_type_id": general
    })

    if test.status_code != 404:
        PUBLIC_JOIN_URL = url
        print("✔ PUBLIC ROUTE FOUND:", url)
        break

if not PUBLIC_JOIN_URL:
    raise Exception("Public queue route not found! Fix backend routing.")


# =========================
# 8. WALK-IN SIMULATION
# =========================
print("\n=== WALK-IN SIMULATION ===")

names = ["Aarav", "Isha", "Rohan", "Neha", "Kabir", "Meera", "Aryan", "Sara"]

for i in range(12):
    name = f"{random.choice(names)}_{i}"
    phone = f"+91{random.randint(7000000000, 9999999999)}"

    service = general if random.random() > 0.25 else emergency

    post(f"{BASE_URL}/operator/add-token", {
        "counter_id": counter_a,
        "customer_name": name,
        "customer_phone": phone,
        "service_type_id": service
    }, op_headers)

    time.sleep(0.15)


# =========================
# 9. PUBLIC USERS
# =========================
print("\n=== PUBLIC QUEUE ===")

for i in range(8):
    post(PUBLIC_JOIN_URL, {
        "customer_name": f"PublicUser_{i}",
        "customer_phone": f"+9198{i}000000",
        "service_type_id": general
    })

    time.sleep(0.15)


# =========================
# 10. EMERGENCY SPIKE
# =========================
print("\n=== EMERGENCY SPIKE ===")

for i in range(5):
    post(f"{BASE_URL}/operator/add-token", {
        "counter_id": counter_a,
        "customer_name": f"Emergency_{i}",
        "customer_phone": f"+91{random.randint(6000000000, 6999999999)}",
        "service_type_id": emergency
    }, op_headers)

    time.sleep(0.1)


# =========================
# 11. LIVE SNAPSHOTS
# =========================
print("\n=== LIVE QUEUE SNAPSHOTS ===")

for _ in range(5):
    data = get(f"{BASE_URL}/admin/counters", headers)
    print("\nSnapshot:", data)
    time.sleep(2)


print("\n=== 🎉 DEMO COMPLETE ===")