"""
test_pz_endpoint.py — Testuje endpoint PZ (Przyjęcie Zewnętrzne) backendu Subiekt.
Uruchom najpierw backend (cd b2b-frontend-master/backend && dotnet run),
następnie uruchom ten skrypt.
"""
import requests
import json

BASE_URL = "http://localhost:5050"


def test_połączenie():
    print("=" * 60)
    print("TEST: Połączenie z backendem")
    try:
        r = requests.get(BASE_URL + "/", timeout=5)
        print(f"✅ Backend odpowiada: {r.text}")
    except Exception as e:
        print(f"❌ Backend niedostępny: {e}")
        print("   Uruchom: cd b2b-frontend-master/backend && dotnet run")
        return False
    return True


def test_produkty():
    print("\n" + "=" * 60)
    print("TEST: Pobieranie produktów z Subiekta")
    try:
        r = requests.get(BASE_URL + "/api/products/grouped", timeout=30)
        if r.status_code == 200:
            data = r.json()
            print(f"✅ Pobrano {len(data)} produktów/grup")
            if data:
                first = data[0]
                print(f"   Przykład: {first.get('name', '?')} | SKU: {first.get('styleCode', '?')}")
        else:
            print(f"❌ Błąd {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"❌ Błąd: {e}")


def test_klienci():
    print("\n" + "=" * 60)
    print("TEST: Wyszukiwanie podmiotów w Subiekcie (dostawca Zalando)")
    try:
        r = requests.get(BASE_URL + "/api/customers/find?email=zalando", timeout=30)
        if r.status_code == 200:
            data = r.json()
            print(f"   Znaleziono {len(data)} podmiotów z 'zalando' w emailu")
        # Spróbuj też po nazwie — szukamy podmiot 'Zalando'
        r2 = requests.get(BASE_URL + "/api/customers/find", timeout=30)
        if r2.status_code == 200:
            all_clients = r2.json()
            zalando = [c for c in all_clients if 'zalando' in c.get('name', '').lower()]
            if zalando:
                print(f"✅ Znaleziono podmiot Zalando: {zalando[0]}")
            else:
                print("⚠️  Brak podmiotu 'Zalando' w Subiekcie — PZ będzie bez dostawcy")
    except Exception as e:
        print(f"❌ Błąd: {e}")


def test_ean_search(ean: str):
    print(f"\n" + "=" * 60)
    print(f"TEST: Szukam produktu po EAN: {ean}")
    try:
        r = requests.get(BASE_URL + f"/api/products/findByEan?ean={ean}", timeout=30)
        if r.status_code == 200:
            data = r.json()
            print(f"✅ Znaleziono: {data.get('name', '?')} | Symbol: {data.get('symbol', '?')}")
            return True
        elif r.status_code == 404:
            print(f"⚠️  Produkt z EAN {ean} nie istnieje w Subiekcie")
        else:
            print(f"❌ Błąd {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"❌ Błąd: {e}")
    return False


def test_pz_dry_run(ean: str, qty: int = 1, cena: float = 299.0):
    """Testowy PZ — tworzy prawdziwy dokument w Subiekcie testowym!"""
    print(f"\n" + "=" * 60)
    print(f"TEST: Tworzę PZ — EAN={ean}, qty={qty}, cena={cena} PLN")
    print("⚠️  To jest PRAWDZIWY zapis w bazie testowej!")

    payload = {
        "dostawcaNip": None,
        "dostawcaEmail": None,
        "dataOperacji": None,
        "items": [
            {
                "ean": ean,
                "quantity": qty,
                "cenaZakupu": cena
            }
        ]
    }

    try:
        r = requests.post(BASE_URL + "/api/pz/create", json=payload, timeout=60)
        if r.status_code == 200:
            data = r.json()
            print(f"✅ PZ UTWORZONE: {data.get('documentNumber', '?')}")
            return True
        else:
            print(f"❌ Błąd {r.status_code}:")
            print(r.text[:500])
    except Exception as e:
        print(f"❌ Błąd: {e}")
    return False


if __name__ == "__main__":
    print("🧪 TESTY ENDPOINTÓW SUBIEKT")
    print("Baza testowa: Nexo_eleat teesty kurwa @ SZEFAKOMP\\INSERTNEXO")

    if not test_połączenie():
        exit(1)

    test_produkty()
    test_klienci()

    # ─── Test EAN + PZ ───────────────────────────────────────────
    # Wpisz EAN z Twojej bazy żeby przetestować
    TEST_EAN = input("\nPodaj EAN produktu z Subiekta do testu PZ (lub Enter żeby pominąć): ").strip()
    if TEST_EAN:
        found = test_ean_search(TEST_EAN)
        if found:
            create = input("Czy stworzyć testowe PZ? (t/n): ").strip().lower()
            if create == "t":
                test_pz_dry_run(TEST_EAN, qty=1, cena=299.0)

    print("\n✅ Testy zakończone.")
