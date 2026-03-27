"""
scrape_and_pz.py — scrapuje produkt Zalando (EAN/SKU per rozmiar)
i tworzy PZ w Subiekcie przez backend API.

Użycie:
  py -3.12 scrape_and_pz.py <URL> <rozmiar>x<ilosc> [<rozmiar>x<ilosc> ...]

Przykład:
  py -3.12 scrape_and_pz.py https://www.zalando.pl/... 41x3 42.5x3
"""
import sys
import json
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BACKEND = "http://localhost:5050"
MARGIN  = 0.15   # 15% marza (sprzedaz = zakup * 1.15)
DISCOUNT = 0.80  # nasze wyliczenie Zalando: plamy 80% ceny = cena zakupu

def scrape_product(url: str) -> dict:
    """Scrapuje URL Zalando i zwraca pełne dane produktu z EAN/SKU per rozmiar."""
    import sys, os
    # Dodaj folder scraper do path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scraper"))
    from browser import create_browser
    from extractor import extract_product_data

    logger.info("Uruchamiam Chrome i scrapuję: %s", url)
    driver = create_browser(headless=False)
    try:
        # Akceptuj cookies automatycznie przez Selenium
        driver.get(url)
        import time; time.sleep(3)
        try:
            btn = driver.find_element("xpath", "//button[contains(.,'Zaakceptuj')]")
            btn.click()
            time.sleep(1)
        except Exception:
            pass

        data = extract_product_data(driver, url)
    finally:
        driver.quit()

    return data


def calculate_buy_price(price_pln: float) -> float:
    """Cena zakupu = cena Zalando * 0.8 (nasze wyliczenie - 20% rabat Zalando)."""
    return round(price_pln * DISCOUNT, 2)


def ensure_product(ean: str, sku: str, brand: str, model: str, size: str, buy_price: float) -> dict:
    """Sprawdza/tworzy produkt w Subiekcie przed PZ uruchamiając lokalne C# CLI."""
    from sfera_api import run_sfera_action
    
    payload = {
        "ean": ean,
        "sku": sku,
        "brand": brand,
        "modelName": model,
        "size": size,
        "cenaZakupu": buy_price
    }
    
    logger.info("Ensure lokalne Sfera: r.%s (EAN=%s)", size, ean or "?")
    res = run_sfera_action("EnsureProducts", [payload])
    
    if res.get("Success"):
        logger.info("Ensure OK: %s", res.get("EnsureResults"))
        # Obliczenie symbolu deterministycznie tak samo jak w CLI
        expected_symbol = f"{sku}-{size}".replace(",", ".").replace(" ", "").replace("/", "-") if (sku and size) else (sku or "")
        return {"symbol": expected_symbol}
    else:
        logger.warning("Ensure FAILED: %s", res.get("Message"))
        return {}


def create_pz(sizes_data: list, product_name: str, invoice_num: str = None) -> dict:
    """Tworzy PZ w Subiekcie przez lokalne Sfera CLI."""
    from sfera_api import run_sfera_action
    
    items = []
    for entry in sizes_data:
        ean = entry.get("ean")
        size = entry.get("size")
        qty  = entry.get("qty", 1)
        buy  = entry.get("buy_price")

        if not ean:
            logger.warning("Brak EAN dla rozmiaru %s — pomijam!", size)
            continue

        sku = entry.get("sku")
        pz_symbol = entry.get("symbol") or (f"{sku}-{size}".replace(",", ".") if sku and size else None)

        items.append({
            "ean": ean,
            "symbol": pz_symbol, 
            "quantity": qty,
            "cenaZakupu": buy
        })

    if not items:
        logger.error("Brak pozycji z EAN — nie tworzę PZ!")
        return {}

    payload = {
        "dostawcaNip": None,
        "dostawcaEmail": None,
        "uwagi": f"AUTO PZ Mrowka — {product_name}",
        "numerFakturyDostawcy": invoice_num or f"ZALA-AUTO",
        "items": items
    }

    logger.info("Lokalne wywołanie CreatePZ Sfera CLI: %d pozycji", len(items))
    res = run_sfera_action("CreatePZ", payload)
    
    if not res.get("Success"):
        print(f"\n❌ PZ create failed:")
        print(f"  Error: {res.get('Message', '?')}")
        print(f"  Raw: {res.get('Raw', '')}")
        return {}
        
    return {"documentNumber": res.get("DocumentNumber")}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[1]
    # Parsuj argumenty: "41x3" -> (41.0, 3), "42.5x3" -> (42.5, 3)
    requested = []
    for arg in sys.argv[2:]:
        parts = arg.split("x")
        if len(parts) != 2:
            print(f"Błędny format: {arg} (oczekiwano np. 41x3)")
            sys.exit(1)
        size  = parts[0].replace(",", ".")
        qty   = int(parts[1])
        requested.append((size, qty))

    logger.info("Requested sizes: %s", requested)

    # === KROK 1: Scrapuj produkt ===
    product = scrape_product(url)
    if not product:
        logger.error("Nie udało się zebrać danych produktu!")
        sys.exit(1)

    logger.info("Produkt: %s | Cena: %.2f PLN", product.get("name"), product.get("current_price", 0))

    # === KROK 2: Znajdź EAN dla żądanych rozmiarów ===
    all_sizes = product.get("sizes", [])
    price     = product.get("current_price")
    if not price:
        logger.error("Nie udało się wyciągnąć ceny produktu! Sprawdź scraper lub URL.")
        sys.exit(1)
    buy_price = calculate_buy_price(price)
    sell_price = round(buy_price * (1 + MARGIN), 2)

    logger.info(
        "Cena Zalando: %.2f PLN | Cena zakupu (x0.8): %.2f PLN | Cena sprzedaży (+15%%): %.2f PLN",
        price, buy_price, sell_price
    )

    sizes_for_pz = []
    for (req_size, qty) in requested:
        # Szukaj w sizes (może być format "41" lub "EU 41")
        found = None
        for s in all_sizes:
            s_clean = str(s.get("size", "")).replace("EU ", "").strip()
            if s_clean == req_size:
                found = s
                break

        if not found:
            logger.warning("Rozmiar %s nie znaleziony w scrape! Dostępne: %s",
                           req_size, [s.get("size") for s in all_sizes])
            continue

        ean = found.get("ean")
        sku = found.get("sku")
        logger.info("Rozmiar %s: EAN=%s SKU=%s ilosc=%d", req_size, ean, sku, qty)

        sizes_for_pz.append({
            "size": req_size,
            "ean": ean,
            "sku": sku,
            "qty": qty,
            "buy_price": buy_price
        })

    if not sizes_for_pz:
        logger.error("Brak pasujących rozmiarów!")
        sys.exit(1)

    # === KROK 3: Wydrukuj podsumowanie ===
    print("\n" + "="*60)
    print(f"PRODUKT: {product.get('brand')} {product.get('name')}")
    print(f"CENA ZALANDO: {price:.2f} PLN")
    print(f"CENA ZAKUPU (x0.8): {buy_price:.2f} PLN")
    print(f"CENA SPRZEDAZY (+15%): {sell_price:.2f} PLN")
    print(f"URL: {url}")
    print("-"*60)
    for s in sizes_for_pz:
        print(f"  Rozmiar {s['size']:>5}  EAN: {s['ean'] or 'BRAK!':15}  SKU: {s['sku'] or '?':15}  Qty: {s['qty']}")
    print("="*60)

    missing_ean = [s for s in sizes_for_pz if not s["ean"]]
    if missing_ean:
        logger.warning("Brak EAN dla rozmiarów %s — pomijam", [s["size"] for s in missing_ean])
        sizes_for_pz = [s for s in sizes_for_pz if s["ean"]]
    if not sizes_for_pz:
        logger.error("Brak rozmiarów z EAN — nie można stworzyć PZ!"); sys.exit(1)

    # === KROK 4: Ensure — dodaj/sprawdź produkty w Subiekcie ===
    brand  = product.get("brand") or "Jordan"
    model  = (product.get("name") or "Air Jordan 1 Mid SE").replace(brand, "").strip()
    print("\n→ Sprawdzam/dodaję produkty w Subiekcie...")
    for s in sizes_for_pz:
        if s.get("ean"):
            ensure_res = ensure_product(
                ean=s["ean"], sku=s.get("sku"), brand=brand, model=model,
                size=s["size"], buy_price=s["buy_price"]
            )
            # Użyj symbolu zwróconego przez ensure (może być inny niż EAN gdy produkt "już istnieje")
            returned_symbol = (ensure_res or {}).get("symbol") or s["ean"]
            if returned_symbol and returned_symbol != s.get("symbol"):
                logger.info("Ensure zwrócił symbol=%s dla r.%s (EAN=%s)", returned_symbol, s["size"], s["ean"])
                s["symbol"] = returned_symbol  # aktualizuj symbol dla PZ create

    # === KROK 5: Utwórz PZ ===
    result = create_pz(
        sizes_for_pz,
        product_name=f"{brand} {model}",
        invoice_num=f"ZALA-{brand.upper()[:5]}"
    )

    if result:
        print(f"\n✅ PZ GOTOWY! Numer: {result.get('documentNumber', result)}")
    else:
        print("\n❌ Błąd tworzenia PZ!")


if __name__ == "__main__":
    main()
