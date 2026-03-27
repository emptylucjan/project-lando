"""Scrape Nike P-6000 rozmiary 39 i 40, wylicz buy_price, wydrukuj JSON."""
import sys, time, json
sys.path.insert(0, r"C:\Users\lukko\Desktop\projekt zalando")

from scraper.browser import create_browser, accept_cookies
from scraper.extractor import extract_product_data
from scraper.pricing import get_eur_rate, calculate_buy_price_eur

URL = "https://www.zalando.pl/nike-sportswear-p-6000-unisex-sneakersy-niskie-black-ni116d0sz-c11.html"
TARGET_SIZES = {"39", "40"}

driver = create_browser(headless=True)
try:
    driver.get("https://www.zalando.pl")
    time.sleep(2)
    accept_cookies(driver)
    time.sleep(1)
    data = extract_product_data(driver, URL)
finally:
    driver.quit()

if not data:
    print("BLAD: brak danych")
    sys.exit(1)

eur_rate = get_eur_rate()
price    = data.get("current_price", 0)
buy_eur  = calculate_buy_price_eur(price, eur_rate)
buy_pln  = round(price * 0.8, 2)

print(f"=== {data.get('name','?')} ===")
print(f"SKU: {data.get('sku','?')}")
print(f"Cena Zalando: {price} PLN")
print(f"Buy EUR: {buy_eur} (kurs {eur_rate:.4f})")
print(f"Buy PLN (80%): {buy_pln}")
print()

result = {"sku": data.get("sku"), "name": data.get("name"), "price_pln": price,
          "buy_pln": buy_pln, "buy_eur": buy_eur, "eur_rate": eur_rate, "sizes": []}

sizes = data.get("sizes", [])
for s in sizes:
    sz = str(s.get("size","") if isinstance(s, dict) else s)
    if sz not in TARGET_SIZES:
        continue
    avail = s.get("available", True) if isinstance(s, dict) else True
    ean   = s.get("ean") if isinstance(s, dict) else None
    print(f"Rozmiar {sz}: available={avail}, EAN={ean}")
    result["sizes"].append({"size": sz, "available": avail, "ean": ean})

with open(r"C:\Users\lukko\Desktop\projekt zalando\p6000_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\nZapisano do p6000_result.json")
