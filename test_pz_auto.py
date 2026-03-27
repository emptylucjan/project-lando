import json
import sys
from sfera_api import run_sfera_action

# Najpierw upewnij się, że produkt istnieje
ensure_payload = [
    {
        "SKU": "ZALA-TEST-SKU",
        "EAN": "5907529223437",
        "Size": "42",
        "Brand": "Zalando",
        "ModelName": "Test Shirt"
    }
]

print("=== TEST ENSURE PRODUCTS ===")
ensure_res = run_sfera_action("EnsureProducts", ensure_payload)
print("Response:", json.dumps(ensure_res, indent=2, ensure_ascii=False))

if not ensure_res.get("Success"):
    print("❌ Nie udało się potwierdzić asortymentu!")
    sys.exit(1)

# Potem stwórz PZ
pz_payload = {
    "dostawcaNip": "66639093114",   # eleat psolka
    "dostawcaEmail": None,
    "uwagi": "TEST PZ Mrowka - Zalando - BEZ BACKENDU",
    "numerFakturyDostawcy": "ZALA-TEST-002",
    "items": [
        {"ean": "5907529223437", "symbol": None, "quantity": 1, "cenaZakupu": 299.0}
    ]
}

print("\n=== TEST PZ LOKALNY ===")
print("Payload:", json.dumps(pz_payload, indent=2))

try:
    result = run_sfera_action("CreatePZ", pz_payload)
    print("Response:", json.dumps(result, indent=2, ensure_ascii=False))
    
    if result.get("Success"):
        print("✅ SUKCES: Dokument PZ utworzony poprawnie pomyślnie z poziomu Python!")
    else:
        print("❌ BŁĄD:", result.get("Message", "Brak wiadomości"))
        sys.exit(1)
        
except Exception as e:
    print(f"Exception: {e}")
    sys.exit(1)
