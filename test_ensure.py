import requests
import json

BASE = "http://localhost:5050"

# Test 1: Sprawdź czy backend żyje
try:
    r = requests.get(f"{BASE}/api/products", timeout=5)
    print(f"[Health] GET /api/products -> {r.status_code}")
except Exception as e:
    print(f"[Health] BRAK POŁĄCZENIA: {e}")
    exit(1)

# Test 2: Ensure nowego produktu testowego
test_ean = "TEST9999999001"
payload = {
    "ean": test_ean,
    "sku": "TEST-INSERT-01",
    "brand": "TestSQL",
    "modelName": "SQL Insert Test",
    "size": "44"
}

print(f"\n[Ensure] POST /api/products/ensure")
print(f"  Payload: {json.dumps(payload)}")

try:
    r = requests.post(f"{BASE}/api/products/ensure", json=payload, timeout=30)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.text[:500]}")
except Exception as e:
    print(f"  ERROR: {e}")
