"""Pełny scrape Nike P-6000 z EAN dla rozm 39 i 40."""
import sys, time, json, logging
sys.path.insert(0, r"C:\Users\lukko\Desktop\projekt zalando")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

from scraper.browser import create_browser, accept_cookies
from scraper.extractor import extract_product_data
from scraper.pricing import get_eur_rate, calculate_buy_price_eur

URL = "https://www.zalando.pl/nike-sportswear-p-6000-unisex-sneakersy-niskie-black-ni116d0sz-c11.html"
TARGET = {"39", "40"}

driver = create_browser(headless=True)
try:
    driver.get("https://www.zalando.pl")
    time.sleep(2)
    accept_cookies(driver)
    time.sleep(1)
    # Pełny scrape — bez max_price ograniczenia (żeby scrapeował EAN)
    data = extract_product_data(driver, URL, max_price=None)
finally:
    driver.quit()

if not data:
    print("BLAD: brak danych"); sys.exit(1)

eur_rate = get_eur_rate()
price    = data.get("current_price", 0)
buy_pln  = round(price * 0.8, 2)
buy_eur  = calculate_buy_price_eur(price, eur_rate)
sku_base = None

print(f"\n=== {data.get('name','?')} ===")
print(f"Cena: {price} PLN | Buy: {buy_pln} PLN | {buy_eur} EUR (kurs {eur_rate:.4f})")
print()

sizes_target = []
for s in data.get("sizes", []):
    sz = str(s.get("size", ""))
    if sz not in TARGET: continue
    ean = s.get("ean")
    sku = s.get("sku")
    if sku: sku_base = sku
    print(f"Rozm {sz}: available={s.get('available')}, EAN={ean}, SKU={sku}")
    sizes_target.append({"size": sz, "ean": ean, "sku": sku,
                         "available": s.get("available", True)})

result = {
    "name": data.get("name"),
    "brand": data.get("brand"),
    "sku_base": sku_base,
    "price_pln": price,
    "buy_pln": buy_pln,
    "buy_eur": buy_eur,
    "eur_rate": eur_rate,
    "sizes": sizes_target
}
with open(r"C:\Users\lukko\Desktop\projekt zalando\p6000_full.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\nZapisano do p6000_full.json")
print(json.dumps(result, ensure_ascii=False, indent=2))
